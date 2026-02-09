from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _get_installed_plugins(self):
        res = super()._get_installed_plugins()
        res.append('l10n_bg_tax_admin')
        return res
