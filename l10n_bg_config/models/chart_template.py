# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import models
from odoo.addons.account.models.chart_template import template

_logger = logging.getLogger(__name__)

BASE_MODULE = 'l10n_bg_config'
PLUGINS_SUFFIX = '_plugins'


class AccountChartTemplate(models.AbstractModel):
    """
    Represents an abstract model inheriting from 'account.chart.template' with
    additional functionality for template data updates and plugin integration.

    This class provides methods to handle chart template data by considering
    installed plugins and updating the data based on customized logic. It includes
    methods for retrieving and modifying records corresponding to accounts, account
    groups, taxes, and fiscal positions. The data modifications are derived from
    template-specific logic and contextual CSV parsing.

    :ivar _inherit: Inherits the 'account.chart.template' model.
    :type _inherit: Str
    """
    _inherit = "account.chart.template"

    def _get_installed_plugins(self):
        """
        Retrieves a list of names of installed plugins that match the naming convention
        defined by the `BASE_MODULE` and `PLUGINS_SUFFIX` variables. This method searches
        for modules in the system's environment whose names start with the base module
        name and plugins suffix, and whose state is marked as installed.

        :return: A list of installed plugin module names that match the filtering criteria.
        :rtype: list[str]
        """
        return self.env['ir.module.module'].search([
            ('name', 'like', f"{BASE_MODULE}{PLUGINS_SUFFIX}%"),
            ('state', '=', 'installed')
        ]).mapped('name')

    def _update_template_data(self, base_data, template_code, data_getter):
        """
        Updates the provided base data dictionary with additional data fetched
        using a specified template code and data getter. The method also iterates
        over installed plugins, retrieving additional data for each plugin and
        incorporating it into the resultant dictionary.

        :param base_data: A dictionary containing the initial data that will be updated.
        :param template_code: A string identifier for the template, used to fetch
            specific data updates.
        :param data_getter: A callable function that takes the template_code (and
            optionally a plugin) as an argument and returns additional data as a
            dictionary.
        :return: A dictionary that combines the base data with updates retrieved
            using the provided data getter and plugin-specific updates.
        :rtype: dict
        """
        result = base_data.copy()
        result.update(data_getter(template_code))

        for plugin in sorted(self._get_installed_plugins()):
            result.update(data_getter(template_code, plugin))

        return result

    @template(model='account.account')
    def _get_bg_account_data(self, template_code, module=BASE_MODULE):
        return self._parse_csv(template_code, 'account.account', module)

    @template(model='account.account')
    def _get_account_account(self, template_code):
        return self._update_template_data(
            super()._get_account_account(template_code),
            template_code,
            self._get_bg_account_data
        )

    @template(model='account.group')
    def _get_bg_account_group_data(self, template_code, module=BASE_MODULE):
        return self._parse_csv(template_code, 'account.group', module)

    @template(model='account.group')
    def _get_account_group(self, template_code):
        return self._update_template_data(
            super()._get_account_group(template_code),
            template_code,
            self._get_bg_account_group_data
        )

    @template(model='account.tax')
    def _get_bg_tax_data(self, template_code, module=BASE_MODULE):
        tax_data = self._parse_csv(template_code, 'account.tax', module)
        self._deref_account_tags(template_code, tax_data)
        return tax_data

    @template(model='account.tax')
    def _get_account_tax(self, template_code):
        return self._update_template_data(
            super()._get_account_tax(template_code),
            template_code,
            self._get_bg_tax_data
        )

    @template(model='account.fiscal.position')
    def _get_bg_fiscal_position_data(self, template_code, module=BASE_MODULE):
        return self._parse_csv(template_code, 'account.fiscal.position', module)

    @template(model='account.fiscal.position')
    def _get_account_fiscal_position(self, template_code):
        return self._update_template_data(
            super()._get_account_tax(template_code),
            template_code,
            self._get_bg_fiscal_position_data
        )
