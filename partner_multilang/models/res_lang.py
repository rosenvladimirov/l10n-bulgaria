# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class Lang(models.Model):
    _inherit = "res.lang"

    transliterate = fields.Boolean(string="Transliterate")

    @api.model_create_multi
    def create(self, vals_list):
        langs = super().create(vals_list)
        langs.filtered("active")._pm_ensure_partner_order_indexes()
        return langs

    def write(self, vals):
        res = super().write(vals)
        if vals.get("active"):
            self._pm_ensure_partner_order_indexes()
        return res

    def _pm_ensure_partner_order_indexes(self):
        # Нов активен език → индекс за сортиране на партньорите по него.
        if self:
            self.env["res.partner"]._pm_ensure_order_indexes(self.mapped("code"))
