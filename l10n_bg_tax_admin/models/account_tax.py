# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from collections import defaultdict

from odoo import _, api, models, fields
from odoo.addons.documents.tests.test_documents import file_a
from odoo.tools.misc import formatLang

_logger = logging.getLogger(__name__)


class AccountTaxGroup(models.Model):
    _inherit = 'account.tax.group'

    tax_tag_ids = fields.Many2many(
        string="Tags",
        comodel_name='account.account.tag',
        ondelete='restrict',
        context={'active_test': False},
        tracking=True,
        help="Tags assigned to this line by the tax creating it, if any. It determines its impact on financial reports.",
    )


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_bg_reverse_charge_vat =  fields.Boolean('Reverse charge with VAT')

    @api.model
    def _prepare_tax_totals_signed(self, base_lines, currency, tax_lines=None):
        """Compute the tax totals details for the business documents.
        :param base_lines:  A list of python dictionaries created using the '_convert_to_tax_base_line_dict' method.
        :param currency:    The currency set on the business document.
        :param tax_lines:   Optional list of python dictionaries created using the '_convert_to_tax_line_dict' method.
                            If specified, the taxes will be recomputed using them instead of recomputing the taxes on
                            the provided base lines.
        :return: A dictionary in the following form:
            {
                'amount_total':                 The total amount to be displayed on the document, including every total
                                                types.
                'amount_untaxed':               The untaxed amount to be displayed on the document.
                'formatted_amount_total':       Same as amount_total, but as a string formatted accordingly with
                                                partner's locale.
                'formatted_amount_untaxed':     Same as amount_untaxed, but as a string formatted accordingly with
                                                partner's locale.
                'groups_by_subtotals':          A dictionary formed liked {'subtotal': groups_data}
                                                Where total_type is a subtotal name defined on a tax group, or the
                                                default one: 'Untaxed Amount'.
                                                And groups_data is a list of dict in the following form:
                    {
                        'tax_group_name':                   The name of the tax groups this total is made for.
                        'tax_group_amount':                 The total tax amount in this tax group.
                        'tax_group_base_amount':            The base amount for this tax group.
                        'formatted_tax_group_amount':       Same as tax_group_amount, but as a string formatted accordingly
                                                            with partner's locale.
                        'formatted_tax_group_base_amount':  Same as tax_group_base_amount, but as a string formatted
                                                            accordingly with partner's locale.
                        'tax_group_id':                     The id of the tax group corresponding to this dict.
                    }
                'subtotals':                    A list of dictionaries in the following form, one for each subtotal in
                                                'groups_by_subtotals' keys.
                    {
                        'name':                             The name of the subtotal
                        'amount':                           The total amount for this subtotal, summing all the tax groups
                                                            belonging to preceding subtotals and the base amount
                        'formatted_amount':                 Same as amount, but as a string formatted accordingly with
                                                            partner's locale.
                    }
                'subtotals_order':              A list of keys of `groups_by_subtotals` defining the order in which it needs
                                                to be displayed
            }
        """

        # ==== Compute the taxes ====
        company_currency = self.env.company.currency_id
        to_process = []
        for base_line in base_lines:
            # _logger.info(f"base_line {base_line}")
            to_update_vals, tax_values_list = self._compute_taxes_for_single_line(
                base_line
            )
            to_process.append((base_line, to_update_vals, tax_values_list))

        def grouping_key_generator(base_line, tax_values):
            source_tax = tax_values["tax_repartition_line"].tax_id
            return {"tax_group": source_tax.tax_group_id}

        global_tax_details = self._aggregate_taxes(
            to_process, grouping_key_generator=grouping_key_generator
        )

        tax_group_vals_list = []
        for tax_detail in global_tax_details["tax_details"].values():
            tax_group_vals = {
                "tax_group": tax_detail["tax_group"],
                "base_amount": tax_detail["base_amount"],
                "tax_amount": tax_detail["tax_amount"],
            }
            tax_amount_currency = (
                tax_detail["tax_amount_currency"] != 0.0
                and tax_detail["tax_amount_currency"]
                or 1.0
            )
            rate = tax_detail["tax_amount"] / tax_amount_currency

            # Handle a manual edition of tax lines.
            if tax_lines is not None:
                matched_tax_lines = [
                    x
                    for x in tax_lines
                    if x["tax_repartition_line"].tax_id.tax_group_id
                    == tax_detail["tax_group"]
                ]
                if matched_tax_lines:
                    tax_amount = tax_amount_signed = 0.0
                    for matched_tax_line in matched_tax_lines:
                        tax_amount += matched_tax_line["tax_amount"]
                        if currency != company_currency:
                            tax_amount_signed += matched_tax_line["tax_amount"] * rate
                        else:
                            tax_amount_signed += matched_tax_line["tax_amount"]

                    tax_group_vals.update(
                        {
                            # 'tax_amount': tax_amount,
                            "tax_amount": tax_amount_signed,
                        }
                    )

            tax_group_vals_list.append(tax_group_vals)

        tax_group_vals_list = sorted(
            tax_group_vals_list,
            key=lambda x: (x["tax_group"].sequence, x["tax_group"].id),
        )

        # ==== Partition the tax group values by subtotals ====

        amount_untaxed = global_tax_details["base_amount"]
        amount_tax = 0.0

        subtotal_order = {}
        groups_by_subtotal = defaultdict(list)
        for tax_group_vals in tax_group_vals_list:
            tax_group = tax_group_vals["tax_group"]

            subtotal_title = tax_group.preceding_subtotal or _("Untaxed Amount")
            sequence = tax_group.sequence

            subtotal_order[subtotal_title] = min(
                subtotal_order.get(subtotal_title, float("inf")), sequence
            )
            groups_by_subtotal[subtotal_title].append(
                {
                    "group_key": tax_group.id,
                    "tax_group_id": tax_group.id,
                    "tax_group_name": tax_group.name,
                    "tax_group_amount": tax_group_vals["tax_amount"],
                    "tax_group_base_amount": tax_group_vals["base_amount"],
                    "formatted_tax_group_amount": formatLang(
                        self.env,
                        tax_group_vals["tax_amount"],
                        currency_obj=company_currency,
                    ),
                    "formatted_tax_group_base_amount": formatLang(
                        self.env,
                        tax_group_vals["base_amount"],
                        currency_obj=company_currency,
                    ),
                }
            )

        # ==== Build the final result ====

        subtotals = []
        for subtotal_title in sorted(
            subtotal_order.keys(), key=lambda k: subtotal_order[k]
        ):
            amount_total = amount_untaxed + amount_tax
            subtotals.append(
                {
                    "name": subtotal_title,
                    "amount": amount_total,
                    "formatted_amount": formatLang(
                        self.env, amount_total, currency_obj=company_currency
                    ),
                }
            )
            for groups_by_subtotal_line in groups_by_subtotal[subtotal_title]:
                amount_tax += groups_by_subtotal_line["tax_group_amount"]

        amount_total = amount_untaxed + amount_tax

        display_tax_base = (
            len(global_tax_details["tax_details"]) == 1
            and company_currency.compare_amounts(
                tax_group_vals_list[0]["base_amount"], amount_untaxed
            )
            != 0
        ) or len(global_tax_details["tax_details"]) > 1
        display_tax_base_signed = currency != company_currency

        return {
            "amount_untaxed": company_currency.round(amount_untaxed),
            "amount_total": company_currency.round(amount_total),
            "formatted_amount_total": formatLang(
                self.env, amount_total, currency_obj=company_currency
            ),
            "formatted_amount_untaxed": formatLang(
                self.env, amount_untaxed, currency_obj=company_currency
            ),
            "groups_by_subtotal": groups_by_subtotal,
            "subtotals": subtotals,
            "subtotals_order": sorted(
                subtotal_order.keys(), key=lambda k: subtotal_order[k]
            ),
            "display_tax_base": display_tax_base,
            "display_tax_base_signed": display_tax_base_signed,
        }
