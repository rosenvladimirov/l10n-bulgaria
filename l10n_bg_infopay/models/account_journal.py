# Copyright 2025 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging
from contextlib import contextmanager
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    """First consumer of the InfoPay statement + payment mixins —
    journals act as both the host for InfoPay account ID + last-sync
    state, and the natural callable for ad-hoc operator-driven
    "Import statements" / "Issue payment" actions.  Bridge modules
    (OCA online provider, EE online account, etc.) inherit the
    mixins separately on their own host model and supply different
    overrides — they do NOT call ``infopay.provider`` directly.
    """

    _name = "account.journal"
    _inherit = [
        "account.journal",
        "l10n.bg.infopay.statement.mixin",
        "l10n.bg.infopay.payment.mixin",
    ]

    l10n_bg_infopay_account_id = fields.Char(
        string="InfoPay Account ID",
        help="UUID of this bank account in InfoPay.  "
             "Set automatically by _infopay_discover_accounts().",
    )
    l10n_bg_infopay_last_sync = fields.Datetime(
        string="InfoPay Last Sync",
        help="Timestamp of the last successful transaction sync.",
    )

    # ── invoice issuance (POST /api/invoices) ─────────────────────────
    # All fields prefixed l10n_bg_ per Rosen rule for additions to core
    # Odoo models.

    l10n_bg_infopay_invoice_enabled = fields.Boolean(
        string="Issue invoices via InfoPay",
        help="When enabled, posted customer invoices on this journal can be "
             "submitted to the InfoPay /api/invoices endpoint.  Use only "
             "with sale journals.",
    )
    l10n_bg_infopay_number_series_id = fields.Char(
        string="InfoPay Number Series",
        help="GUID of the invoice number series pre-created in the InfoPay "
             "portal.  Borica does not expose a list endpoint, so this is "
             "configuration data — copy it from the portal once.",
    )
    # Note: language and payment-method are NOT stored as journal fields —
    # both are derived from the move at payload-build time:
    #   * language: from move.partner_id.lang ("bg_BG" → "BG", else "EN")
    #   * paymentMethod.paymentType: bankTransfer (default for B2B issued
    #     via InfoPay); the IBAN comes from move.partner_bank_id /
    #     journal.bank_account_id / company.bank_ids in that fallback
    #     order.  Cash / card / other variants would need a per-move
    #     override (context flag) — not common enough to warrant fields.

    # ── session helper (legacy, kept for direct callers) ──────────────

    @contextmanager
    def _infopay_session(self, admin=False):
        """Context manager that yields ``(provider, session)``.

        ``admin=False`` (default) uses interactive user credentials
        (wallet, password); ``admin=True`` uses the Fernet-decrypted
        admin token (cron, no password) — see
        ``res.company._l10n_bg_infopay_set_admin_credentials``.

        Prefer the mixin methods (``_l10n_bg_infopay_pull_*``) for new
        code so the bridge architecture stays uniform.  This helper
        survives because callers in ``_infopay_discover_accounts``
        and the cron path still use it for cross-cutting flows.
        """
        provider = self.env["infopay.provider"]
        session = provider._create_session(self.company_id, admin=admin)
        try:
            yield provider, session
        finally:
            provider._close_session(session)

    # ── statement-mixin abstract overrides ────────────────────────────

    def _l10n_bg_infopay_get_company(self):
        self.ensure_one()
        return self.company_id

    def _l10n_bg_infopay_get_account_id(self):
        self.ensure_one()
        if not self.l10n_bg_infopay_account_id:
            raise UserError(self.env._(
                "Journal '%s' has no InfoPay Account ID configured.",
                self.name,
            ))
        return self.l10n_bg_infopay_account_id

    def _l10n_bg_infopay_use_admin_token(self):
        """Journal default: respect the ``infopay_admin`` context flag —
        cron sets it True, interactive UI sets it False.  No flag in
        context → False (safer interactive default).
        """
        return bool(self.env.context.get("infopay_admin", False))

    # ── account discovery ─────────────────────────────────────────────

    def _infopay_discover_accounts(self):
        """Fetch InfoPay accounts and auto-match to journals by IBAN.

        Call once (or periodically) to populate ``l10n_bg_infopay_account_id``.
        Returns a list of dicts with the discovered accounts.
        """
        self.ensure_one()
        with self._infopay_session() as (provider, session):
            accounts = provider._get_accounts(session, with_balance=True)

        from odoo.addons.base.models.res_bank import sanitize_account_number

        for acct in accounts:
            iban = acct.get("IBAN", "")
            sanitized = sanitize_account_number(iban)
            if not sanitized:
                continue
            journal = self.search(
                [
                    ("type", "=", "bank"),
                    ("bank_account_id.sanitized_acc_number", "ilike", sanitized),
                ],
                limit=1,
            )
            if journal and not journal.l10n_bg_infopay_account_id:
                journal.l10n_bg_infopay_account_id = acct["AccountId"]
                _logger.info(
                    "InfoPay account %s (%s) → journal %s",
                    acct["AccountId"],
                    iban,
                    journal.name,
                )
        return accounts

    # ── statement sync ────────────────────────────────────────────────

    def _infopay_sync_statements(
        self, date_from=None, date_to=None, admin=False,
    ):
        """Fetch transactions from InfoPay and create bank statement lines.

        ``admin=False`` (default) — uses interactive user credentials;
        suitable for the "Import" UI button after the operator unlocks
        their wallet.

        ``admin=True`` — uses the Fernet-decrypted admin token; the
        cron path takes this so it can run without a user session.

        Returns list of created ``account.bank.statement`` IDs.
        """
        self.ensure_one()
        if not self.l10n_bg_infopay_account_id:
            raise UserError(
                self.env._(
                    "Journal '%s' has no InfoPay Account ID configured.",
                    self.name,
                )
            )

        today = fields.Date.context_today(self)
        if date_to is None:
            date_to = today
        if date_from is None:
            if self.l10n_bg_infopay_last_sync:
                date_from = self.l10n_bg_infopay_last_sync.date()
            else:
                date_from = date_to - timedelta(days=30)

        with self._infopay_session(admin=admin) as (provider, session):
            transactions, balances = provider._get_transactions(
                session, self.l10n_bg_infopay_account_id, date_from, date_to
            )

        if not transactions:
            _logger.info("InfoPay: no transactions for %s (%s → %s)",
                         self.name, date_from, date_to)
            self.l10n_bg_infopay_last_sync = fields.Datetime.now()
            return []

        stmts_vals = self._infopay_prepare_stmts_vals(
            transactions, balances, date_from, date_to
        )
        account_number = (
            self.bank_account_id.acc_number if self.bank_account_id else None
        )
        stmts_vals = self._infopay_complete_stmts_vals(stmts_vals, account_number)
        statement_ids = self._infopay_create_bank_statements(stmts_vals)

        self.l10n_bg_infopay_last_sync = fields.Datetime.now()
        _logger.info(
            "InfoPay: synced %d transactions → %d statements for %s",
            len(transactions),
            len(statement_ids),
            self.name,
        )
        return statement_ids

    # ── transaction → statement conversion ────────────────────────────

    def _infopay_prepare_transaction_line(self, tx):
        """Convert a single InfoPay transaction dict to a statement line dict."""
        amount = float(tx["TransactionAmount"]["amount"])
        tx_type = tx.get("TransactionType")

        # Ensure correct sign: Credit → positive, Debit → negative
        if tx_type == "Debit" and amount > 0:
            amount = -amount
        elif tx_type == "Credit" and amount < 0:
            amount = -amount

        # Counterparty: for incoming → debtor, for outgoing → creditor
        if tx_type == "Credit":
            account_number = tx.get("DebtorAccount") or ""
            partner_name = tx.get("DebtorName") or ""
        else:
            account_number = tx.get("CreditorAccount") or ""
            partner_name = tx.get("CreditorName") or ""

        # Build payment reference from available fields
        payment_ref = (
            tx.get("RemittanceInformationUnstructured")
            or tx.get("EntryReference")
            or partner_name
            or "/"
        )

        # Unique ID: prefer TransactionExternalId, fallback to TransactionId
        unique_id = tx.get("TransactionExternalId") or tx.get("TransactionId") or ""

        booking_date = tx.get("BookingDate")
        if booking_date:
            # "2024-01-15T00:00:00" → "2024-01-15"
            booking_date = booking_date[:10]

        vals = {
            "date": booking_date,
            "payment_ref": payment_ref,
            "amount": amount,
            "account_number": account_number,
            "partner_name": partner_name,
        }
        if unique_id:
            vals["unique_import_id"] = unique_id
        return vals

    def _infopay_prepare_stmts_vals(self, transactions, balances, date_from, date_to):
        """Group transactions into a single statement dict."""
        self.ensure_one()
        iban = self.bank_account_id.acc_number if self.bank_account_id else "?"

        lines = [self._infopay_prepare_transaction_line(tx) for tx in transactions]

        stmt = {
            "name": f"InfoPay {iban} {date_from} / {date_to}",
            "date": date_to,
            "transactions": lines,
        }

        # Try to extract balance info
        for bal in balances:
            bal_type = bal.get("BalanceType")
            bal_amount = bal.get("BalanceAmount", {})
            try:
                val = float(bal_amount.get("amount", 0))
            except (ValueError, TypeError):
                continue
            if bal_type == "BeginDay":
                stmt["balance_start"] = val
            elif bal_type in ("ActualBalance", "AvailableBalance"):
                stmt["balance_end_real"] = val

        return [stmt]

    def _infopay_complete_stmts_vals(self, stmts_vals, account_number):
        """Fill journal_id and ensure unique_import_id prefix."""
        self.ensure_one()
        for st_vals in stmts_vals:
            st_vals["journal_id"] = self.id
            for lvals in st_vals["transactions"]:
                lvals["journal_id"] = self.id
                # Prefix unique_import_id with account number to avoid cross-journal collisions
                uid = lvals.get("unique_import_id")
                if uid and account_number:
                    lvals["unique_import_id"] = f"{account_number}-{uid}"
                if not lvals.get("payment_ref"):
                    lvals["payment_ref"] = "/"
        return stmts_vals

    def _infopay_create_bank_statements(self, stmts_vals):
        """Create bank statements, skipping duplicate lines.

        Mirrors ``account.statement.import._create_bank_statements``.
        """
        self.ensure_one()
        BankStatement = self.env["account.bank.statement"]
        BankStatementLine = self.env["account.bank.statement.line"]
        statement_ids = []

        for st_vals in stmts_vals:
            lines_to_create = []
            for lvals in st_vals["transactions"]:
                if lvals.get("unique_import_id"):
                    existing = BankStatementLine.sudo().search(
                        [("unique_import_id", "=", lvals["unique_import_id"])],
                        limit=1,
                    )
                    if existing:
                        if "balance_start" in st_vals:
                            st_vals["balance_start"] += float(lvals["amount"])
                        continue
                lines_to_create.append(lvals)

            if not lines_to_create:
                continue

            for seq, vals in enumerate(lines_to_create, start=1):
                vals["sequence"] = seq
            st_vals.pop("transactions", None)
            st_vals["line_ids"] = [(0, 0, line) for line in lines_to_create]
            statement = BankStatement.create(st_vals)
            statement_ids.append(statement.id)

        return statement_ids

    # ── batch sync (called from UI module) ───────────────────────────

    @api.model
    def _infopay_sync_all_statements(self, admin=True):
        """Sync every journal that has an InfoPay account configured.

        Called from cron + UI buttons.  Defaults to ``admin=True``
        because the cron path has no user session — pass ``admin=False``
        from interactive UI buttons that have just unlocked the wallet.
        """
        all_ids = []
        journals = self.search([("l10n_bg_infopay_account_id", "!=", False)])
        for journal in journals:
            try:
                all_ids.extend(journal._infopay_sync_statements(admin=admin))
            except Exception:
                _logger.exception(
                    "InfoPay sync failed for journal %s (id=%s)",
                    journal.name, journal.id,
                )
        return all_ids
