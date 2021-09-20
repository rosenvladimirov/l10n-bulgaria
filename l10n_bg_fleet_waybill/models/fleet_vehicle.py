# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _


class FleetVehicle(models.Model):

    _inherit = "fleet.vehicle"

    fuel_city_quantity = fields.Float('City fuel consumption')
    fuel_suburban_quantity = fields.Float('Suburban fuel consumption')
    waybill_count = fields.Integer('Waybills', compute="_compute_waybill_count")

    @api.multi
    def _compute_waybill_count(self):
        for record in self:
            record.waybill_count = self.env['fleet.vehicle.waybill'].search_count([('vehicle_id', '=', record.id)])

    def action_view_waybills(self):
        self.ensure_one()
        action = self.env.ref('l10n_bg_fleet_waybill.fleet_vehicle_waybill_act_window').read()[0]
        action['domain'] = [
            ('vehicle_id', '=', self.id),
        ]
        return action
