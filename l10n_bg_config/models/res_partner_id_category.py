#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import models

_logger = logging.getLogger(__name__)

try:
    import stdnum
    from stdnum.exceptions import InvalidFormat, InvalidChecksum, InvalidLength
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
        id_number = id_number.name.upper()
        duplicate_bg = False
        validate = False

        if not validate:
            try:
                if not "".join(filter(str.istitle, id_number)) \
                        and stdnum.get_cc_module('bg', 'egn').validate(id_number):
                    cat = self.env.ref("l10n_bg_config.partner_identification_egn_number_category").id
                    duplicate_bg = self._search_duplicate(cat, id_number, True)
                    validate = True
            except InvalidLength:
                validate = False

        if not validate:
            try:
                if stdnum.get_cc_module('bg', 'pnf').validate(id_number):
                    cat = self.env.ref("l10n_bg_config.partner_identification_pnf_number_category").id
                    duplicate_bg = self._search_duplicate(cat, id_number, True)
                    validate = True
            except InvalidLength:
                validate = False

        if not validate:
            uid_check = "".join(filter(str.isdigit, id_number))
            if len(uid_check) in [9, 13] and check_uic_base(uid_check):
                cat = self.env.ref("l10n_bg_config.partner_identification_uic_number_category").id
                duplicate_bg = self._search_duplicate(cat, id_number, True)
                validate = True

            if len(uid_check) == 13 and not check_uic_extra(uid_check):
                cat = self.env.ref("l10n_bg_config.partner_identification_uic_number_category").id
                duplicate_bg = self._search_duplicate(cat, uid_check, True)
                validate = True

        if not duplicate_bg or not validate:
            return False
        return False
