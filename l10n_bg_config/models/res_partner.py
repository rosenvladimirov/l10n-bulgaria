#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from odoo import fields, models, api, _

_logger = logging.getLogger(__name__)

try:
    import stdnum
    from stdnum.exceptions import InvalidFormat, InvalidChecksum, InvalidLength, InvalidComponent
except ImportError:
    _logger.debug("Cannot `import external dependency python stdnum package`.")


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _l10n_bg_uic_type(self):
        return [
            ('bg_uic', _('BG Unified identification number (BULSTAT)')),
            ('bg_egn', _('BG Identification number')),
            ('bg_pnf', _('BG Personal number of a foreigner')),
            ('bg_onnra', _('BG Official number from the National Revenue Agency')),
            ('bg_crauid', _('BG Unique identification code under the CRA')),
            ('bg_non_eu', _('BG Non EU Tax administration number')),
            ('eu_vat', _('EU Tax administration number'))
        ]

    # l10n_bg_uic = fields.Char('Unique identification code')
    l10n_bg_uic_type = fields.Selection(selection=lambda self: self._l10n_bg_uic_type(),
                                        string='Type of Bulgaria UID',
                                        help="Choice type of Bulgaria UID.")
    l10n_bg_uic = fields.Char(
        string="Unique identification code",
        compute=lambda s: s._compute_identification(
            "l10n_bg_uic", s.l10n_bg_uic_type
        ),
        inverse=lambda s: s._inverse_identification(
            "l10n_bg_uic", s.l10n_bg_uic_type
        ),
        search=lambda s, *a: s._search_identification(s.l10n_bg_uic_type, *a),
    )

    @api.onchange('l10n_bg_uic_type')
    @api.depends('l10n_bg_uic')
    def _onchange_l10n_bg_uic_type(self):
        for record in self:
            if record.id_numbers.filtered(lambda r: r.category_id.code != record.l10n_bg_uic_type):
                record.id_numbers.category_id.unlink()

    @api.onchange('vat', 'country_id')
    def _onchange_check_vies(self):
        res = super()._onchange_check_vies()
        id_number = str(self.vat).upper()
        if not id_number:
            return res
        _logger.info("VAT %s" % id_number)
        validate = False
        if not validate:
            try:
                if "".join(filter(str.istitle, id_number)) == 'BG' \
                        and stdnum.get_cc_module('bg', 'vat').validate(id_number):
                    _logger.info("VAT %s:%s" % (
                        "".join(filter(str.istitle, id_number)), stdnum.get_cc_module('bg', 'vat').validate(id_number)))
                    self.l10n_bg_uic_type = 'bg_uic'
                    self.l10n_bg_uic = stdnum.get_cc_module('bg', 'vat').compact(id_number)
                    validate = True
            except InvalidFormat:
                validate = False

        if not validate:
            try:
                if not "".join(filter(str.istitle, id_number)) \
                        and stdnum.get_cc_module('bg', 'egn').validate(id_number):
                    _logger.info("EGN %s:%s" % (
                        "".join(filter(str.istitle, id_number)), stdnum.get_cc_module('bg', 'egn').validate(id_number)))
                    self.l10n_bg_uic_type = 'bg_egn'
                    self.l10n_bg_uic = stdnum.get_cc_module('bg', 'egn').compact(id_number)
                    validate = True
            except InvalidFormat:
                validate = False

        if not validate:
            try:
                if stdnum.get_cc_module('bg', 'pnf').validate(id_number):
                    _logger.info("PNF %s:%s" % stdnum.get_cc_module('bg', 'pnf').validate(id_number))
                    self.l10n_bg_uic_type = 'bg_pnf'
                    self.l10n_bg_uic = stdnum.get_cc_module('bg', 'pnf').compact(id_number)
                    validate = True
            except InvalidFormat:
                validate = False

        if not validate:
            try:
                if stdnum.get_cc_module('eu', 'vat').validate(id_number):
                    self.l10n_bg_uic_type = 'eu_vat'
                    self.l10n_bg_uic = stdnum.get_cc_module('eu', 'vat').compact(id_number)
                    validate = True
            except InvalidComponent:
                validate = False
            except InvalidFormat:
                validate = False

        if not validate:
            self.l10n_bg_uic_type = 'bg_non_eu'
            self.l10n_bg_uic = '99999999999'
            self.vat = False
            _logger.info(_('Validate check Bulgaria unified indication number'))
        return res
