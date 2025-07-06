#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import logging

from odoo import Command, _, api, fields, models
from odoo.addons.l10n_bg_config.models.l10n_bg_config_mixin import generate_key2, generate_encryption_keys
from odoo.tools import sql

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
        ("bg_uic", "BG Unified identification number (BULSTAT)"),
        ("bg_egn", "BG Identification number"),
        ("bg_pnf", "BG Personal number of a foreigner"),
        ("bg_onnra", "BG Official number from the National Revenue Agency"),
        ("bg_crauid", "BG Unique identification code under the CRA"),
        ("bg_non_eu", "BG Non EU Tax administration number"),
        ("eu_vat", "EU Tax administration number"),
    ]


class ResPartner(models.Model):
    _inherit = ["res.partner", "l10n.bg.config.mixin"]
    _name = "res.partner"

    type = fields.Selection(
        selection_add=[
            ("represent", "Company represent/manager"),
            ("agent", "Company agent"),
            ("tax", "Tax agent"),
        ],
        ondelete={"represent": "set null", "agent": "set null", "tax": "set null"},
    )
    l10n_bg_represent_contact_id = fields.Many2one(
        "res.partner",
        string="Representative",
        compute="_compute_l10n_bg_represent_contact_id",
        inverse="_inverse_l10n_bg_represent_contact_id",
        store=True,
    )
    l10n_bg_uic_type = fields.Selection(
        selection=_l10n_bg_uic_type(),
        string="Type of Bulgaria UID",
        help="Choice type of Bulgaria UID.",
    )
    l10n_bg_uic = fields.Char(
        string="Unique identification code",
        help="Unique identification code for the Bulgaria received from trade registry",
    )
    l10n_bg_key = fields.Char('Api Key', help='Enter the key to encrypt the data. If not entered, a random key will be generated.')
    l10n_bg_crypt_key = fields.Binary(
        'Crypt Key',
        attachment=False,
        help='Enter the key to decrypt the data. If not entered, a random key will be generated.'
    )

    def __init__(self, env, ids=(), prefetch_ids=()):
        super().__init__(env, ids=ids, prefetch_ids=prefetch_ids)
        if not sql.column_exists(self.env.cr, self._table, "l10n_bg_key"):
            self.env.cr.execute("ALTER TABLE res_partner ADD COLUMN l10n_bg_key varchar;")

    def _validate_l10n_bg_uic(self):
        id_number = str(self.vat).upper()
        if not id_number:
            return False

        validate = False
        # First, check id numbers with a prefix
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

    def _compute_l10n_bg_represent_contact_id(self):
        for record in self:
            record.l10n_bg_represent_contact_id = record.child_ids.filtered(
                lambda r: r.type == "represent"
            )

    def _inverse_l10n_bg_represent_contact_id(self):
        for record in self:
            if record.l10n_bg_represent_contact_id:
                record.l10n_bg_represent_contact_id.type = "represent"
                record.child_ids = [
                    Command.link(record.l10n_bg_represent_contact_id.id)
                ]
            else:
                record.l10n_bg_represent_contact_id = False

    def get_api_key(self):
        l10n_bg_uic = self.l10n_bg_uic or '99999999999'
        return generate_key2(len(l10n_bg_uic))

    def _update_key(self, values):
        if values.get("l10n_bg_key") and (self.l10n_bg_uic or values.get("l10n_bg_uic")):
            return base64.b64encode(generate_encryption_keys(values.get("l10n_bg_uic") or self.l10n_bg_uic, values["l10n_bg_key"]))
        return False

    def write(self, values):
        l10n_bg_crypt_key = self._update_key(values)
        if l10n_bg_crypt_key:
            values['l10n_bg_crypt_key'] = l10n_bg_crypt_key
        res = super().write(values)
        if values.get("type") and values["type"] == "represent":
            company_id = self.env["res.company"].search(
                [("partner_id", "=", self.id)], limit=1
            )
            if company_id:
                company_id.l10n_bg_represent_contact_id = self.id
            elif not company_id and self.parent_id:
                self.parent_id.l10n_bg_represent_contact_id = self.id
        if "vat" in values and not self._context.get('block_validate', False):
            self.with_context(dict(**self._context, block_validate=True))._validate_l10n_bg_uic()
        return res
