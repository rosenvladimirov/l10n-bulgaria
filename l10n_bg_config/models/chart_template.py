import logging
import re

from odoo import models
from odoo.addons.account.models.chart_template import template

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    # def _deref_account_tags(self, template_code, tax_data):
    #     super()._deref_account_tags(template_code, tax_data)
    #     for tax_values in tax_data.values():
    #         tag_name = tax_values.get("name")
    #         tag_id = re.sub(r"\D", "", tag_name)
    #         _logger.info(f"Tag ID: {tag_id}-{tax_values}")
    #         if tag_id:
    #             _logger.info(f"Tag ID: {tag_id}-{tax_values}")

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
