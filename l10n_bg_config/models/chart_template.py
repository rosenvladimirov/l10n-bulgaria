import logging
import re

from odoo import models

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _deref_account_tags(self, template_code, tax_data):
        super()._deref_account_tags(template_code, tax_data)
        for tax_values in tax_data.values():
            tag_name = tax_values.get("name")
            tag_id = re.sub(r"\D", "", tag_name)
            _logger.info(f"Tag ID: {tag_id}-{tax_values}")
            if tag_id:
                _logger.info(f"Tag ID: {tag_id}-{tax_values}")
