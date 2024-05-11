#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import _, api, fields, models

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


def _l10n_bg_uic_type():
    return [
        ("bg_uic", _("BG Unified identification number (BULSTAT)")),
        ("bg_egn", _("BG Identification number")),
        ("bg_pnf", _("BG Personal number of a foreigner")),
        ("bg_onnra", _("BG Official number from the National Revenue Agency")),
        ("bg_crauid", _("BG Unique identification code under the CRA")),
        ("bg_non_eu", _("BG Non EU Tax administration number")),
        ("eu_vat", _("EU Tax administration number")),
    ]


class ResPartner(models.Model):
    _inherit = "res.partner"

    # l10n_bg_uic = fields.Char('Unique identification code')
    l10n_bg_uic_type = fields.Selection(
        selection=_l10n_bg_uic_type(),
        string="Type of Bulgaria UID",
        help="Choice type of Bulgaria UID.",
    )
    l10n_bg_uic = fields.Char(
        string="Unique identification code",
        help="Unique identification code for the Bulgaria received from trade registry",
    )
    l10n_bg_function = fields.Selection(
        selection=[
            ("represent", _("Company represent/manager")),
            ("agent", _("Company agent")),
        ],
        string="Function fo NRA",
    )

    @api.onchange("vat", "country_id")
    def _onchange_check_vies(self):
        res = super()._onchange_check_vies()
        self._validate_l10n_bg_uic()
        return res

    def _validate_l10n_bg_uic(self):
        id_number = str(self.vat).upper()
        if not id_number:
            return False

        validate = False
        # First check id numbers with prefix
        if "".join(filter(str.istitle, id_number)):
            # BG VAT number convert to uic
            if "".join(filter(str.istitle, id_number)) == "BG":
                try:
                    if stdnum.get_cc_module("bg", "vat").validate(id_number):
                        self.l10n_bg_uic_type = "bg_uic"
                        self.l10n_bg_uic = stdnum.get_cc_module("bg", "vat").compact(
                            id_number
                        )
                        validate = True
                except InvalidFormat:
                    validate = False
                except InvalidChecksum:
                    validate = False
                    _logger.info(f"Invalid check sum of {id_number}")
                except ValidationError as e:
                    _logger.info(f"Invalid {id_number} with error {e}")
                    validate = False

            #  Try for EU VAT Number
            if not validate:
                try:
                    if stdnum.get_cc_module("eu", "vat").validate(id_number):
                        self.l10n_bg_uic_type = "eu_vat"
                        self.l10n_bg_uic = stdnum.get_cc_module("eu", "vat").compact(
                            id_number
                        )
                        validate = True
                except InvalidComponent:
                    validate = False
                except InvalidFormat:
                    validate = False
                except ValidationError as e:
                    _logger.info(f"Invalid {id_number} with error {e}")
                    validate = False

        # After check for ENG and PNF
        if (
            not validate
            and not "".join(filter(str.istitle, id_number))
            and "".join(filter(str.isdigit, id_number))
        ):
            #  Check for ENG
            try:
                if stdnum.get_cc_module("bg", "egn").validate(id_number):
                    self.l10n_bg_uic_type = "bg_egn"
                    self.l10n_bg_uic = stdnum.get_cc_module("bg", "egn").compact(
                        id_number
                    )
                    validate = True
            except InvalidFormat:
                validate = False
            except ValidationError as e:
                _logger.info(f"Invalid {id_number} with error {e}")
                validate = False

            # Check for PNF
            if not validate:
                try:
                    if stdnum.get_cc_module("bg", "pnf").validate(id_number):
                        self.l10n_bg_uic_type = "bg_pnf"
                        self.l10n_bg_uic = stdnum.get_cc_module("bg", "pnf").compact(
                            id_number
                        )
                        validate = True
                except InvalidFormat:
                    validate = False
                except ValidationError as e:
                    _logger.info(f"Invalid {id_number} with error {e}")
                    validate = False
        # Finally, mark like outside EU if isn't validated
        if not validate:
            self.l10n_bg_uic_type = "bg_non_eu"
            self.l10n_bg_uic = "99999999999"
            self.vat = False
        return True
