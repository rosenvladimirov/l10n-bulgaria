# Copyright 2025 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Borica ``EnumPaymentStatus`` (виж integration_openapi.yaml).
# Авторитетен признак за финалност е ``TransactionStatus.IsFinal``
# (boolean) — тези множества определят само ПОСОКАТА (успех / отказ)
# когато статусът е финален.
INFOPAY_FINAL_OK = frozenset({
    "Processed", "ProcessedInterbank", "Executed",
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
    l10n_bg_infopay_status_url = fields.Char(
        string="InfoPay Status URL",
        readonly=True,
        copy=False,
        help="Линк, върнат от InfoPay (``Links.Status``) за проверка на "
             "статуса на плащането.  Polling-ът го ползва директно "
             "вместо да конструира endpoint — Borica контролира URL-а.",
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

        currency_name = self.currency_id.name
        if currency_name != "EUR":
            raise UserError(
                self.env._(
                    "InfoPay supports only EUR payments since 01.01.2026 "
                    "(BG eurozone entry).  Currency '%s' is not supported.",
                    currency_name,
                )
            )
        country = (
            self.partner_id.country_id.code
            or partner_bank.acc_number[:2]
            or "BG"
        )
        with journal._infopay_session() as (provider, session):
            result = provider._create_sepa_payment(
                session,
                debtor_iban,
                creditor_name,
                creditor_iban,
                self.amount,
                description,
                creditor_country=country,
            )

        links = result.get("Links") or {}
        sca_url = links.get("ScaRedirect")
        self.write({
            "l10n_bg_infopay_payment_id": result.get("PaymentId"),
            "l10n_bg_infopay_sca_url": sca_url,
            "l10n_bg_infopay_status_url": links.get("Status"),
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
        self._l10n_bg_infopay_enqueue_poll()
        return result

    # ── status polling ────────────────────────────────────────────────

    @staticmethod
    def _l10n_bg_infopay_parse_status(result):
        """Извлечи ``(status_str, is_final)`` от status response-а.

        Авторитетен признак за финалност е
        ``TransactionStatus.IsFinal`` (boolean).  ``Status`` enum-ът
        определя само посоката (успех / отказ) когато е финален.
        """
        tx = result.get("TransactionStatus") or {}
        if isinstance(tx, dict):
            status_str = tx.get("Status") or result.get(
                "TransactionState", ""
            )
            is_final = bool(tx.get("IsFinal", False))
        else:
            status_str = result.get("TransactionState", "")
            is_final = False
        return status_str, is_final

    def _l10n_bg_infopay_apply_final_status(self, status_str, is_final):
        """Актуализирай payment документа според финалния статус.

        * финален + успех  → лог (плащането е минало).
        * финален + отказ  → отказва Odoo плащането ако е draft.
        * не-финален       → нищо (продължава polling).
        * финален, но неясен (напр. PartiallyProcessed) → warning,
          оставя за ръчна проверка (не импровизираме счетоводство).
        """
        self.ensure_one()
        if not is_final:
            return
        if status_str in INFOPAY_FINAL_OK:
            _logger.info(
                "InfoPay payment %s completed (%s)",
                self.l10n_bg_infopay_payment_id, status_str,
            )
        elif status_str in INFOPAY_FINAL_FAIL:
            _logger.warning(
                "InfoPay payment %s failed (%s)",
                self.l10n_bg_infopay_payment_id, status_str,
            )
            if self.state == "draft":
                self.action_cancel()
        else:
            _logger.warning(
                "InfoPay payment %s final with unhandled status '%s' — "
                "manual review needed.",
                self.l10n_bg_infopay_payment_id, status_str,
            )

    def _infopay_check_status(self):
        """Poll InfoPay for the current payment status and update the
        record.  Ползва записания ``Links.Status`` URL когато е наличен.

        Returns the raw API response dict.
        """
        self.ensure_one()
        if not self.l10n_bg_infopay_payment_id:
            return {}

        journal = self.journal_id
        with journal._infopay_session() as (provider, session):
            result = provider._get_payment_status(
                session,
                self.l10n_bg_infopay_payment_id,
                bulk=self.l10n_bg_infopay_bulk,
                status_url=self.l10n_bg_infopay_status_url or None,
            )

        status_str, is_final = self._l10n_bg_infopay_parse_status(result)
        self.l10n_bg_infopay_status = status_str
        _logger.info(
            "InfoPay payment %s status: %s (final: %s)",
            self.l10n_bg_infopay_payment_id, status_str, is_final,
        )
        return result

    def _infopay_pull_status(self):
        """Check status for a recordset of payments and handle final
        states (auto-cancel on rejection, log on success).
        """
        for payment in self:
            if not payment.l10n_bg_infopay_payment_id:
                continue
            if payment.l10n_bg_infopay_status in (
                INFOPAY_FINAL_OK | INFOPAY_FINAL_FAIL
            ):
                continue  # already resolved

            try:
                result = payment._infopay_check_status()
            except Exception:
                _logger.exception(
                    "InfoPay status check failed for payment %s (id=%s)",
                    payment.l10n_bg_infopay_payment_id, payment.id,
                )
                continue

            status_str, is_final = payment._l10n_bg_infopay_parse_status(
                result,
            )
            payment._l10n_bg_infopay_apply_final_status(
                status_str, is_final,
            )

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
                                status_url=(
                                    payment.l10n_bg_infopay_status_url
                                    or None
                                ),
                            )
                            status_str, is_final = (
                                payment._l10n_bg_infopay_parse_status(
                                    result,
                                )
                            )
                            payment.l10n_bg_infopay_status = status_str
                            payment._l10n_bg_infopay_apply_final_status(
                                status_str, is_final,
                            )
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

    # async status poll (queue_job via l10n_bg_queue_poll)

    def _l10n_bg_infopay_queue_poll(self):
        """Poll non-final InfoPay payments in ``self`` once and handle
        final states; return True when none remain pending.

        Consumed by ``queue.poll`` -- truthy stops the poll loop.
        """
        resolved = INFOPAY_FINAL_OK | INFOPAY_FINAL_FAIL
        pending = self.filtered(
            lambda p: p.l10n_bg_infopay_payment_id
            and p.l10n_bg_infopay_status not in resolved
        )
        if pending:
            pending._infopay_pull_status()
        still = self.filtered(
            lambda p: p.l10n_bg_infopay_payment_id
            and p.l10n_bg_infopay_status not in resolved
        )
        return not still

    def _l10n_bg_infopay_enqueue_poll(self):
        """Enqueue async status polling with adaptive backoff + live
        refresh of the payment form (l10n_bg_queue_poll).  cron 42 stays
        disabled as a manual safety-net.
        """
        targets = self.filtered("l10n_bg_infopay_payment_id")
        if not targets:
            return
        self.env["queue.poll"].start(
            "account.payment",
            targets.ids,
            "_l10n_bg_infopay_queue_poll",
            refresh={
                "model": "account.payment",
                "res_ids": targets.ids,
                "mode": "record",
            },
            identity_key="infopay-poll-%s" % (
                ",".join(str(i) for i in sorted(targets.ids)),
            ),
        )

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
        if currency_name != "EUR":
            raise UserError(
                self.env._(
                    "InfoPay bulk payments support only EUR since 01.01.2026 "
                    "(BG eurozone entry).  Currency '%s' is not supported.",
                    currency_name,
                )
            )

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
            pay_dicts.append({
                "creditor_name": pay.partner_id.name or "",
                "creditor_iban": partner_bank.acc_number,
                "amount": pay.amount,
                "description": pay.ref or pay.name or "",
                "country": (
                    pay.partner_id.country_id.code
                    or partner_bank.acc_number[:2]
                    or "BG"
                ),
            })

        with journal._infopay_session() as (provider, session):
            result = provider._create_bulk_sepa_payments(
                session, debtor_iban, pay_dicts
            )

        links = result.get("Links") or {}
        self.write({
            "l10n_bg_infopay_payment_id": result.get("PaymentId"),
            "l10n_bg_infopay_sca_url": links.get("ScaRedirect"),
            "l10n_bg_infopay_status_url": links.get("Status"),
            "l10n_bg_infopay_status": result.get("TransactionStatus"),
            "l10n_bg_infopay_bulk": True,
        })
        self._l10n_bg_infopay_enqueue_poll()
        return result
