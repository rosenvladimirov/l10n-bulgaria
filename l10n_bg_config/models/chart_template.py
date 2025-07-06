import logging
import re

from odoo import models
from odoo.addons.account.models.chart_template import template

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template(model='account.account')
    def _get_account_l10n_bg_account(self, template_code):
        account_data_l10n_bg_config = self._parse_csv(template_code, 'account.account', 'l10n_bg_config')
        return account_data_l10n_bg_config

    @template(model='account.account')
    def _get_account_account(self, template_code):
        account_data = super()._get_account_account(template_code)
        account_data.update(self._get_account_l10n_bg_account(template_code))
        return account_data

    @template(model='account.group')
    def _get_account_l10n_bg_account_group(self, template_code):
        account_group_data_l10n_bg_config = self._parse_csv(template_code, 'account.group', 'l10n_bg_config')
        return account_group_data_l10n_bg_config

    @template(model='account.group')
    def _get_account_group(self, template_code):
        account_group_data = super()._get_account_group(template_code)
        account_group_data.update(self._get_account_l10n_bg_account_group(template_code))
        return account_group_data

    @template(model='account.tax')
    def _get_account_l10n_bg_tax(self, template_code):
        tax_data_l10n_bg_config = self._parse_csv(template_code, 'account.tax', 'l10n_bg_config')
        self._deref_account_tags(template_code, tax_data_l10n_bg_config)
        return tax_data_l10n_bg_config

    @template(model='account.tax')
    def _get_account_tax(self, template_code):
        tax_data = super()._get_account_tax(template_code)
        tax_data.update(self._get_account_l10n_bg_tax(template_code))
        return tax_data
