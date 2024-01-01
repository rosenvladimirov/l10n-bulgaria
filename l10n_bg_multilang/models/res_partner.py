# coding: utf-8
import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = 'res.partner'

    display_name_bg = fields.Char(compute='_compute_display_name_bg',
                                  recursive=True,
                                  store=True,
                                  index='trigram')

    @api.depends('is_company', 'name', 'parent_id.display_name_bg', 'type', 'company_name', 'commercial_company_name')
    def _compute_display_name_bg(self):
        # retrieve name_get() without any fancy feature
        lang_name = f'display_name_{self.env.user.lang.split("_")[0]}'
        if lang_name == 'display_name_bg' and lang_name in self._fields:
            names = dict(self.with_context(**dict(self._context, lang=self.env.user.lang)).name_get())
            for partner in self:
                partner.display_name_bg = names.get(partner.id)

    def _auto_init(self):
        self.env["res.partner"]._rec_names_search.extend(['display_name_bg'])
        return super()._auto_init()
