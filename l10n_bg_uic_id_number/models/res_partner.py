#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

try:
    import stdnum
    from stdnum.exceptions import (
        InvalidChecksum,
        InvalidComponent,
        InvalidFormat,
        InvalidLength,
        ValidationError,
    )
except ImportError:
    _logger.debug("Cannot `import external dependency python stdnum package`.")


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_bg_uic = fields.Char(
        string="Unique identification code",
        compute=lambda s: s._compute_identification("l10n_bg_uic", s.l10n_bg_uic_type),
        inverse=lambda s: s._inverse_identification("l10n_bg_uic", s.l10n_bg_uic_type),
        search=lambda s, *a: s._search_identification(s.l10n_bg_uic_type, *a),
    )

    @api.onchange("l10n_bg_uic_type")
    @api.depends("l10n_bg_uic")
    def _onchange_l10n_bg_uic_type(self):
        for record in self:
            if record.id_numbers.filtered(
                lambda r: r.category_id.code != record.l10n_bg_uic_type
            ):
                record.id_numbers.category_id.unlink()

    #
    # def _check_l10n_bg_uic(self):
    #     id_number = str(self.vat).upper()
    #     if not id_number:
    #         return False
    #
    #     validate = False
    #     # First check id numbers with prefix
    #     if "".join(filter(str.istitle, id_number)):
    #         # BG VAT number convert to uic
    #         if "".join(filter(str.istitle, id_number)) == 'BG':
    #             try:
    #                 if stdnum.get_cc_module('bg', 'vat').validate(id_number):
    #                     self.l10n_bg_uic_type = 'bg_uic'
    #                     self.l10n_bg_uic = stdnum.get_cc_module('bg', 'vat').compact(id_number)
    #                     validate = True
    #             except InvalidFormat:
    #                 validate = False
    #             except InvalidChecksum:
    #                 validate = False
    #                 _logger.info(f'Invalid check sum of {id_number}')
    #             except ValidationError as e:
    #                 _logger.info(f'Invalid {id_number} with error {e}')
    #                 validate = False
    #
    #         #  Try for EU VAT Number
    #         if not validate:
    #             try:
    #                 if stdnum.get_cc_module('eu', 'vat').validate(id_number):
    #                     self.l10n_bg_uic_type = 'eu_vat'
    #                     self.l10n_bg_uic = stdnum.get_cc_module('eu', 'vat').compact(id_number)
    #                     validate = True
    #             except InvalidComponent:
    #                 validate = False
    #             except InvalidFormat:
    #                 validate = False
    #             except ValidationError as e:
    #                 _logger.info(f'Invalid {id_number} with error {e}')
    #                 validate = False
    #
    #     # After check for ENG and PNF
    #     if not validate and not "".join(filter(str.istitle, id_number)) and "".join(filter(str.isdigit, id_number)):
    #         #  Check for ENG
    #         try:
    #             if stdnum.get_cc_module('bg', 'egn').validate(id_number):
    #                 self.l10n_bg_uic_type = 'bg_egn'
    #                 self.l10n_bg_uic = stdnum.get_cc_module('bg', 'egn').compact(id_number)
    #                 validate = True
    #         except InvalidFormat:
    #             validate = False
    #         except ValidationError as e:
    #             _logger.info(f'Invalid {id_number} with error {e}')
    #             validate = False
    #
    #         # Check for PNF
    #         if not validate:
    #             try:
    #                 if stdnum.get_cc_module('bg', 'pnf').validate(id_number):
    #                     self.l10n_bg_uic_type = 'bg_pnf'
    #                     self.l10n_bg_uic = stdnum.get_cc_module('bg', 'pnf').compact(id_number)
    #                     validate = True
    #             except InvalidFormat:
    #                 validate = False
    #             except ValidationError as e:
    #                 _logger.info(f'Invalid {id_number} with error {e}')
    #                 validate = False
    #     # Finally, mark like outside EU if isn't validated
    #     if not validate:
    #         self.l10n_bg_uic_type = 'bg_non_eu'
    #         self.l10n_bg_uic = '99999999999'
    #         self.vat = False
    #     return True
    #
    # @api.onchange('vat', 'country_id')
    # def _onchange_check_vies(self):
    #     res = super()._onchange_check_vies()
    #     self._check_l10n_bg_uic()
    #     return res
