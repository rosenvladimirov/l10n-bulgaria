# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

import logging
_logger = logging.getLogger(__name__)

try:
    from stdnum import get_cc_module
except ImportError:
    _logger.warning("BG VAT/EGN/PNF validation partially unavailable because the `stdnum` Python library cannot be found. "
                    "Install it to support more countries, for example with `easy_install stdnum`.")
    vatnumber = None


class ResPartner(models.Model):
    _inherit = ['res.partner']
    _name = 'res.partner'

    uid = fields.Char(compute="_get_from_vat", inverse="_set_from_uid", string='UID', store=True, help="Trade Identification Number. "
                                                                                                          "Fill it if the company is subjected to taxes. "
                                                                                                          "Used by the some of the legal statements.")
    uid_type = fields.Selection([
        ('uid', _('Unified identification number (BULSTAT)')),
        ('egn', _('Identification number')),
        ('pnf', _('Personal number of a foreigner')),
        ('onnra', _('Official number from the National Revenue Agency')),
        ('crauid', _('Unique identification code under the CRA')),
    ], string='Type of UID', help="Choice type of UID.")
    fax = fields.Char('Fax')
    mobile = fields.Char('Mobile Phone')

    def __init__(self, pool, cr):
        cr.execute("SELECT column_name FROM information_schema.columns "
                   "WHERE table_name = 'res_partner' AND column_name = 'uid'")
        if not cr.fetchone():
            cr.execute('ALTER TABLE res_partner '
                       'ADD COLUMN uid character varying;')

        cr.execute("SELECT column_name FROM information_schema.columns "
                   "WHERE table_name = 'res_partner' AND column_name = 'uid_type'")
        if not cr.fetchone():
            cr.execute('ALTER TABLE res_partner '
                       'ADD COLUMN uid_type character varying;')
        cr.execute("SELECT column_name FROM information_schema.columns "
                   "WHERE table_name = 'res_partner' AND column_name = 'fax'")
        if not cr.fetchone():
            cr.execute('ALTER TABLE res_partner '
                       'ADD COLUMN fax character varying;')
        cr.execute("SELECT column_name FROM information_schema.columns "
                   "WHERE table_name = 'res_partner' AND column_name = 'mobile'")
        if not cr.fetchone():
            cr.execute('ALTER TABLE res_partner '
                       'ADD COLUMN mobile character varying;')
        super(ResPartner, self).__init__(pool, cr)

    @api.multi
    @api.depends('vat')
    def _get_from_vat(self):
        for record in self:
            if record.vat:
                record.uid = record.vat.upper().replace('BG', '')
            else:
                record.uid = False

    @api.multi
    def _set_from_uid(self):
        for record in self:
            if record.uid: continue
            if not record.uid:
                record.uid = '999999999999999'
            else:
                record.uid = record.uid

    # VAT/UIC/EGN/PNF validation in Bulgaria, contributed by # Rosen Vladimirov & dXFactory
    def check_vat_bg(self, vat):
        """
        Check Bulgarian EIK/BULSTAT codes for validity
        full information about algoritm is available here
        http://bulstat.registryagency.bg/About.html
        but nothing not work in Bulgaria creasy administration
        """ 
        if not (len(vat) in [9, 10, 13]):
            return False
        try:
            int(vat)
        except ValueError:
            return False

        # check eng
        if len(vat) == 10:
            ret = get_cc_module('bg','egn').is_valid(vat)
            if ret:
                return ret
            return get_cc_module('bg','pnf').is_valid(vat)

        if (len(vat) in [9, 13]):
            return get_cc_module('bg','vat').is_valid(vat)
