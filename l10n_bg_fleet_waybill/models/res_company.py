# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    cons_location_id = fields.Many2one('stock.location', 'Fuel consumption')

    def __init__(self, pool, cr):
        super(ResCompany, self).__init__(pool, cr)
        cr.execute("SELECT column_name FROM information_schema.columns "
                   "WHERE table_name = 'res_company' AND column_name = 'cons_location_id'")
        if not cr.fetchone():
            cr.execute('ALTER TABLE res_company '
                       'ADD COLUMN cons_location_id integer;')
