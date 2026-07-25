#  Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo.addons.account_reports.models.account_generic_tax_report import GenericTaxReportCustomHandler as generictaxreportcustomhandler
from .models.account_generic_tax_report import GenericTaxReportCustomHandler

def post_load_hook():
    generictaxreportcustomhandler._add_tax_group_closing_items = GenericTaxReportCustomHandler._add_tax_group_closing_items
    generictaxreportcustomhandler._compute_vat_closing_entry = GenericTaxReportCustomHandler._compute_vat_closing_entry
    generictaxreportcustomhandler._get_key_compute_vat_closing_entry = GenericTaxReportCustomHandler._get_key_compute_vat_closing_entry
