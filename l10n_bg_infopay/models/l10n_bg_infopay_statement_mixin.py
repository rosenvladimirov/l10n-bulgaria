# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

"""Mixin for InfoPay statement-import bridges.

Bridge modules (OCA `account_statement_import_online`, EE
`account_online_synchronization`, or any future host) inherit this
mixin alongside their host model and override 3 small overrides
(`_l10n_bg_infopay_get_company`, `_l10n_bg_infopay_get_account_id`,
`_l10n_bg_infopay_use_admin_token`) — they do NOT call
``infopay.provider`` directly.  Session lifecycle, error handling,
admin/user-token routing and transaction normalisation all live
here.
"""

import logging
from collections import defaultdict
from datetime import date

from odoo import models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class InfopayStatementMixin(models.AbstractModel):
    _name = "l10n.bg.infopay.statement.mixin"
    _description = "InfoPay statement-import mixin (host-agnostic)"

    # ── overrides for the host model ──────────────────────────────────

    def _l10n_bg_infopay_get_company(self):
        """Return the ``res.company`` whose InfoPay credentials should
        be used.  Hosts: account.journal → ``self.company_id``; OCA
        provider → ``self.journal_id.company_id``; EE online.account →
        ``self.journal_ids.company_id``.
        """
        self.ensure_one()
        raise NotImplementedError(
            "%s must implement _l10n_bg_infopay_get_company" % self._name
        )

    def _l10n_bg_infopay_get_account_id(self):
        """Return the InfoPay account UUID for the host record."""
        self.ensure_one()
        raise NotImplementedError(
            "%s must implement _l10n_bg_infopay_get_account_id" % self._name
        )

    def _l10n_bg_infopay_use_admin_token(self):
        """Return True for cron / scheduled paths (admin Fernet token,
        no user password); False for interactive paths (user wallet).
        Default: True — most bridge calls are scheduled.  Hosts that
        run from an authenticated UI button override to False.
        """
        return True

    # ── public concrete methods (called by bridges) ───────────────────

    def _l10n_bg_infopay_pull_transactions(
        self, date_since: date, date_until: date,
    ):
        """Pull booked transactions + balances for the host's account.

        Returns ``(transactions, balances)`` tuple — same shape as
        ``infopay.provider._get_transactions``.  Bridge code is
        responsible for normalising into its own host's statement
        format using ``_l10n_bg_infopay_normalize_transaction``.
        """
        self.ensure_one()
        company = self._l10n_bg_infopay_get_company()
        account_id = self._l10n_bg_infopay_get_account_id()
        admin = self._l10n_bg_infopay_use_admin_token()
        provider = self.env["infopay.provider"]
        session = provider._create_session(company, admin=admin)
        try:
            return provider._get_transactions(
                session, account_id, date_since, date_until,
            )
        finally:
            provider._close_session(session)

    def _l10n_bg_infopay_pull_accounts(self, with_balance: bool = False):
        """Pull list of registered InfoPay accounts for the company."""
        self.ensure_one()
        company = self._l10n_bg_infopay_get_company()
        admin = self._l10n_bg_infopay_use_admin_token()
        provider = self.env["infopay.provider"]
        session = provider._create_session(company, admin=admin)
        try:
            return provider._get_accounts(session, with_balance=with_balance)
        finally:
            provider._close_session(session)

    def _l10n_bg_infopay_pull_missing_dates(
        self, date_since: date, date_until: date,
    ):
        """Pull the date-gap report for the host's account."""
        self.ensure_one()
        company = self._l10n_bg_infopay_get_company()
        account_id = self._l10n_bg_infopay_get_account_id()
        admin = self._l10n_bg_infopay_use_admin_token()
        provider = self.env["infopay.provider"]
        session = provider._create_session(company, admin=admin)
        try:
            return provider._get_missing_dates(
                session, account_id, date_since, date_until,
            )
        finally:
            provider._close_session(session)

    # ── normalisation (raw → standard statement line dict) ────────────

    def _l10n_bg_infopay_normalize_transaction(self, tx: dict) -> dict:
        """Convert one raw InfoPay transaction dict into a normalised
        Odoo statement-line dict with keys:

            date, payment_ref, ref, amount, account_number,
            partner_name, unique_import_id, narration

        Same shape used by all consumers (OCA online provider, EE
        widget, MT940 import path, manual button).  Bridges may
        post-process to add host-specific keys.
        """
        amount = float(tx.get("TransactionAmount", {}).get("amount", 0) or 0)
        tx_type = tx.get("TransactionType")
        # Sign correction — Credit positive, Debit negative
        if tx_type == "Debit" and amount > 0:
            amount = -amount
        elif tx_type == "Credit" and amount < 0:
            amount = -amount
        # Counterparty: incoming → debtor, outgoing → creditor
        if tx_type == "Credit":
            account_number = tx.get("DebtorAccount") or ""
            partner_name = tx.get("DebtorName") or ""
        else:
            account_number = tx.get("CreditorAccount") or ""
            partner_name = tx.get("CreditorName") or ""
        payment_ref = (
            tx.get("RemittanceInformationUnstructured")
            or tx.get("EntryReference")
            or partner_name
            or "/"
        )
        ref = tx.get("EntryReference") or tx.get("EndToEndIdentification") or ""
        unique_id = (
            tx.get("TransactionExternalId")
            or tx.get("TransactionId")
            or ""
        )
        booking_date = tx.get("BookingDate") or ""
        if booking_date:
            booking_date = booking_date[:10]  # ISO date prefix
        narration = tx.get("RemittanceInformationUnstructured") or ""

        return {
            "date": booking_date,
            "payment_ref": payment_ref,
            "ref": ref,
            "amount": amount,
            "account_number": account_number,
            "partner_name": partner_name,
            "unique_import_id": unique_id,
            "narration": narration,
        }

    def _l10n_bg_infopay_summarize_balances(self, balances: list) -> dict:
        """Reduce InfoPay balances list to ``{begin, end}`` floats.

        InfoPay returns several balance variants (BeginDay, ActualBalance,
        AvailableBalance, ...).  We pick the most common pair.
        """
        result = {"begin": None, "end": None}
        for bal in balances or []:
            try:
                val = float(bal.get("BalanceAmount", {}).get("amount", 0))
            except (ValueError, TypeError):
                continue
            bal_type = bal.get("BalanceType")
            if bal_type == "BeginDay":
                result["begin"] = val
            elif bal_type in ("ActualBalance", "AvailableBalance"):
                if result["end"] is None:
                    result["end"] = val
        return result

    # ── helper used by hosts that create statements directly ──────────

    def _l10n_bg_infopay_group_transactions_into_statement(
        self, transactions: list, balances: list,
        date_from: date, date_until: date, name: str = "",
    ) -> dict:
        """Build a single statement-shaped dict — useful for hosts
        that want one ``account.bank.statement`` per pull.

        Returns:

            {
                "name": "...",
                "date": <date_until>,
                "balance_start": <float | None>,
                "balance_end_real": <float | None>,
                "transactions": [ <normalised line>, ... ],
            }
        """
        bals = self._l10n_bg_infopay_summarize_balances(balances)
        lines = [
            self._l10n_bg_infopay_normalize_transaction(tx)
            for tx in transactions
        ]
        return {
            "name": name or f"InfoPay {date_from} / {date_until}",
            "date": date_until,
            "balance_start": bals["begin"],
            "balance_end_real": bals["end"],
            "transactions": lines,
        }

    # ── dedup helper across imports (mt940 + this provider) ──────────

    def _l10n_bg_infopay_dedup_lines(
        self, lines: list, account_number: str | None = None,
    ) -> list:
        """Strip lines whose ``unique_import_id`` already exists.

        Mirrors ``account.bank.statement.line.unique_import_id``
        constraint logic.  Optionally prefixes the unique id with
        ``account_number`` to avoid cross-journal collisions (matches
        the convention used by the MT940 import).
        """
        if not lines:
            return lines
        BankStatementLine = self.env["account.bank.statement.line"]
        result = []
        for line in lines:
            uid = line.get("unique_import_id")
            if uid and account_number:
                uid = f"{account_number}-{uid}"
                line = dict(line, unique_import_id=uid)
            if uid:
                existing = BankStatementLine.sudo().search(
                    [("unique_import_id", "=", uid)], limit=1,
                )
                if existing:
                    continue
            result.append(line)
        return result
