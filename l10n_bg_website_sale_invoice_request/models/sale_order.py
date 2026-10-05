# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
import logging

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

SALES_REPORT_DOCUMENT_TYPE = "81"


class SaleOrder(models.Model):
    _inherit = "sale.order"

    l10n_bg_invoice_requested = fields.Boolean(
        string="Invoice Requested",
        copy=False,
        help="The customer asked for an invoice on checkout. Website orders without it are "
        "invoiced at the end of the month to the random customer as a sales report "
        "(Art. 119 VAT Act, document type 81).",
    )

    def _l10n_bg_random_customer(self):
        return self.env.ref("l10n_bg_config.partner_random_customer", raise_if_not_found=False)

    def action_confirm(self):
        # Checkout-ът на Odoo сменя адреса за фактура при всеки избор на адрес,
        # затова подмяната със „Случаен клиент“ става едва при потвърждаване
        # (ADR l10n-bg-sales-report-119/0001)
        random_customer = self._l10n_bg_random_customer()
        if random_customer:
            for order in self.filtered(
                lambda o: o.website_id
                and not o.l10n_bg_invoice_requested
                and o.company_id.country_id.code == "BG"
                and o.state in ("draft", "sent")
            ):
                order.partner_invoice_id = random_customer
        return super().action_confirm()

    # --- „Искам фактура“: клиентът на поръчката става фирмата (Росен, 05.10.2026) ---

    def _l10n_bg_delivery_person(self):
        self.ensure_one()
        return self.partner_shipping_id if self.partner_id.is_company else self.partner_id

    def _l10n_bg_invoice_company(self):
        """Фирмата за фактура: клиентът, ако вече е фирма с ЕИК или ДДС, иначе нищо."""
        self.ensure_one()
        commercial = self.partner_id.commercial_partner_id
        if commercial.is_company and (commercial.l10n_bg_uic or commercial.vat):
            return commercial
        return self.env["res.partner"]

    def _l10n_bg_visible_partners(self):
        """При поръчка към фирма купувачът вижда само фирмата, себе си и своите
        адреси — не и другите контакти на фирмата (Росен, 05.10.2026)."""
        self.ensure_one()
        if not (self.l10n_bg_invoice_requested and self.partner_id.is_company):
            return False
        person = self._l10n_bg_delivery_person()
        own = self.env["res.partner"].sudo().search([("id", "child_of", person.id)])
        return self.partner_id | person | own

    def _l10n_bg_find_company(self, uic, vat):
        Partner = self.env["res.partner"].sudo().with_context(active_test=False)
        domain = [("is_company", "=", True), ("parent_id", "=", False)]
        if uic:
            found = Partner.search(domain + [("l10n_bg_uic", "=", uic)], limit=1)
            if found:
                return found
        if vat:
            return Partner.search(domain + [("vat", "=", vat)], limit=1)
        return Partner

    def _l10n_bg_set_invoice_company(self, values):
        """Фирмата от формата „Фирма за фактура“: заварена по ЕИК/ДДС или нова.
        Заварените данни не се презаписват — допълват се само празните полета."""
        self.ensure_one()
        person = self._l10n_bg_delivery_person()
        uic, vat = values.get("l10n_bg_uic"), values.get("vat")
        company = self._l10n_bg_find_company(uic, vat)
        data = {
            "name": values["name"],
            "is_company": True,
            "l10n_bg_uic": uic or False,
            "l10n_bg_uic_type": "bg_uic" if uic and uic.isdigit() and len(uic) in (9, 13) else False,
            "vat": vat or False,
            "street": values.get("street") or False,
            "city": values.get("city") or False,
            "zip": values.get("zip") or False,
            "country_id": values.get("country_id") or False,
            # имейлът е задължителен за адреса за фактура в магазина
            "email": person.email or False,
            "phone": person.phone or False,
        }
        if company:
            company.write({k: v for k, v in data.items() if v and not company[k]})
        else:
            company = self.env["res.partner"].sudo().with_context(no_vat_validation=True).create(data)
        self._l10n_bg_bind_invoice_company(company)
        return company

    def _l10n_bg_bind_invoice_company(self, company):
        """Клиентът става фирмата, лицето — неин адрес за доставка, фактурата — към фирмата."""
        self.ensure_one()
        person = self._l10n_bg_delivery_person()
        if person != company and person.parent_id != company:
            person.sudo().write({"parent_id": company.id, "type": "delivery"})
        self.write({
            "partner_id": company.id,
            "partner_invoice_id": company.id,
            "partner_shipping_id": person.id,
            "l10n_bg_invoice_requested": True,
        })

    def _l10n_bg_unset_invoice_company(self):
        """Без фактура: поръчката се връща към лицето (фирмата остава в базата)."""
        self.ensure_one()
        person = self._l10n_bg_delivery_person()
        self.write({
            "partner_id": person.id,
            "partner_invoice_id": person.id,
            "partner_shipping_id": person.id,
            "l10n_bg_invoice_requested": False,
        })

    @api.model
    def _cron_l10n_bg_invoice_random_customer(self):
        # Месечната фактура към „Случаен клиент“: всички потвърдени поръчки до
        # края на предходния месец, групирани по стандартния механизъм на Odoo,
        # вид 81, дата — последният ден на месеца
        random_customer = self._l10n_bg_random_customer()
        if not random_customer:
            return
        first_of_month = fields.Date.context_today(self).replace(day=1)
        invoice_date = first_of_month - relativedelta(days=1)
        companies = self.env["res.company"].search([]).filtered(lambda c: c.country_id.code == "BG")
        for company in companies:
            orders = self.with_company(company).search([
                ("company_id", "=", company.id),
                ("state", "=", "sale"),
                ("partner_invoice_id", "=", random_customer.id),
                # „нищо за фактуриране“ = неекспедирано при политика „по доставка“
                ("invoice_status", "in", ("to invoice", "no")),
                ("date_order", "<", fields.Datetime.to_datetime(first_of_month)),
            ])
            if not orders:
                continue
            try:
                with self.env.cr.savepoint():
                    orders._l10n_bg_create_sales_report(invoice_date)
            except Exception:
                _logger.exception("Monthly sales report failed for company %s", company.name)

    def _l10n_bg_create_sales_report(self, invoice_date):
        # „Всички потвърдени“ (Росен, 04.10.2026): фактурира се поръчаното,
        # не само експедираното
        self._force_lines_to_invoice_policy_order()
        moves = self.with_context(raise_if_nothing_to_invoice=False)._create_invoices(final=True)
        moves.write({
            "invoice_date": invoice_date,
            "l10n_bg_document_type": SALES_REPORT_DOCUMENT_TYPE,
        })
        moves.action_post()
        return moves
