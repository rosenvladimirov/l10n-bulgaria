# Copyright 2011-2017 Akretion (http://www.akretion.com)
# Copyright 2009-2018 Noviat (http://www.noviat.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# @author Luc de Meyer <info@noviat.com>

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    intrastat_origin_transport_id = fields.Many2one(
        comodel_name="res.country",
        string="Country of transport",
        help="In which country the transport unit is registered",
    )
    # l10n_bg_intrastat_reporting_level = fields.Selection(
    #     selection='_get_l10n_bg_intrastat_reporting_level',
    #     string='BG Reporting Level',
    #     default='extended',
    # )
    #
    # @api.model
    # def _get_l10n_bg_intrastat_reporting_level(self):
    #     return [
    #         ('standard', _('Standard')),
    #         ('extended', _('Extended'))]

    # def __init__(self, pool, cr):
    #     super(ResCompany, self).__init__(pool, cr)
    #     cr.execute("SELECT column_name FROM information_schema.columns "
    #                "WHERE table_name = 'res_company' AND column_name = 'intrastat_origin_transport_id'")
    #     if not cr.fetchone():
    #         cr.execute('ALTER TABLE res_company '
    #                    'ADD COLUMN intrastat_origin_transport_id integer;')
    #     cr.execute("SELECT column_name FROM information_schema.columns "
    #                "WHERE table_name = 'res_company' AND column_name = 'reporting_level_bg'")
    #     if not cr.fetchone():
    #         cr.execute('ALTER TABLE res_company '
    #                    'ADD COLUMN reporting_level_bg character varying;')
