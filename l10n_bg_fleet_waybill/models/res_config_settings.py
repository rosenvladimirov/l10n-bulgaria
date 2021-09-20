# Copyright 2017 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# Copyright 2009-2018 Noviat (http://www.noviat.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cons_location_id = fields.Many2one('stock.location', 'Fuel consumption', related='company_id.cons_location_id')
