# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.addons.l10n_bg_config.models.res_company import L10N_BG_MULTILANGUAGE


class Module(models.Model):
    _inherit = "ir.module.module"

    @api.onchange('state')
    def _onchange_state(self):
        if self.state == 'installed':
            if self.name in L10N_BG_MULTILANGUAGE:
                self.env.company.write({'is_l10n_bg_multilanguage': self.state == 'installed'})
