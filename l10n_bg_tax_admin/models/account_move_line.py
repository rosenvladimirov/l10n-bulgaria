#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.tools import frozendict


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    # === Price fields company currency === #
    price_unit_signed = fields.Float(
        string='Unit Price in company currency',
        compute="_compute_price_unit_signed", store=True, readonly=False, precompute=True,
        digits='Product Price',
    )
    price_subtotal_signed = fields.Monetary(
        string='Subtotal in company currency',
        compute='_compute_totals_signed', store=True,
        currency_field='company_currency_id',
    )
    price_total_signed = fields.Monetary(
        string='Total in company currency',
        compute='_compute_totals_signed', store=True,
        currency_field='company_currency_id',
    )

    @api.depends('price_unit', 'move_id.l10n_bg_protocol_invoice_id')
    def _compute_price_unit_signed(self):
        for line in self:
            if line.currency_id == line.company_id.currency_id:
                line.price_unit_signed = line.price_unit
            else:
                line.price_unit_signed = line.company_id.currency_id.round(line.price_unit / line.currency_rate)

    @api.depends('quantity', 'discount', 'price_unit', 'tax_ids', 'currency_id', 'move_id.l10n_bg_protocol_invoice_id')
    def _compute_totals_signed(self):
        for line in self:
            if line.display_type != 'product':
                line.price_total_signed = line.price_subtotal_signed = False
            else:
                subtotal = line.company_id.currency_id.round(line.amount_currency / line.currency_rate)
                # Compute 'price_total_signed'.
                if line.tax_ids:
                    taxes_res = line.tax_ids.compute_all(
                        subtotal,
                        quantity=1.0,
                        currency=line.currency_id,
                        product=line.product_id,
                        partner=line.partner_id,
                        is_refund=line.is_refund,
                    )
                    line.price_subtotal_signed = taxes_res['total_excluded']
                    line.price_total_signed = taxes_res['total_included']
                else:
                    line.price_total_signed = line.price_subtotal_signed = subtotal

    @api.onchange("amount_currency", "currency_id", "currency_rate")
    def _inverse_amount_currency(self):
        res = super()._inverse_amount_currency()
        for line in self:
            if (
                line.currency_id != line.company_id.currency_id
                and line.move_id.l10n_bg_type_vat in ('in_customs', 'out_customs')
                and self._context.get("statistic_rate")
            ):
                line.balance = line.company_id.currency_id.round(
                    line.amount_currency / line.currency_rate
                )
        return res

    @api.depends('tax_ids', 'currency_id', 'partner_id', 'analytic_distribution', 'balance', 'partner_id',
                 'move_id.partner_id', 'price_unit', 'quantity')
    def _compute_all_tax(self):
        for line in self:
            sign = line.move_id.direction_sign
            if line.display_type in ['tax', 'cogs']:
                line.compute_all_tax = {}
                line.compute_all_tax_dirty = False
                continue
            if line.display_type == 'product' and line.move_id.is_invoice(True):
                amount_currency = sign * line.price_unit * (1 - line.discount / 100)
                handle_price_include = True
                quantity = line.quantity
            else:
                amount_currency = line.amount_currency
                handle_price_include = False
                quantity = 1
            compute_all_currency = line.tax_ids.compute_all(
                amount_currency,
                currency=line.currency_id,
                quantity=quantity,
                product=line.product_id,
                partner=line.move_id.partner_id or line.partner_id,
                is_refund=line.is_refund,
                handle_price_include=handle_price_include,
                include_caba_tags=line.move_id.always_tax_exigible,
                fixed_multiplicator=sign,
            )
            rate = line.amount_currency / line.balance if line.balance else 1
            line.compute_all_tax_dirty = True
            line.compute_all_tax = {
                frozendict({
                    'tax_repartition_line_id': tax['tax_repartition_line_id'],
                    'group_tax_id': tax['group'] and tax['group'].id or False,
                    'account_id': tax['account_id'] or line.account_id.id,
                    'currency_id': line.currency_id.id,
                    'analytic_distribution': ((tax['analytic'] or not tax[
                        'use_in_tax_closing']) and line.move_id.state == 'draft') and line.analytic_distribution,
                    'tax_ids': [(6, 0, tax['tax_ids'])],
                    'tax_tag_ids': [(6, 0, tax['tag_ids'])],
                    'partner_id': line.move_id.partner_id.id or line.partner_id.id,
                    'move_id': line.move_id.id,
                    'display_type': line.display_type,
                }): {
                    'name': tax['name'] + (' ' + _('(Discount)') if line.display_type == 'epd' else ''),
                    'balance': tax['amount'] / rate,
                    'amount_currency': tax['amount'],
                    'tax_base_amount': tax['base'] / rate * (-1 if line.tax_tag_invert else 1),
                }
                for tax in compute_all_currency['taxes']
                if tax['amount']
            }
            if not line.tax_repartition_line_id:
                line.compute_all_tax[frozendict({'id': line.id})] = {
                    'tax_tag_ids': [(6, 0, compute_all_currency['base_tags'])],
                }

    @api.depends('currency_id', 'company_id', 'move_id.date')
    def _compute_currency_rate(self):
        if self.move_id.l10n_bg_type_vat == 'in_customs':
            self.currency_rate = self.move_id.l10n_bg_currency_rate
        else:
            super()._compute_currency_rate()
