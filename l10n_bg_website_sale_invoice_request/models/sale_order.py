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
