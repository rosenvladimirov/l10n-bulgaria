# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
import logging

import psycopg2

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = "pos.order"

    l10n_bg_wholesale = fields.Boolean(
        string="Wholesale Mode",
        copy=False,
        help="The order was made in the Wholesale mode of the Point of Sale.",
    )
    l10n_bg_is_b2b = fields.Boolean(
        string="Wholesale (B2B) Sale",
        copy=False,
        index=True,
        help="Sale in Wholesale mode or to a business buyer. Such a sale is "
        "always invoiced.",
    )
    l10n_bg_doc_mode = fields.Selection(
        selection=[
            ("odoo_invoice", "Odoo invoice + fiscal receipt"),
            ("fd_invoice", "Fiscal device invoice"),
        ],
        string="Invoice Document",
        default="odoo_invoice",
        copy=False,
    )
    l10n_bg_receipt_kind = fields.Selection(
        selection=[
            ("items", "Receipt with items"),
            ("summary", "Summary receipt"),
            ("none", "No fiscal receipt"),
            ("fd_invoice", "Fiscal device invoice"),
        ],
        string="Fiscal Receipt Kind",
        copy=False,
        help="What was actually printed by the fiscal device for this order.",
    )
    l10n_bg_invoice_ref_on_receipt = fields.Char(
        string="Invoice Reference on Receipt",
        copy=False,
        help="Invoice number and date as printed on the fiscal receipt.",
    )
    l10n_bg_shipping_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Delivery Address",
        copy=False,
        help="Delivery address chosen by the cashier. Empty: the default "
        "delivery address of the customer is used on the invoice.",
    )
    client_order_ref = fields.Char(
        string="Customer Reference",
        copy=False,
        help="Reference given by the customer (purchase order number); it "
        "becomes the reference of the invoice.",
    )
    l10n_bg_credit_override_by = fields.Many2one(
        comodel_name="res.users",
        string="Credit Limit Overridden By",
        copy=False,
    )
    l10n_bg_credit_override_reason = fields.Char(
        string="Credit Limit Override Reason",
        copy=False,
    )
    l10n_bg_guard_ack = fields.Char(
        string="Confirmed Warnings",
        copy=False,
        help="Warnings of the wholesale checks that the cashier confirmed "
        "before payment.",
    )

    # ------------------------------------------------------------------
    # Синхронизация: мрежа за безопасност на сървъра
    # ------------------------------------------------------------------

    @api.model
    def _process_order(self, order, existing_order):
        """Форсира фактура за B2B купувач — без грешка при синхронизация.

        Гардът е на фронтенда, преди плащането (котвата §10). Тук е само
        мрежата за безопасност: платена поръчка към B2B купувач без отметка
        „Invoice“ (стар бъндъл, друг канал, грешка) получава фактура и
        бележка в chatter-а. UserError тук би оставил платената поръчка
        завинаги в буфера на касата (§10.1).
        """
        forced = self._l10n_bg_b2b_prepare_order(order)
        paid = order.get("state") != "draft"
        pos_order_id = super()._process_order(order, existing_order)
        if paid:
            self.browse(pos_order_id)._l10n_bg_b2b_post_sync_notes(forced)
        return pos_order_id

    @api.model
    def _l10n_bg_b2b_prepare_order(self, order):
        """Попълва B2B признака и при нужда `to_invoice` в данните от касата.

        :return: True, ако `to_invoice` е форсиран
        """
        if order.get("state") == "draft":
            return False
        partner = self.env["res.partner"]
        if order.get("partner_id"):
            partner = partner.browse(order["partner_id"]).exists()
        is_buyer = bool(partner and partner.l10n_bg_is_b2b_buyer)
        if not (is_buyer or order.get("l10n_bg_wholesale")):
            return False
        order["l10n_bg_is_b2b"] = True
        if is_buyer and not order.get("to_invoice") and self._l10n_bg_may_force_invoice(order):
            order["to_invoice"] = True
            return True
        return False

    @api.model
    def _l10n_bg_may_force_invoice(self, order):
        """Връщане на продажба без фактура НЕ получава КИ автоматично.

        КИ към несъществуваща фактура не се издава (котвата §16, В14): пътят
        е фактура за оригинала, после КИ — решение на счетоводителя.
        """
        refunded_line_ids = [
            line[2].get("refunded_orderline_id")
            for line in order.get("lines") or []
            if len(line) > 2 and isinstance(line[2], dict) and line[2].get("refunded_orderline_id")
        ]
        if not refunded_line_ids:
            return True
        refunded = self.env["pos.order.line"].browse(refunded_line_ids).exists()
        return all(refunded.order_id.mapped("account_move"))

    def _l10n_bg_b2b_post_sync_notes(self, forced):
        self.ensure_one()
        notes = []
        if forced:
            notes.append(_(
                "Invoice forced by the wholesale (B2B) check: the customer is "
                "a business buyer and the order was not marked for invoicing."
            ))
        if self.l10n_bg_guard_ack:
            notes.append(_(
                "Warnings confirmed by the cashier before payment: %s",
                self.l10n_bg_guard_ack,
            ))
        if self.l10n_bg_credit_override_by:
            notes.append(_(
                "Credit limit exceeded, confirmed by %(user)s: %(reason)s",
                user=self.l10n_bg_credit_override_by.name,
                reason=self.l10n_bg_credit_override_reason or "-",
            ))
        for note in notes:
            self.message_post(body=note)

    def _process_saved_order(self, draft):
        # Контекстът казва на _generate_pos_order_invoice, че сме в sync —
        # само тогава грешката при фактурата се поглъща в savepoint.
        order = self
        if self.l10n_bg_is_b2b and not draft:
            order = self.with_context(l10n_bg_b2b_sync=True)
        return super(PosOrder, order)._process_saved_order(draft)

    # ------------------------------------------------------------------
    # Фактурата: идемпотентност, savepoint, двете дати
    # ------------------------------------------------------------------

    def _generate_pos_order_invoice(self):
        # Идемпотентност (котвата §14): една поръчка → една фактура. Ядрото
        # заключва записите, но не проверява дали фактура вече има.
        if len(self) == 1 and self.account_move:
            return self.account_move
        if len(self) == 1 and self.l10n_bg_is_b2b and self.env.context.get("l10n_bg_b2b_sync"):
            return self._l10n_bg_b2b_generate_invoice_safe()
        return super()._generate_pos_order_invoice()

    def _l10n_bg_b2b_generate_invoice_safe(self):
        """Фактурата при sync в savepoint (котвата §13).

        Изключение от `_post` (заключен период, липсващ реквизит, поредица)
        връща само фактурата: поръчката остава платена, без фактура, в
        справката „B2B orders without invoice“, с причината в chatter-а —
        синхронизацията минава. Не се поглъщат: „поръчката се фактурира в
        момента“ (опитай пак) и грешките на базата при конкурентен достъп
        (механизмът за повторен опит на Odoo трябва да ги види).
        """
        self.ensure_one()
        if not self.env["res.company"]._with_locked_records(self, allow_raising=False):
            raise UserError(_("Some orders are already being invoiced. Please try again later."))
        try:
            with self.env.cr.savepoint():
                return super()._generate_pos_order_invoice()
        except psycopg2.OperationalError:
            raise
        except Exception as error:  # noqa: BLE001 — нарочно: sync не бива да пада
            _logger.warning(
                "Wholesale order %s was synchronised without an invoice: %s",
                self.name, error,
            )
            self.message_post(body=_(
                "The invoice could not be created during synchronisation; "
                "the order stays paid without an invoice. Reason: %s",
                str(error),
            ))
            return self.env["account.move"]

    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()
        if len(self) != 1 or not self.l10n_bg_is_b2b:
            # При сборна фактура (няколко поръчки) датите са на ядрото.
            return vals
        # Две дати (котвата §8.5, ADR specs/pos-b2b-wholesale/0001):
        # дата на издаване = денят, в който фактурата реално се създава
        # (ЗДДС чл. 114, ал. 1, т. 3); дата на данъчното събитие = денят на
        # поръчката (т. 10). Ядрото слага date_order и за издаването, което
        # при офлайн поръчка, синхронизирана на другия ден, дава по-ранна
        # дата на издаване от реалната.
        vals["invoice_date"] = fields.Datetime.context_timestamp(
            self, fields.Datetime.now()
        ).date()
        vals["delivery_date"] = fields.Datetime.context_timestamp(
            self, self.date_order
        ).date()
        if self.l10n_bg_shipping_partner_id:
            vals["partner_shipping_id"] = self.l10n_bg_shipping_partner_id.id
        if self.client_order_ref and not vals.get("reversed_entry_id"):
            vals["ref"] = self.client_order_ref
        return vals
