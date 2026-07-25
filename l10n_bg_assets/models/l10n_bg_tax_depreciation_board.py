# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, Command, fields, models, _


class AccountAssetDepreciationBoard(models.Model):
    _name = 'bg.account.asset.depreciation.board'
    _description = 'BG Asset Depreciation Board from law defined'

    asset_id = fields.Many2one('account.asset', string='Asset', index=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company')

    # Base data for asset
    init_entry = fields.Boolean(string='Initial Entry')
    prorata_date = fields.Date(string='Prorata Date', related='asset_id.prorata_date')
    sequence = fields.Integer(string='Sequence')
    ref = fields.Char(string='Reference', translate=True)
    line_date = fields.Date(string='Period date')

    # Depreciation params
    method_percentage = fields.Float(string='Percentage Depreciation', related='asset_id.l10n_bg_method_percentage')
    original_value = fields.Float(string='Original value')
    salvage_value = fields.Float(string='Salvage value')
    depreciation_value = fields.Float(string='Depreciation value', compute='_compute_depreciation_value', store=True)
    sleep_period_id = fields.Many2one('bg.account.asset.freeze.periods', string='Sleeping period')
    value_residual = fields.Float(string='Value residual')
    value = fields.Float(string='Value')

    @api.depends('depreciation_value', 'salvage_value')
    def _compute_depreciation_value(self):
        for record in self:
            record.depreciation_value = record.original_value * record.salvage_value
