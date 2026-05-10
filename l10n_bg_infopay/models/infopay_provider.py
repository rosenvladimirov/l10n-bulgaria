# Copyright 2025 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

import requests

from odoo import api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

INFOPAY_BASE_URL = "https://integration.infopay.bg"
INFOPAY_TIMEOUT = 30


class InfopayProvider(models.AbstractModel):
    _name = "infopay.provider"
    _description = "InfoPay API Client"

    # ── helpers ───────────────────────────────────────────────────────

    @api.model
    def _get_base_url(self):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("l10n_bg_infopay.base_url", INFOPAY_BASE_URL)
        )

    @api.model
    def _request(self, method, endpoint, session=None, **kwargs):
        """Low-level HTTP request to InfoPay.

        *endpoint* can be a relative path (``/api/…``) or a full URL returned
        by a pagination link.
        """
        if endpoint.startswith("http"):
            url = endpoint
        else:
            url = f"{self._get_base_url()}{endpoint}"

        headers = kwargs.pop("headers", {})
        if session:
            headers["SessionId"] = session["session_id"]
            headers["SessionKey"] = session["session_key"]
        headers.setdefault("Content-Type", "application/json")

        try:
            resp = requests.request(
                method, url, headers=headers, timeout=INFOPAY_TIMEOUT, **kwargs
            )
        except requests.RequestException as exc:
            raise UserError(
                self.env._("InfoPay connection error: %s", exc)
            ) from exc

        if resp.status_code == 401:
            raise UserError(
                self.env._("InfoPay authentication failed. Check credentials.")
            )
        if resp.status_code == 403:
            raise UserError(
                self.env._("InfoPay access denied. Check subscription plan.")
            )
        if resp.status_code not in (200, 201, 204):
            _logger.error(
                "InfoPay %s %s → %s: %s", method, url, resp.status_code, resp.text
            )
            raise UserError(
                self.env._("InfoPay API error (%(code)s): %(body)s",
                           code=resp.status_code, body=resp.text[:200])
            )

        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()

    # ── session ───────────────────────────────────────────────────────

    @api.model
    def _create_session(self, company):
        """Authenticate and return ``{session_id, session_key}``.

        The access token is read from the crypto wallet of the user
        referenced by ``company.infopay_token_user_id``.
        """
        if not company.infopay_unique_id:
            raise UserError(
                self.env._(
                    "InfoPay credentials are not configured on company '%s'.",
                    company.name,
                )
            )
        access_token = company._infopay_get_access_token()
        result = self._request("POST", "/api/session", json={
            "uniqueId": company.infopay_unique_id,
            "accessToken": access_token,
        })
        status = result.get("Status")
        if status != "Success":
            raise UserError(
                self.env._("InfoPay session creation failed: %s", status)
            )
        return {
            "session_id": result["SessionId"],
            "session_key": result["SessionKey"],
        }

    @api.model
    def _close_session(self, session):
        try:
            self._request("POST", "/api/session/close", session=session)
        except Exception:
            _logger.warning("Failed to close InfoPay session", exc_info=True)

    @api.model
    def _check_session(self, session):
        result = self._request("POST", "/api/session/check", session=session)
        return result.get("State")

    # ── synchronisation ───────────────────────────────────────────────

    @api.model
    def _refresh_sync(self, session, account_ids=None):
        """Trigger a balance + transaction refresh at the bank."""
        data = {}
        if account_ids:
            data["AccountIds"] = account_ids
        self._request(
            "POST",
            "/api/synchronizations/balancesAndTransactions/refresh",
            session=session,
            json=data,
        )

    @api.model
    def _get_sync_state(self, session, account_ids=None):
        params = {}
        if account_ids:
            params["accountIds"] = account_ids
        result = self._request(
            "GET",
            "/api/synchronizations/balancesAndTransactions/currentState",
            session=session,
            params=params,
        )
        return result.get("States", [])

    # ── accounts ──────────────────────────────────────────────────────

    @api.model
    def _get_accounts(self, session, with_balance=False):
        params = {}
        if with_balance:
            params["withBalance"] = "true"
        result = self._request(
            "GET", "/api/accounts", session=session, params=params
        )
        return result.get("Accounts", [])

    @api.model
    def _get_account(self, session, account_id, with_balance=False):
        params = {}
        if with_balance:
            params["withBalance"] = "true"
        return self._request(
            "GET", f"/api/accounts/{account_id}", session=session, params=params
        )

    # ── transactions ──────────────────────────────────────────────────

    @api.model
    def _get_transactions(self, session, account_id, date_from, date_to):
        """Fetch all booked transactions (handles pagination).

        Returns ``(transactions_list, balances_list)``.
        """
        all_transactions = []
        balances = []
        endpoint = f"/api/accounts/{account_id}/transactions"
        params = {
            "dateFrom": date_from.isoformat(),
            "dateTo": date_to.isoformat(),
        }

        while endpoint:
            result = self._request(
                "GET", endpoint, session=session, params=params
            )
            # only the first request carries query params; subsequent pages
            # include them in the pagination URL
            params = {}

            if not balances:
                balances = result.get("Balances", [])

            tx_block = result.get("Transactions", {})
            all_transactions.extend(tx_block.get("Booked", []))

            next_link = (tx_block.get("Links") or {}).get("Next")
            endpoint = next_link.get("href") if next_link else None

        return all_transactions, balances

    @api.model
    def _get_missing_dates(self, session, account_id, date_from, date_to):
        result = self._request(
            "GET",
            f"/api/accounts/{account_id}/transactionsMissingDates",
            session=session,
            params={
                "dateFrom": date_from.isoformat(),
                "dateTo": date_to.isoformat(),
            },
        )
        return result.get("NotSyncedTransactionsDates", [])

    # ── single payments ───────────────────────────────────────────────

    @api.model
    def _create_domestic_payment(
        self, session, debtor_iban, creditor_name, creditor_iban,
        amount, description, service_level=None, end_to_end_id=None,
    ):
        payment = {
            "CreditorName": creditor_name[:35],
            "CreditorAccount": {"IBAN": creditor_iban},
            "InstructedAmount": {"Amount": str(amount), "Currency": "BGN"},
            "RemittanceInformationUnstructured": description[:70],
        }
        if service_level:
            payment["ServiceLevel"] = service_level
        if end_to_end_id:
            payment["EndToEndIdentification"] = end_to_end_id[:35]

        return self._request(
            "POST",
            "/api/payments/domestic-credit-transfers-bgn",
            session=session,
            json={
                "DebitorAccount": {"IBAN": debtor_iban},
                "Payment": payment,
            },
        )

    @api.model
    def _create_sepa_payment(
        self, session, debtor_iban, creditor_name, creditor_iban,
        amount, description, creditor_country,
        creditor_city=None, service_level=None, end_to_end_id=None,
    ):
        payment = {
            "CreditorName": creditor_name[:35],
            "CreditorAccount": {"IBAN": creditor_iban},
            "CreditorAddress": {"Country": creditor_country},
            "InstructedAmount": {"Amount": str(amount), "Currency": "EUR"},
            "RemittanceInformationUnstructured": description[:70],
        }
        if creditor_city:
            payment["CreditorAddress"]["City"] = creditor_city[:35]
        if service_level:
            payment["ServiceLevel"] = service_level
        if end_to_end_id:
            payment["EndToEndIdentification"] = end_to_end_id[:35]

        return self._request(
            "POST",
            "/api/payments/sepa-credit-transfers",
            session=session,
            json={
                "DebitorAccount": {"IBAN": debtor_iban},
                "Payment": payment,
            },
        )

    @api.model
    def _create_budget_payment(
        self, session, debtor_iban, creditor_name, creditor_iban,
        amount, description, ultimate_debtor, tax_payer_id, tax_payer_type,
        service_level=None, end_to_end_id=None,
    ):
        data = {
            "DebitorAccount": {"IBAN": debtor_iban},
            "CreditorName": creditor_name[:35],
            "CreditorAccount": {"IBAN": creditor_iban},
            "InstructedAmount": {"Amount": str(amount), "Currency": "BGN"},
            "RemittanceInformationUnstructured": description[:70],
            "UltimateDebtor": ultimate_debtor,
            "BudgetPaymentDetails": {
                "TaxPayerId": tax_payer_id,
                "TaxPayerType": tax_payer_type,
            },
        }
        if service_level:
            data["ServiceLevel"] = service_level
        if end_to_end_id:
            data["EndToEndIdentification"] = end_to_end_id[:35]

        return self._request(
            "POST",
            "/api/payments/domestic-budget-transfers-bgn",
            session=session,
            json=data,
        )

    # ── bulk payments ─────────────────────────────────────────────────

    @api.model
    def _create_bulk_domestic_payments(self, session, debtor_iban, payments):
        """*payments*: list of dicts ``{creditor_name, creditor_iban,
        amount, description}``.  Min 2 / max 250 items.
        """
        return self._request(
            "POST",
            "/api/bulk-payments/domestic-credit-transfers-bgn",
            session=session,
            json={
                "DebitorAccount": {"IBAN": debtor_iban},
                "Payments": [
                    {
                        "CreditorName": p["creditor_name"][:35],
                        "CreditorAccount": {"IBAN": p["creditor_iban"]},
                        "InstructedAmount": {
                            "Amount": str(p["amount"]),
                            "Currency": "BGN",
                        },
                        "RemittanceInformationUnstructured": p["description"][:70],
                    }
                    for p in payments
                ],
            },
        )

    @api.model
    def _create_bulk_sepa_payments(self, session, debtor_iban, payments):
        """*payments*: list of dicts ``{creditor_name, creditor_iban,
        amount, description, country}``.  Min 2 / max 250 items.
        """
        return self._request(
            "POST",
            "/api/bulk-payments/sepa-credit-transfers",
            session=session,
            json={
                "DebitorAccount": {"IBAN": debtor_iban},
                "Payments": [
                    {
                        "CreditorName": p["creditor_name"][:35],
                        "CreditorAccount": {"IBAN": p["creditor_iban"]},
                        "CreditorAddress": {"Country": p["country"]},
                        "InstructedAmount": {
                            "Amount": str(p["amount"]),
                            "Currency": "EUR",
                        },
                        "RemittanceInformationUnstructured": p["description"][:70],
                    }
                    for p in payments
                ],
            },
        )

    # ── payment status ────────────────────────────────────────────────

    @api.model
    def _get_payment_status(self, session, payment_id, bulk=False):
        prefix = "bulk-payments" if bulk else "payments"
        return self._request(
            "GET", f"/api/{prefix}/{payment_id}/status", session=session
        )

    # ── invoices ──────────────────────────────────────────────────────

    @api.model
    def _create_invoice(self, session, payload):
        """Issue an invoice into the InfoPay dashboard.

        *payload* must follow the OpenAPI ``InvoiceCreateRequest`` schema —
        the caller (typically ``account.move._l10n_bg_infopay_build_payload``)
        is responsible for shape compliance:

        * ``number`` — exactly 10 digits, leading zeros required (regex
          ``^[0-9]{10}$``).  The InfoPay server rejects non-conforming
          numbers with HTTP 400; do not send a free-form Odoo move name.
        * ``numberSeriesId`` — opaque GUID pre-created in the InfoPay
          portal.  No ``GET`` endpoint exists to list series, so this is
          configuration data on ``account.journal``.
        * ``content`` — discriminator on ``contentType``
          (``contentWithVAT`` | ``contentWithoutVAT``).  Server validates
          arithmetic strictly (``amount = quantity * unitPrice``,
          ``amountVATIncluded = amount + vatAmount``, group totals = sum
          of line totals).  Round to 2 decimals consistently.
        * ``customer.identificationNumber`` — required; covers EIK / ЕГН /
          ЛНЧ.  ``vatId`` is the separate VAT registration number for
          VAT-registered counterparties.

        Response shape: ``{invoiceId, number}``.  There is no GET / status
        / cancel endpoint for invoices in the public spec — caller must
        treat the returned ``invoiceId`` as the only handle for the
        document.  See ``reference_infopay_api_spec.md`` for full surface
        and gotchas.
        """
        return self._request(
            "POST", "/api/invoices", session=session, json=payload
        )
