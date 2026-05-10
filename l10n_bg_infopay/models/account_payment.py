# Copyright 2025 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

INFOPAY_FINAL_OK = frozenset({
    "Processed", "ProcessedInterbank", "Executed", "Completed",
})
INFOPAY_FINAL_FAIL = frozenset({
    "Cancelled", "Rejected", "InsufficientFunds",
    "Rejected_Cancelled",
})


class AccountPayment(models.Model):
    _inherit = "account.payment"

    l10n_bg_infopay_payment_id = fields.Char(
        string="InfoPay Payment ID",
        readonly=True,
        copy=False,
    )
    l10n_bg_infopay_sca_url = fields.Char(
        string="InfoPay SCA URL",
        readonly=True,
        copy=False,
        help="Redirect URL for Strong Customer Authentication at the bank.",
    )
    l10n_bg_infopay_status = fields.Char(
        string="InfoPay Status",
        readonly=True,
        copy=False,
    )
    l10n_bg_infopay_bulk = fields.Boolean(
        string="InfoPay Bulk",
        readonly=True,
        copy=False,
        help="True if this payment was sent as part of a bulk payment.",
    )

    # ── submit ────────────────────────────────────────────────────────

    def _infopay_submit(self):
        """Submit this payment to InfoPay.

        Returns the API response dict containing ``PaymentId`` and
        ``Links.ScaRedirect``.
        """
        self.ensure_one()
        journal = self.journal_id
        if not journal.l10n_bg_infopay_account_id:
            raise UserError(
                self.env._(
                    "Journal '%s' is not configured for InfoPay.", journal.name
                )
            )

        debtor_iban = journal.bank_account_id.acc_number
        if not debtor_iban:
            raise UserError(
                self.env._(
                    "Journal '%s' has no bank account number set.", journal.name
                )
            )

        partner_bank = self.partner_bank_id or self.partner_id.bank_ids[:1]
        if not partner_bank:
            raise UserError(
                self.env._(
                    "Partner '%s' has no bank account configured.",
                    self.partner_id.name,
                )
            )

        creditor_iban = partner_bank.acc_number
        creditor_name = self.partner_id.name or ""
        description = self.ref or self.name or ""

        with journal._infopay_session() as (provider, session):
            currency_name = self.currency_id.name
            if currency_name == "BGN":
                result = provider._create_domestic_payment(
                    session,
                    debtor_iban,
                    creditor_name,
                    creditor_iban,
                    self.amount,
                    description,
                )
            elif currency_name == "EUR":
                country = (
                    self.partner_id.country_id.code
                    or partner_bank.acc_number[:2]  # first 2 chars of IBAN
                    or "BG"
                )
                result = provider._create_sepa_payment(
                    session,
                    debtor_iban,
                    creditor_name,
                    creditor_iban,
                    self.amount,
                    description,
                    creditor_country=country,
                )
            else:
                raise UserError(
                    self.env._(
                        "InfoPay supports only BGN and EUR payments.  "
                        "Currency '%s' is not supported.",
                        currency_name,
                    )
                )

        sca_url = (result.get("Links") or {}).get("ScaRedirect")
        self.write({
            "l10n_bg_infopay_payment_id": result.get("PaymentId"),
            "l10n_bg_infopay_sca_url": sca_url,
            "l10n_bg_infopay_status": result.get("TransactionStatus"),
        })
        _logger.info(
            "InfoPay payment %s created for %s %s %s (SCA: %s)",
            result.get("PaymentId"),
            creditor_name,
            self.amount,
            self.currency_id.name,
            sca_url,
        )
        return result

    def _infopay_submit_budget(
        self, ultimate_debtor, tax_payer_id, tax_payer_type,
        service_level=None,
    ):
        """Submit a budget/tax payment to InfoPay.

        Only BGN domestic budget transfers are supported.
        ``tax_payer_type``: ``'EGN'``, ``'EIK'`` or ``'PNF'``.
        """
        self.ensure_one()
        journal = self.journal_id
        if not journal.l10n_bg_infopay_account_id:
            raise UserError(
                self.env._(
                    "Journal '%s' is not configured for InfoPay.", journal.name
                )
            )

        debtor_iban = journal.bank_account_id.acc_number
        partner_bank = self.partner_bank_id or self.partner_id.bank_ids[:1]
        if not partner_bank:
            raise UserError(
                self.env._(
                    "Partner '%s' has no bank account configured.",
                    self.partner_id.name,
                )
            )

        with journal._infopay_session() as (provider, session):
            result = provider._create_budget_payment(
                session,
                debtor_iban,
                self.partner_id.name or "",
                partner_bank.acc_number,
                self.amount,
                self.ref or self.name or "",
                ultimate_debtor=ultimate_debtor,
                tax_payer_id=tax_payer_id,
                tax_payer_type=tax_payer_type,
                service_level=service_level,
            )

        sca_url = (result.get("Links") or {}).get("ScaRedirect")
        self.write({
            "l10n_bg_infopay_payment_id": result.get("PaymentId"),
            "l10n_bg_infopay_sca_url": sca_url,
            "l10n_bg_infopay_status": result.get("TransactionStatus"),
        })
        return result

    # ── status polling ────────────────────────────────────────────────

    def _infopay_check_status(self):
        """Poll InfoPay for the current payment status and update the record.

        Returns the raw API response dict.
        """
        self.ensure_one()
        if not self.l10n_bg_infopay_payment_id:
            return {}

        journal = self.journal_id
        with journal._infopay_session() as (provider, session):
            result = provider._get_payment_status(
                session, self.l10n_bg_infopay_payment_id, bulk=self.l10n_bg_infopay_bulk
            )

        tx_status = result.get("TransactionStatus", {})
        status_str = tx_status.get("Status", result.get("TransactionState", ""))
        is_final = tx_status.get("IsFinal", False)

        self.l10n_bg_infopay_status = status_str
        _logger.info(
            "InfoPay payment %s status: %s (final: %s)",
            self.l10n_bg_infopay_payment_id, status_str, is_final,
        )
        return result

    def _infopay_pull_status(self):
        """Check status for a recordset of payments and handle final states.

        * Successful final statuses → log as completed.
        * Failed final statuses → cancel the Odoo payment if still draft.
        """
        for payment in self:
            if not payment.l10n_bg_infopay_payment_id:
                continue
            if payment.l10n_bg_infopay_status in INFOPAY_FINAL_OK | INFOPAY_FINAL_FAIL:
                continue  # already resolved

            try:
                result = payment._infopay_check_status()
            except Exception:
                _logger.exception(
                    "InfoPay status check failed for payment %s (id=%s)",
                    payment.l10n_bg_infopay_payment_id, payment.id,
                )
                continue

            tx_status = result.get("TransactionStatus", {})
            status_str = tx_status.get(
                "Status", result.get("TransactionState", "")
            )

            if status_str in INFOPAY_FINAL_OK:
                _logger.info(
                    "InfoPay payment %s completed (%s)",
                    payment.l10n_bg_infopay_payment_id, status_str,
                )
            elif status_str in INFOPAY_FINAL_FAIL:
                _logger.warning(
                    "InfoPay payment %s failed (%s)",
                    payment.l10n_bg_infopay_payment_id, status_str,
                )
                if payment.state == "draft":
                    payment.action_cancel()

    @api.model
    def _infopay_pull_all_pending(self):
        """Poll status for every pending InfoPay payment.

        Called from UI buttons / menu actions in a separate module.
        Groups by journal to reuse a single API session per bank account.
        """
        pending = self.search([
            ("l10n_bg_infopay_payment_id", "!=", False),
            ("l10n_bg_infopay_status", "not in",
             list(INFOPAY_FINAL_OK | INFOPAY_FINAL_FAIL)),
        ])
        if not pending:
            return pending

        for journal in pending.mapped("journal_id"):
            jp = pending.filtered(lambda p, j=journal: p.journal_id == j)
            try:
                with journal._infopay_session() as (provider, session):
                    for payment in jp:
                        try:
                            result = provider._get_payment_status(
                                session,
                                payment.l10n_bg_infopay_payment_id,
                                bulk=payment.l10n_bg_infopay_bulk,
                            )
                            tx = result.get("TransactionStatus", {})
                            status = tx.get(
                                "Status",
                                result.get("TransactionState", ""),
                            )
                            payment.l10n_bg_infopay_status = status

                            if status in INFOPAY_FINAL_FAIL \
                                    and payment.state == "draft":
                                payment.action_cancel()
                        except Exception:
                            _logger.exception(
                                "InfoPay status poll failed for payment %s",
                                payment.l10n_bg_infopay_payment_id,
                            )
            except Exception:
                _logger.exception(
                    "InfoPay session failed for journal %s", journal.name,
                )
        return pending

    # ── bulk submit helper ────────────────────────────────────────────

    def _infopay_submit_bulk(self):
        """Submit multiple payments as a single bulk order.

        Call on a recordset of 2–250 payments that share the same journal
        and currency.  Returns the API response dict.
        """
        if len(self) < 2:
            raise UserError(
                self.env._("Bulk payments require at least 2 items.")
            )
        if len(self) > 250:
            raise UserError(
                self.env._("Bulk payments allow at most 250 items.")
            )

        journals = self.mapped("journal_id")
        if len(journals) != 1:
            raise UserError(
                self.env._("All bulk payments must use the same journal.")
            )
        journal = journals[0]
        if not journal.l10n_bg_infopay_account_id:
            raise UserError(
                self.env._(
                    "Journal '%s' is not configured for InfoPay.", journal.name
                )
            )

        currencies = self.mapped("currency_id")
        if len(currencies) != 1:
            raise UserError(
                self.env._("All bulk payments must use the same currency.")
            )
        currency_name = currencies[0].name

        debtor_iban = journal.bank_account_id.acc_number

        pay_dicts = []
        for pay in self:
            partner_bank = pay.partner_bank_id or pay.partner_id.bank_ids[:1]
            if not partner_bank:
                raise UserError(
                    self.env._(
                        "Partner '%s' has no bank account.", pay.partner_id.name
                    )
                )
            entry = {
                "creditor_name": pay.partner_id.name or "",
                "creditor_iban": partner_bank.acc_number,
                "amount": pay.amount,
                "description": pay.ref or pay.name or "",
            }
            if currency_name == "EUR":
                entry["country"] = (
                    pay.partner_id.country_id.code
                    or partner_bank.acc_number[:2]
                    or "BG"
                )
            pay_dicts.append(entry)

        with journal._infopay_session() as (provider, session):
            if currency_name == "BGN":
                result = provider._create_bulk_domestic_payments(
                    session, debtor_iban, pay_dicts
                )
            elif currency_name == "EUR":
                result = provider._create_bulk_sepa_payments(
                    session, debtor_iban, pay_dicts
                )
            else:
                raise UserError(
                    self.env._(
                        "InfoPay bulk payments support only BGN and EUR."
                    )
                )

        sca_url = (result.get("Links") or {}).get("ScaRedirect")
        self.write({
            "l10n_bg_infopay_payment_id": result.get("PaymentId"),
            "l10n_bg_infopay_sca_url": sca_url,
            "l10n_bg_infopay_status": result.get("TransactionStatus"),
            "l10n_bg_infopay_bulk": True,
        })
        return result
