# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re

from odoo import models
from odoo.addons.account.models.chart_template import template
from itertools import zip_longest

_logger = logging.getLogger(__name__)

BASE_MODULE = 'l10n_bg_config'
PLUGINS_SUFFIX = '_plugins'


def apply_mask_zip(
        value: str,
        mask: str,
        placeholder: str = '#',
        target_len: int | None = None,
        fill_char: str | None = None,
) -> str:
    """
    Форматира 'value' по дадена 'mask', като:
      • пропуска разделителите от маската, ако няма оставащи цифри;
      • допълва липсващи позиции с fill_char;
      • НЕ брои вече присъстващи разделители във value.
    """
    # ----------- Премахваме всички нецифрови символи от входа -----------
    raw_value = re.sub(r'\D', '', value)       # само цифри
    value = raw_value                          # занапред работим с прочистен низ

    # ----------- Изчисляване на минималната изисквана дължина -----------
    placeholders = mask.count(placeholder)
    min_len = placeholders if target_len is None else max(placeholders, target_len)

    # ----------- Допълване, ако е необходимо -----------
    if len(value) < min_len:
        if fill_char is None:
            fill_char = value[-1] if value else '0'
        value += fill_char * (min_len - len(value))

    # ----------- Прилагане на маската -----------
    digits = iter(value)
    result, pending_sep = [], None

    for m_ch, d_ch in zip_longest(mask, digits, fillvalue=None):
        if m_ch == placeholder:            # позиция за цифра
            if d_ch is None:
                break
        else:                              # разделител от маската
            pending_sep = m_ch
            if pending_sep:
                result.append(pending_sep)
                pending_sep = None
        result.append(d_ch)

    # Остатъчни цифри (ако value е по-дълъг от маската)
    leftover = ''.join(digits)
    if leftover:
        if pending_sep:
            result.append(pending_sep)
        result.append(leftover)

    return ''.join(result)


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
        name and plugin suffix, and whose state is marked as installed.

        :return: A list of installed plugin module names that match the filtering criteria.
        :rtype: list[str]
        """
        return self.env['ir.module.module'].search([
            ('name', 'like', f"{BASE_MODULE}{PLUGINS_SUFFIX}%"),
            ('state', '=', 'installed')
        ]).mapped('name')

    def _update_template_data(self, base_data, template_code, data_getter, type_template=None):
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
        if type_template == 'account.account' and hasattr(self, '_get_bg_template_data'):
            bg_template_data = self._get_bg_template_data()
            account_mask = bg_template_data.get('account_mask') or None
            try:
                target_len = int(bg_template_data.get('code_digits', 6))
            except (TypeError, ValueError):
                target_len = 6

            if account_mask:
                for key, account_data in result.items():
                    result[key]['code'] = apply_mask_zip(
                        account_data['code'],
                        account_mask,
                        target_len=target_len,
                        fill_char='0'
                    )
        return result

    @template(model='account.account')
    def _get_bg_account_data(self, template_code, module=BASE_MODULE):
        return self._parse_csv(template_code, 'account.account', module)

    @template(model='account.account')
    def _get_account_account(self, template_code):
        return self._update_template_data(
            super()._get_account_account(template_code),
            template_code,
            self._get_bg_account_data,
            type_template='account.account',
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

    @template(model='account.journal')
    def _get_account_journal(self, template_code):
        res = super()._get_account_journal(template_code)
        update_func = getattr(self, f'_get_{template_code}_account_journal', None)
        if update_func:
            res.update(update_func(template_code))
        return res

    # @template(model='account.fiscal.position')
    # def _get_bg_fiscal_position_data(self, template_code, module=BASE_MODULE):
    #     return self._parse_csv(template_code, 'account.fiscal.position', module)
    #
    # @template(model='account.fiscal.position')
    # def _get_account_fiscal_position(self, template_code):
    #     return self._update_template_data(
    #         super()._get_account_tax(template_code),
    #         template_code,
    #         self._get_bg_fiscal_position_data
    #     )

    @template('bg')
    def _get_bg_template_data_external(self):
        return {
            'account_mask': '###.###',
            'code_digits': '6',
        }

    @template('bg')
    def _get_bg_template_data(self):
        res = super()._get_bg_template_data()
        res.update(self._get_bg_template_data_external())
        return res
