# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, Command, fields, models, _


class AccountAssetFreezePeriods(models.Model):
    _name = 'bg.account.asset.freeze.periods'
    _description = 'BG Asset Depreciation Board from law defined'

    asset_id = fields.Many2one('account.asset', string='Asset', index=True, ondelete='cascade')
