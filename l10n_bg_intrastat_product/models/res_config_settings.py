# Copyright 2017 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# Copyright 2009-2018 Noviat (http://www.noviat.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    intrastat_origin_transport_id = fields.Many2one(
        comodel_name='res.country',
        related='company_id.intrastat_origin_transport_id')
    reporting_level_bg = fields.Selection(
        related='company_id.reporting_level_bg',
        string='BG Reporting Level',)
