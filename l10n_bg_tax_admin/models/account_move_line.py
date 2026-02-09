# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    l10n_bg_move_type = fields.Selection(
        related='move_id.l10n_bg_move_type',
    )

    l10n_bg_price_unit = fields.Monetary(
        string='Unit price currency (balance)',
        compute='_compute_l10n_bg_price_unit',
        store=True,
        readonly=False,
        currency_field='company_currency_id',
        tracking=True,
    )

    # ДАНЪК ВЪРХУ РАЗХОДИ В НАТУРА
    l10n_bg_personal_consumption = fields.Float(
        string='Personal consumption',
        help="Mileage for personal use",
        tracking=True,
    )

    l10n_bg_total_consumption = fields.Float(
        string='Total consumption',
        help="Total kilometers traveled",
        tracking=True,
    )

    l10n_bg_consumption_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of measure',
        domain="[('category_id.name', 'in', ['Length', 'Working Time'])]",
        default=lambda self: self.env.ref('uom.product_uom_km', raise_if_not_found=False),
        help="Unit of measure for measuring consumption (km or hours)"
    )

    l10n_bg_consumption_coefficient = fields.Float(
        string='Coefficient (%)',
        compute='_compute_l10n_bg_consumption_coefficient',
        inverse='_inverse_l10n_bg_consumption_coefficient',
        store=True,
        readonly=False,
        help="Ratio between personal and total consumption in percentage"
    )

    l10n_bg_consumption_coefficient_manual = fields.Float(
        string='Ръчен коефициент (%)',
        help="Manually entered coefficient"
    )

    # Митнически данни
    l10n_bg_customs_value = fields.Monetary(
        string='Customs Value',
        currency_field='company_currency_id',
        compute='_compute_l10n_bg_customs_value',
        inverse='_inverse_l10n_bg_customs_value',
        store=True,
        readonly=False,
        help="Customs value of the goods"
    )

    l10n_bg_customs_value_manual = fields.Monetary(
        string='Manual Customs Value',
        currency_field='company_currency_id',
        help="Manually entered customs value"
    )

    l10n_bg_weight_gross = fields.Float(
        string='Gross Weight (kg)',
        help="Gross weight in kilograms"
    )

    l10n_bg_weight_net = fields.Float(
        string='Net Weight (kg)',
        help="Нето тегло в килограми"
    )

    l10n_bg_customs_procedure_id = fields.Many2one(
        'l10n.bg.customs.nomenclature',
        string='Customs Procedure',
        domain=[('type', '=', 'procedure')],
        help="Customs more rules according to UN/ECE"
    )

    l10n_bg_is_customs_expense = fields.Boolean(
        string='Is Customs Expense',
        help="Notes if this is a customs fee/expense"
    )

    @api.depends('balance')
    def _compute_l10n_bg_price_unit(self):
        for line in self:
            quantity = line.quantity == 0 and 1 or line.quantity
            line.l10n_bg_price_unit = line.balance / quantity

    @api.depends('price_subtotal', 'move_id.l10n_bg_customs_move_id',
                 'l10n_bg_is_customs_expense', 'l10n_bg_customs_value_manual',
                 'move_id.l10n_bg_currency_rate', 'move_id.currency_id')
    def _compute_l10n_bg_customs_value(self):
        """Изчислява митническата стойност пропорционално"""
        for line in self:
            _logger.info("DEBUG VAT: Computing customs_value for line %s (move %s)", line.id, line.move_id.id)
            if line.l10n_bg_customs_value_manual:
                line.l10n_bg_customs_value = line.l10n_bg_customs_value_manual
                _logger.info("DEBUG VAT: Using manual value %s", line.l10n_bg_customs_value)
                continue

            if line.l10n_bg_is_customs_expense:
                line.l10n_bg_customs_value = 0.0
                _logger.info("DEBUG VAT: Is customs expense, value 0.0")
                continue

            customs_move = line.move_id.l10n_bg_customs_move_id

            if not customs_move:
                # Използваме статистическия курс за преизчисление
                currency_rate = line.move_id.l10n_bg_currency_rate or 1.0
                line.l10n_bg_customs_value = line.price_subtotal * currency_rate
                _logger.info("DEBUG VAT: No customs_move, using currency_rate %s. Subtotal %s -> Customs %s",
                             currency_rate, line.price_subtotal, line.l10n_bg_customs_value)
                continue

            total_invoice_amount = sum(
                customs_move.l10n_bg_customs_invoice_ids.mapped('amount_untaxed')
            )

            if total_invoice_amount == 0:
                currency_rate = line.move_id.l10n_bg_currency_rate or 1.0
                line.l10n_bg_customs_value = line.price_subtotal * currency_rate
                _logger.info("DEBUG VAT: Total invoice amount 0, using currency_rate %s. Customs %s",
                             currency_rate, line.l10n_bg_customs_value)
                continue

            total_customs_value = customs_move.total_customs_value or sum(
                customs_move.invoice_line_ids.filtered(
                    lambda l: not l.l10n_bg_is_customs_expense
                ).mapped('price_subtotal')
            )

            proportion = line.price_subtotal / total_invoice_amount if total_invoice_amount else 0
            currency_rate = line.move_id.l10n_bg_currency_rate or 1.0
            line.l10n_bg_customs_value = (total_customs_value * proportion) * currency_rate
            _logger.info("DEBUG VAT: Customs move found. total_customs=%s, total_inv=%s, proportion=%s, rate=%s. Final: %s",
                         total_customs_value, total_invoice_amount, proportion, currency_rate, line.l10n_bg_customs_value)

    def _inverse_l10n_bg_customs_value(self):
        """Позволява ръчно въвеждане на митническа стойност"""
        for line in self:
            if not line.l10n_bg_customs_value:
                line.l10n_bg_customs_value_manual = line.l10n_bg_customs_value

    @api.onchange('l10n_bg_customs_value_manual')
    def _onchange_customs_value_manual(self):
        for line in self:
            if line.l10n_bg_customs_value_manual == 0:
                line.l10n_bg_customs_value_manual = False

    @api.depends('l10n_bg_personal_consumption', 'l10n_bg_total_consumption',
                 'l10n_bg_consumption_coefficient_manual', 'l10n_bg_move_type')
    def _compute_l10n_bg_consumption_coefficient(self):
        """Изчислява коефициента на личната консумация"""
        for line in self:
            if line.l10n_bg_move_type != 'private':
                line.l10n_bg_consumption_coefficient = 0.0
                continue

            if line.l10n_bg_consumption_coefficient_manual:
                line.l10n_bg_consumption_coefficient = line.l10n_bg_consumption_coefficient_manual
                continue

            if not line.l10n_bg_total_consumption or line.l10n_bg_total_consumption == 0:
                line.l10n_bg_consumption_coefficient = 50.0
                continue

            if not line.l10n_bg_personal_consumption or line.l10n_bg_personal_consumption == 0:
                line.l10n_bg_consumption_coefficient = 50.0
                continue

            coefficient = (line.l10n_bg_personal_consumption / line.l10n_bg_total_consumption) * 100.0
            line.l10n_bg_consumption_coefficient = min(max(coefficient, 0.0), 100.0)

    def _inverse_l10n_bg_consumption_coefficient(self):
        for line in self:
            if line.l10n_bg_consumption_coefficient is not False:
                line.l10n_bg_consumption_coefficient_manual = line.l10n_bg_consumption_coefficient

    @api.onchange('l10n_bg_personal_consumption', 'l10n_bg_total_consumption')
    def _onchange_consumption_values(self):
        for line in self:
            if line.l10n_bg_personal_consumption or line.l10n_bg_total_consumption:
                line.l10n_bg_consumption_coefficient_manual = 0.0
