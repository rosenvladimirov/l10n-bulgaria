import logging

from odoo import models
from odoo.addons.account.models.chart_template import template

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template(model='account.tax')
    def _get_account_l10n_bg_tax_admin(self, template_code, module_plugins='l10n_bg_admin'):
        tax_data_l10n_bg_config = self._parse_csv(template_code, 'account.tax', module_plugins)
        self._deref_account_tags(template_code, tax_data_l10n_bg_config)
        return tax_data_l10n_bg_config

    @template(model='account.tax')
    def _get_account_tax(self, template_code):
        tax_data = super()._get_account_tax(template_code)
        tax_data.update(self._get_account_l10n_bg_tax_admin(template_code))

        # Install additional plugins
        all_modules = self.env['ir.module.module'].search([
            ('name', 'like', 'l10n_bg_admin_%'),
            ('state', '=', 'installed')
        ])

        plugins_modules = [
            module.name for module in all_modules
            if module.name.startswith('l10n_bg_admin_')
        ]
        for plugins in sorted(plugins_modules):
            tax_data.update(self._get_account_l10n_bg_tax_admin(template_code, plugins))
        return tax_data
