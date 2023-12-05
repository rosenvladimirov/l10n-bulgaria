# coding: utf-8
import logging

from odoo import api, fields, models, _
from .iso9 import transliterate

_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = 'res.partner'

    display_name_bg = fields.Char(compute='_compute_display_name',
                                  recursive=True,
                                  store=True,
                                  index='trigram')

    @api.depends('is_company', 'name', 'parent_id.display_name_bg', 'type', 'company_name', 'commercial_company_name')
    def _compute_display_name(self):
        # retrieve name_get() without any fancy feature
        ctx = {}
        lang_name = f'display_name_{self.env.user.lang.split("_")[0]}'
        if lang_name in self._fields:
            ctx = {'lang': self.env.user.lang}
        names = dict(self.with_context(ctx).name_get())
        for partner in self:
            partner.display_name_bg = names.get(partner.id)

    def _auto_init(self):
        self.env["res.partner"]._rec_names_search.extend(['display_name_bg'])
        return super()._auto_init()

    def partner_name_translate(self, name):
        name = super().partner_name_translate(name)
        lang_name = f'display_name_{self.env.user.lang.split("_")[0]}'
        if lang_name in self._fields:
            return transliterate(name)
        return name

    # @api.model
    # def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
    #     args = args or []
    #     domain = []
    #     if name:
    #         # Be sure name_search is symmetric to name_get
    #         name = name.split(' / ')[-1]
    #         lang_name = f'display_name_{self.env.user.sudo().lang.split("_")[0]}'
    #         if lang_name in DIFFERENT_LETTERS and lang_name in self._fields:
    #             domain = [
    #                 "|",
    #                 (lang_name, operator, name),
    #                 ('name', operator, name)
    #             ]
    #             if operator in expression.NEGATIVE_TERM_OPERATORS:
    #                 domain = ["&", "!"] + domain[1:]
    #         else:
    #             domain = [('name', operator, name)]
    #     return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
