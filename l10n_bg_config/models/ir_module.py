# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.addons.l10n_bg_config.models.res_company import L10N_BG_MULTILANGUAGE


class Module(models.Model):
    _inherit = "ir.module.module"

    def _button_immediate_function(self, function):
        res = super(Module, self)._button_immediate_function(function)
        if self:
            for module in self.filtered(lambda m: m.name in L10N_BG_MULTILANGUAGE):
                is_l10n_bg_multilanguage = self.env.company.is_l10n_bg_multilanguage or {}
                is_l10n_bg_multilanguage.update({module.name: module.state})
                self.env.company.write(
                    {'is_l10n_bg_multilanguage': is_l10n_bg_multilanguage}
                )
        return res
