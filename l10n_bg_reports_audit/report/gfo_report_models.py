#  Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Abstract `report.*` models that bind QWeb templates to wizard values.

Odoo's default _render_qweb_pdf passes `{'docs': records, 'doc_ids': ids}`
to the template. Our templates need company/asset_rows/etc. — we inject
them via `_get_report_values()` here, by delegating to the wizard's
`get_report_values()` builder.
"""
from odoo import api, models


class _GfoReportBase(models.AbstractModel):
    _name = "report.l10n_bg_reports_audit.gfo_report_base"
    _description = "GFO/GOD Report Values Base"

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env["l10n.bg.gfo.print.wizard"].browse(docids)
        return wizard.get_report_values()


class GfoBalanceReport(models.AbstractModel):
    _name = "report.l10n_bg_reports_audit.gfo_balance_pdf"
    _inherit = "report.l10n_bg_reports_audit.gfo_report_base"
    _description = "GFO Balance Sheet — Report Values"


class GfoPlReport(models.AbstractModel):
    _name = "report.l10n_bg_reports_audit.gfo_pl_pdf"
    _inherit = "report.l10n_bg_reports_audit.gfo_report_base"
    _description = "GFO P&L — Report Values"


class GfoCfReport(models.AbstractModel):
    _name = "report.l10n_bg_reports_audit.gfo_cf_pdf"
    _inherit = "report.l10n_bg_reports_audit.gfo_report_base"
    _description = "GFO Cash Flow — Report Values"


class GfoEquityReport(models.AbstractModel):
    _name = "report.l10n_bg_reports_audit.gfo_equity_pdf"
    _inherit = "report.l10n_bg_reports_audit.gfo_report_base"
    _description = "GFO Changes in Equity — Report Values"


class GodReport(models.AbstractModel):
    _name = "report.l10n_bg_reports_audit.god_pdf"
    _inherit = "report.l10n_bg_reports_audit.gfo_report_base"
    _description = "NSI Annual Activity Report — Report Values"
