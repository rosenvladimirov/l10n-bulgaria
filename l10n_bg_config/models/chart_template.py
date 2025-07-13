import logging
import re
from odoo import models
from odoo.addons.account.models.chart_template import template

_logger = logging.getLogger(__name__)

# Константи за префикси на модули
BASE_CONFIG_MODULE = 'l10n_bg_config'
MODULE_PREFIXES = {
    'account': 'l10n_bg_config_acc_',
    'group': 'l10n_bg_config_group_',
    'tax': 'l10n_bg_config_tax_',
    'fiscal_position': 'l10n_bg_config_fp_'
}


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"


    def _get_plugins(self):
        return self.env['ir.module.module'].search([
            ('name', 'like', 'l10n_bg_config_%'),
            ('state', '=', 'installed')
        ]).mapped('name')

    def _get_plugins_by_prefix(self, prefix):
        """Помощен метод за филтриране на модули по префикс"""
        return [m for m in self._get_plugins() if m.startswith(prefix)]

    def _update_data_from_plugins(self, base_data, template_code, model_type, get_data_method):
        """Общ метод за обновяване на данни от плъгини"""
        data = base_data.copy()
        data.update(get_data_method(template_code))

        for plugin in sorted(self._get_plugins_by_prefix(MODULE_PREFIXES[model_type])):
            data.update(get_data_method(template_code, plugin))

        return data

    @template(model='account.account')
    def _get_account_l10n_bg_account(self, template_code, module_plugins=BASE_CONFIG_MODULE):
        return self._parse_csv(template_code, 'account.account', module_plugins)

    @template(model='account.account')
    def _get_account_account(self, template_code):
        return self._update_data_from_plugins(
            super()._get_account_account(template_code),
            template_code,
            'account',
            self._get_account_l10n_bg_account
        )

    @template(model='account.group')
    def _get_account_l10n_bg_account_group(self, template_code, module_plugins=BASE_CONFIG_MODULE):
        return self._parse_csv(template_code, 'account.group', module_plugins)

    @template(model='account.group')
    def _get_account_group(self, template_code):
        return self._update_data_from_plugins(
            super()._get_account_group(template_code),
            template_code,
            'group',
            self._get_account_l10n_bg_account_group
        )

    @template(model='account.tax')
    def _get_account_l10n_bg_tax_admin(self, template_code, module_plugins=BASE_CONFIG_MODULE):
        tax_data = self._parse_csv(template_code, 'account.tax', module_plugins)
        self._deref_account_tags(template_code, tax_data)
        return tax_data

    @template(model='account.tax')
    def _get_account_tax(self, template_code):
        return self._update_data_from_plugins(
            super()._get_account_tax(template_code),
            template_code,
            'tax',
            self._get_account_l10n_bg_tax_admin
        )

    @template(model='account.fiscal.position')
    def _get_account_l10n_bg_fiscal_position(self, template_code, module_plugins=BASE_CONFIG_MODULE):
        return self._parse_csv(template_code, 'account.fiscal.position', module_plugins)

    @template(model='account.fiscal.position')
    def _get_account_fiscal_position(self, template_code):
        return self._update_data_from_plugins(
            super()._get_account_tax(template_code),
            template_code,
            'fiscal_position',
            self._get_account_l10n_bg_fiscal_position
        )
