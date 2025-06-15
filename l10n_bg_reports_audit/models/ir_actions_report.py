# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, tools, SUPERUSER_ID, _


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.model
    def _build_wkhtmltopdf_args(self, paperformat_id, landscape, specific_paperformat_args=None,
                                set_viewport_size=False):
        command_args = super()._build_wkhtmltopdf_args(
            paperformat_id,
            landscape,
            specific_paperformat_args=specific_paperformat_args,
            set_viewport_size=set_viewport_size
        )

        shrinking_disabled = specific_paperformat_args.get('data-report-disable-shrinking')
        if shrinking_disabled is None:
            return command_args

        shrinking_arg = '--disable-smart-shrinking'
        has_shrinking_arg = shrinking_arg in command_args

        if shrinking_disabled and not has_shrinking_arg:
            command_args.append(shrinking_arg)
        elif not shrinking_disabled and has_shrinking_arg:
            command_args.remove(shrinking_arg)

        return command_args
