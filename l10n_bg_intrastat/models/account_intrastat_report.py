# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import UserError, RedirectWarning
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

from datetime import datetime, timedelta
from lxml import etree


class IntrastatReportCustomHandler(models.AbstractModel):
    _inherit = 'account.intrastat.report.handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)

        if self.env.company.partner_id.country_id.code != 'BG':
            return

        xml_button = {
            'name': _('XML'),
            'sequence': 30,
            'action': 'export_file',
            'action_param': 'bg_intrastat_export_to_xml',
            'file_export_type': _('XML'),
        }
        options['buttons'].append(xml_button)
        options['intrastat_grouped'] = True  # We always activate the grouping for the belgian intrastat report

    def _show_region_code(self):
        if self.env.company.account_fiscal_country_id.code == 'BE' and not self.env.company.intrastat_region_id:
            return False
        return super()._show_region_code()

    @api.model
    def bg_intrastat_export_to_xml(self, options):
        pass
