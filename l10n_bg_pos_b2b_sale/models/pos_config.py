# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from datetime import datetime, time

import pytz
from markupsafe import escape

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command

# Справките, които касата показва в десния екран (ADR 0003, фаза 1)
L10N_BG_B2B_REPORTS = {
    "quotation": "sale.report_saleorder",
    "pro_forma": "sale.report_saleorder_pro_forma",
}


class PosConfig(models.Model):
    _inherit = "pos.config"

    def l10n_bg_b2b_save_quotation(self, payload):
        """Записва поръчката на едро от касата като чернова SO (оферта).

        Създава нова или обновява вече записаната — само докато е чернова
        или изпратена. Стойностите от формата минават през същата проверка
        като при синхронизацията на поръчката (`_l10n_bg_b2b_unpack_form`).
        Редовете се заменят изцяло; цената и отстъпката са тези от касата.

        :return: id, номер и състояние на SO и адресите на печатите
        """
        self.ensure_one()
        partner = self.env["res.partner"].browse(payload.get("partner_id")).exists()
        if not partner:
            raise UserError(_("Choose the customer before saving the quotation."))
        lines = [line for line in payload.get("lines") or [] if line.get("product_id")]
        if not lines:
            raise UserError(_("Add at least one product before saving the quotation."))

        checked = {
            "partner_id": partner.id,
            "session_id": self.current_session_id.id,
            "l10n_bg_b2b_form": payload.get("form") or {},
        }
        self.env["pos.order"]._l10n_bg_b2b_unpack_form(checked)

        SaleOrder = self.env["sale.order"]
        order = SaleOrder.browse(payload.get("sale_order_id") or []).exists()
        if order and order.state not in ("draft", "sent"):
            raise UserError(_(
                "The quotation %s is already confirmed and cannot be changed "
                "from the Point of Sale.", order.name,
            ))

        commercial = partner.commercial_partner_id
        vals = {
            "partner_id": partner.id,
            "partner_invoice_id": checked.get("l10n_bg_invoice_partner_id")
            or commercial.address_get(["invoice"])["invoice"],
            "partner_shipping_id": checked.get("l10n_bg_shipping_partner_id")
            or commercial.address_get(["delivery"])["delivery"],
            "user_id": checked.get("l10n_bg_salesperson_id") or self.env.user.id,
            "warehouse_id": checked.get("l10n_bg_warehouse_id") or self.warehouse_id.id,
            "client_order_ref": payload.get("client_order_ref") or False,
            "origin": payload.get("pos_reference") or False,
            "company_id": self.company_id.id,
            "team_id": self.crm_team_id.id or False,
        }
        pricelist = self.env["product.pricelist"].browse(payload.get("pricelist_id") or []).exists()
        if pricelist:
            vals["pricelist_id"] = pricelist.id
        if checked.get("l10n_bg_payment_term_id"):
            vals["payment_term_id"] = checked["l10n_bg_payment_term_id"]
        if checked.get("l10n_bg_validity_date"):
            vals["validity_date"] = checked["l10n_bg_validity_date"]
        if checked.get("l10n_bg_b2b_note"):
            vals["note"] = escape(checked["l10n_bg_b2b_note"]).replace("\n", "<br/>")
        shipping_date = payload.get("shipping_date")
        if shipping_date:
            day = fields.Date.to_date(str(shipping_date)[:10])
            local = self.env.tz.localize(datetime.combine(day, time(12, 0)))
            vals["commitment_date"] = local.astimezone(pytz.UTC).replace(tzinfo=None)

        vals["order_line"] = self._l10n_bg_b2b_quotation_line_commands(order, lines)
        if order:
            order.write(vals)
        else:
            order = SaleOrder.create(vals)
        return {
            "id": order.id,
            "name": order.name,
            "state": order.state,
            "state_label": dict(order._fields["state"]._description_selection(self.env)).get(order.state),
            "reports": {
                key: f"/report/pdf/{report}/{order.id}"
                for key, report in L10N_BG_B2B_REPORTS.items()
            },
            "lines": {
                line.l10n_bg_pos_line_uuid: {
                    "id": line.id,
                    "price_unit": line.price_unit,
                    "discount": line.discount,
                }
                for line in order.order_line
                if line.l10n_bg_pos_line_uuid
            },
        }

    def _l10n_bg_b2b_quotation_line_commands(self, order, lines):
        """Редовете на офертата се обновяват НА МЯСТО по реда в касата.

        Връзката е `l10n_bg_pos_line_uuid`: съществуващ ред се обновява,
        нов се създава, изтритият в касата се трие. Пълна подмяна би
        загубила всичко, закачено за реда (напр. конфигурация POC).
        """
        existing = {
            line.l10n_bg_pos_line_uuid: line
            for line in order.order_line
            if line.l10n_bg_pos_line_uuid
        }
        commands = []
        seen = set()
        for line in lines:
            uuid = line.get("uuid")
            so_line = existing.get(uuid) if uuid else None
            vals = self._l10n_bg_b2b_quotation_line(line, so_line)
            if so_line:
                commands.append(Command.update(so_line.id, vals))
                seen.add(uuid)
            else:
                commands.append(Command.create(vals))
        # трият се само редовете, дошли от касата; добавените в Продажби
        # (без връзка към касата) остават
        for line in order.order_line:
            if line.l10n_bg_pos_line_uuid and line.l10n_bg_pos_line_uuid not in seen:
                commands.append(Command.delete(line.id))
        return commands

    def _l10n_bg_b2b_quotation_line(self, line, so_line=None):
        """Стойностите на реда от касата. `so_line` — заварен ред или None."""
        vals = {
            "product_uom_qty": line.get("qty") or 0.0,
            "price_unit": line.get("price_unit") or 0.0,
            "discount": line.get("discount") or 0.0,
            "l10n_bg_pos_line_uuid": line.get("uuid") or False,
        }
        if not so_line or so_line.product_id.id != line["product_id"]:
            vals["product_id"] = line["product_id"]
        # Мерната на реда в касата: при пакет количеството и цената са за
        # кашон. Без нея редът в офертата остава в мерната на артикула и
        # „2 кашона по 54,00“ става „2 бройки по 54,00“.
        if line.get("product_uom_id"):
            vals["product_uom_id"] = line["product_uom_id"]
        return vals
