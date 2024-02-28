#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import models

_logger = logging.getLogger(__name__)

try:
    import stdnum
    from stdnum.exceptions import InvalidFormat, InvalidChecksum, InvalidLength, ValidationError
except ImportError:
    _logger.debug("Cannot `import external dependency python stdnum package`.")


class ResPartnerIdCategory(models.Model):
    _inherit = "res.partner.id_category"

    def validate_res_partner_bg(self, id_number):
        def get_checksum(weights, digits):
            checksum = sum([weight * int(digit) for weight, digit in zip(weights, digits)])
            return checksum % 11

        def check_uic_base(uic):
            checksum = get_checksum(range(1, 9), uic)
            if checksum == 10:
                checksum = get_checksum(range(3, 11), uic)
            return uic[-1] == checksum % 10

        def check_uic_extra(uic):
            digits = uic[9:13]
            checksum = get_checksum([2, 7, 3, 5], digits)
            if checksum == 10:
                checksum = get_checksum([4, 9, 5, 7], digits)
            return digits[-1] == checksum % 10

        self.ensure_one()
        if not id_number:
            return False
        id_number = str(id_number).upper()
        validate = False
        duplicate_bg = False

        # First check the id_number without any prefix only digits like ENG or PNF
        if not "".join(filter(str.istitle, id_number)):
            # Validation for BG Identification Number (EGN)
            try:
                if stdnum.get_cc_module('bg', 'egn').validate(id_number):
                    cat = self.env.ref("l10n_bg_config.partner_identification_egn_number_category").id
                    duplicate_bg = self._search_duplicate(cat, id_number, True)
                    validate = True
            except InvalidLength:
                _logger.info(f"Invalid length for EGN: {id_number}")
            except ValidationError:
                _logger.info(f"Validate error for EGN: {id_number}")

            # Validation for BG Personal Number of a Foreigner (PNF)
            if not validate:
                try:
                    if stdnum.get_cc_module('bg', 'pnf').validate(id_number):
                        cat = self.env.ref("l10n_bg_config.partner_identification_pnf_number_category").id
                        duplicate_bg = self._search_duplicate(cat, id_number, True)
                        validate = True
                except InvalidLength:
                    _logger.info("Invalid length for PNF")

            # Validation for BG Unified Identification Code (UIC)
            if not validate:
                uid_check = "".join(filter(str.isdigit, id_number))
                if len(uid_check) in [9, 13] and check_uic_base(uid_check):
                    cat = self.env.ref("l10n_bg_config.partner_identification_uic_number_category").id
                    duplicate_bg = self._search_duplicate(cat, uid_check, True)
                    validate = True
                else:
                    _logger.info("The length of id_number_check ot 9 or 13")

                if len(uid_check) == 13 and not check_uic_extra(uid_check):
                    cat = self.env.ref("l10n_bg_config.partner_identification_uic_number_category").id
                    duplicate_bg = self._search_duplicate(cat, uid_check, True)
                    validate = True
                else:
                    _logger.info("The length of is 13")

        if not duplicate_bg or not validate:
            _logger.info("Duplicate")
            return False
        return False
