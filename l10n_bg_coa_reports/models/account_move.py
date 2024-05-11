import datetime
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    def _calculate_sales_invoice_totals(self, options):
        # Returns filtered by date and  calculated SALES TOTAL, SALES VAT and SALES COUNT
        invoices = self._filter_invoices_by_date_range(options, self)
        invoices = self._filter_invoices_type(
            options, invoices, ["out_invoice", "out_refund"]
        )

        # SALES TOTAL AMOUNT and SALES VAT TOTAL AMOUNT
        return {
            "sales_total": sum(
                abs(inv.price_subtotal) for inv in invoices.invoice_line_ids
            ),
            "sales_vat_total": sum(abs(inv.amount_tax) for inv in invoices),
        }

    def _calculate_amount_total(self):
        # Returns amount for different type documents
        if self.move_type in ["out_refund", "in_refund"]:
            amount_total = -self.amount_total
        else:
            amount_total = sum(inv.price_subtotal for inv in self.invoice_line_ids)

        return amount_total

    def _calculate_amount_for_different_purchases_taxes(self, options):
        # Calculate and return filtered invoices total amounts of VAT with different tax taxs a given invoice.
        invoices = self._filter_invoices_by_date_range_purchases(options, self)
        invoices = self._filter_invoices_type(
            options, invoices, ["in_invoice", "in_refund"]
        )

        # Define tax tag IDs for different categories
        tax_tag_ids = {
            "amount_tag_41": [38, 39],
            "amount_tag_31": [34, 35],
            "amount_tag_32": [36, 37],
            "amount_tag_42": [40, 41],
            "amount_tag_30": [32, 33],
        }

        # Calculate total amounts for each tax tag
        total_amounts = {}
        for tag, ids in tax_tag_ids.items():
            total_amounts[tag] = sum(
                [
                    abs(line.balance)
                    for line in invoices.line_ids
                    if line.tax_tag_ids.id in ids
                ]
            )

        total_amounts["vat_tax_40"] = sum(
            [
                inv.amount_tax
                for inv in invoices
                if inv.move_type in ["in_invoice", "in_refund"]
            ]
        )
        total_amounts["len"] = len(invoices)

        return total_amounts

    def _calculate_amount_for_different_sales_taxes(self, options):
        # Calculate and return filtered invoices total amounts of VAT with different tax tags a given invoice.
        invoices = self._filter_invoices_type(
            options, self, ["out_invoice", "out_refund"]
        )
        invoices = self._filter_invoices_by_date_range(options, invoices)

        # Define tax tag IDs for different categories
        tag_tax_ids = {
            "amount_tag_11": [4, 5],
            "amount_tag_12_1": [6, 7],
            "amount_tag_12_2": [8, 9],
            "amount_tag_21": [24, 25],
            "amount_tag_22": [26, 27],
            "amount_tag_13": [10, 11],
            "amount_tag_24": [30, 31],
            "amount_tag_14": [12, 13],
            "amount_tag_15": [14, 15],
            "amount_tag_16": [16, 17],
            "amount_tag_17": [18, 19],
            "amount_tag_18": [20, 21],
            "amount_tag_19": [23, 22],
            "amount_tag_23": [28, 29],
        }

        # Calculate total amounts for each tax tag
        total_amounts = {}
        for tag, ids in tag_tax_ids.items():
            total_amounts[tag] = sum(
                [
                    abs(line.balance)
                    for line in invoices.line_ids
                    if line.tax_tag_ids.id in ids
                ]
            )

        total_amounts["len"] = len(invoices)

        return total_amounts

    def _convert_date_string_to_date(self, date_str):
        # Returns convert string to datetime.datetime
        try:
            date_datetime = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            return date_datetime.date()
        except ValueError:
            # Handle invalid date string or format as needed
            raise ValueError("Invalid cast from string to datetime")

    def _get_document_number(self):
        # Returns Invoice numbers
        return self.ref if self.move_type in ["in_invoice", "in_refund"] else self.name

    def _get_document_type(self):
        # Returns invoice type
        return {
            "in_invoice": "01",
            "out_invoice": "01",
            "out_refund": "03",
            "in_refund": "03",
        }.get(self.move_type, None)

    def _filter_invoices_type(self, options, invoices, move_types):
        # Returns filtered invoices
        filtered_invoices = self.filtered(lambda inv: inv.move_type in move_types)

        return filtered_invoices

    def _filter_invoices_by_date_range(self, options, invoices):
        # Returns filtered invoices
        date_from_str = options["date"]["date_from"]
        date_to_str = options["date"]["date_to"]

        date_from_date = self._convert_date_string_to_date(date_from_str)
        date_to_date = self._convert_date_string_to_date(date_to_str)

        filtered_invoices = self.filtered(
            lambda inv: date_from_date <= inv.invoice_date <= date_to_date
        )

        return filtered_invoices

    def _filter_invoices_by_date_range_purchases(self, options, invoices):
        # Returns filtered invoices
        date_from_str = options["date"]["date_from"]
        date_to_str = options["date"]["date_to"]

        date_from_date = self._convert_date_string_to_date(date_from_str)
        date_to_date = self._convert_date_string_to_date(date_to_str)

        filtered_invoices = self.filtered(
            lambda inv: date_from_date <= inv.date <= date_to_date
        )

        return filtered_invoices

    def _l10n_bg_get_amounts(self, company_currency=False):
        """Method used to prepare data to present amounts and taxes related amounts when creating an
        electronic invoice for Bulgarian and the txt files for digital VAT books. Only take into account the Bulgarian taxes"""
        self.ensure_one()
        amount_field = company_currency and "balance" or "amount_currency"
        # if we use balance we need to correct sign (on price_subtotal is positive for refunds and invoices)
        sign = -1 if self.is_inbound() else 1

        # if we are on a document that works invoice and refund and it's a refund, we need to export it as negative
        sign = -sign if self.move_type in ("out_refund", "in_refund") else sign

        tax_lines = self.line_ids.filtered("tax_line_id")
        vat_taxes = tax_lines.filtered(
            lambda r: r.tax_line_id.tax_group_id.l10n_bg_vat_code
        )

        vat_taxable = self.env["account.move.line"]
        for line in self.invoice_line_ids:
            if any(
                tax.tax_group_id.l10n_bg_vat_code
                and tax.tax_group_id.l10n_bg_vat_code not in ["0", "1", "2"]
                for tax in line.tax_ids
            ):
                vat_taxable |= line

        account_tag_11_id = [4, 5]
        account_tag_21_id = [24, 25]

        return {
            "vat_taxes_amount": sign
            * sum((tax_lines - vat_taxes).mapped(amount_field)),
            "vat_tag_11": sum(
                [
                    abs(line.balance)
                    for line in self.line_ids.filtered(
                        lambda r: r.tax_tag_ids.id in account_tag_11_id
                    )
                ]
            ),
            "vat_tag_21": sum(
                [
                    abs(line.balance)
                    for line in self.line_ids.filtered(
                        lambda r: r.tax_tag_ids.id in account_tag_21_id
                    )
                ]
            ),
        }

    def _get_vat(self):
        """Applies on wsfe web service and in the VAT digital books"""
        # if we are on a document that works invoice and refund and it's a refund, we need to export it as negative
        sign = (
            -1
            if self.move_type in ("out_refund", "in_refund")
            and self.l10n_latam_document_type_id.code
            in self._get_l10n_bg_codes_used_for_inv_and_ref()
            else 1
        )

        res = []
        vat_taxable = self.env["account.move.line"]
        # get all invoice lines that are vat taxable
        for line in self.line_ids:
            if (
                any(
                    tax.tax_group_id.l10n_bg_vat_code
                    and tax.tax_group_id.l10n_bg_vat_code not in ["0", "1", "2"]
                    for tax in line.tax_line_id
                )
                and line["amount_currency"]
            ):
                vat_taxable |= line
        for tax_group in vat_taxable.mapped("tax_group_id"):
            base_imp = sum(
                self.invoice_line_ids.filtered(
                    lambda x: x.tax_ids.filtered(
                        lambda y: y.tax_group_id.l10n_bg_vat_code
                        == tax_group.l10n_bg_vat_code
                    )
                ).mapped("price_subtotal")
            )
            imp = abs(
                sum(
                    vat_taxable.filtered(
                        lambda x: x.tax_group_id.l10n_bg_vat_code
                        == tax_group.l10n_bg_vat_code
                    ).mapped("amount_currency")
                )
            )
            res += [
                {
                    "Id": tax_group.l10n_bg_vat_code,
                    "BaseImp": sign * base_imp,
                    "Importe": sign * imp,
                }
            ]

        # Report vat 0%
        vat_base_0 = sum(
            self.invoice_line_ids.filtered(
                lambda x: x.tax_ids.filtered(
                    lambda y: y.tax_group_id.l10n_bg_vat_code == "0"
                )
            ).mapped("price_subtotal")
        )
        if vat_base_0:
            res += [{"Id": "3", "BaseImp": vat_base_0, "Importe": 0.0}]

        return res if res else []

    @api.model
    def _l10n_bg_get_document_number_parts(self, document_number):
        invoice_number = document_number
        return int(invoice_number)

    @api.model
    def _get_l10n_bg_codes_used_for_inv_and_ref(self):
        """List of document types that can be used as an invoice and refund. This list can be increased once needed
        and demonstrated. As far as we've checked document types of wsfev1 don't allow negative amounts so, for example
        document 60 and 61 could not be used as refunds."""
        return [
            "01",
            "02",
            "03",
        ]
