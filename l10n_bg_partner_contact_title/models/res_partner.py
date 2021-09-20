# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

import logging
_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = 'res.partner'

    name_with_title = fields.Char("Partner name with title", compute="_compute_name_with_title")
    display_name = fields.Char(compute='_compute_display_name', store=False, index=False)

    api.multi
    def _compute_name_with_title(self):
        country = self.env.user.partner_id.country_id
        for partner in self:
            if country.title_format and not self._context.get('without_company'):
                arg = {
                    'title': partner.title,
                    'partner': partner.display_name,
                    'academic_title_display': partner.academic_title_display,
                }
                return country.title_format % arg
            return partner.display_name

    @api.depends('is_company', 'name', 'parent_id.name', 'type', 'company_name')
    def _compute_display_name(self):
        for partner in self:
            name_en, partner.display_name, lang_name, is_lang = partner._compute_display_name_ext(display=True)
            partner.display_name = partner.name_with_title
