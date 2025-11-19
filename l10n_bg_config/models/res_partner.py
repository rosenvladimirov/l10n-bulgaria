#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import logging

from odoo import Command, _, api, fields, models
from odoo.addons.l10n_bg_config.models.l10n_bg_config_mixin import generate_key2, generate_encryption_keys

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

    def _validate_l10n_bg_uic(self, raise_on_error=False):
        """
        Валидира UIC номера за български партньори.

        :param raise_on_error: Ако е True, вдига UserError при невалиден VAT
        :return: True ако валидацията е успешна, False в противен случай
        """
        for record in self:
            id_number = str(record.vat).upper() if record.vat else ""

            # Празен VAT е валиден случай - не всички партньори имат VAT
            if not id_number:
                # Изчистваме старите данни за UIC ако VAT е изтрит
                if record.l10n_bg_uic or record.l10n_bg_uic_type:
                    record.l10n_bg_uic = False
                    record.l10n_bg_uic_type = False
                return True

            validate = False
            error_message = None

            # First, check id numbers with a prefix
            if "".join(filter(str.istitle, id_number)):
                # BG VAT number convert to uic
                if "".join(filter(str.istitle, id_number)) == "BG":
                    try:
                        if stdnum.get_cc_module("bg", "vat").validate(id_number):
                            record.l10n_bg_uic_type = "bg_uic"
                            record.l10n_bg_uic = stdnum.get_cc_module("bg", "vat").compact(
                                id_number
                            )
                            validate = True
                    except InvalidFormat:
                        error_message = _("Invalid format for Bulgarian VAT number: %s") % id_number
                    except InvalidChecksum:
                        error_message = _("Invalid checksum for Bulgarian VAT number: %s") % id_number
                        _logger.info(f"Invalid check sum of {id_number}")
                    except ValidationError as e:
                        error_message = _("Validation error for Bulgarian VAT: %s - %s") % (id_number, str(e))
                        _logger.info(f"Invalid {id_number} with error {e}")

                #  Try for EU VAT Number
                if not validate and not error_message:
                    try:
                        if stdnum.get_cc_module("eu", "vat").validate(id_number):
                            record.l10n_bg_uic_type = "eu_vat"
                            record.l10n_bg_uic = stdnum.get_cc_module("eu", "vat").compact(
                                id_number
                            )
                            validate = True
                    except (InvalidComponent, InvalidFormat):
                        pass  # Continue to next validation
                    except ValidationError as e:
                        _logger.info(f"Invalid {id_number} with error {e}")

            # After check for EGN and PNF
            if (
                    not validate
                    and not "".join(filter(str.istitle, id_number))
                    and "".join(filter(str.isdigit, id_number))
            ):
                #  Check for EGN
                try:
                    if stdnum.get_cc_module("bg", "egn").validate(id_number):
                        record.l10n_bg_uic_type = "bg_egn"
                        record.l10n_bg_uic = stdnum.get_cc_module("bg", "egn").compact(
                            id_number
                        )
                        validate = True
                except (InvalidFormat, ValidationError) as e:
                    _logger.info(f"Invalid EGN {id_number} with error {e}")

                # Check for PNF
                if not validate:
                    try:
                        if stdnum.get_cc_module("bg", "pnf").validate(id_number):
                            record.l10n_bg_uic_type = "bg_pnf"
                            record.l10n_bg_uic = stdnum.get_cc_module("bg", "pnf").compact(
                                id_number
                            )
                            validate = True
                    except (InvalidFormat, ValidationError) as e:
                        _logger.info(f"Invalid PNF {id_number} with error {e}")

            # Finally, mark like outside EU if isn't validated
            if not validate:
                if raise_on_error and error_message:
                    raise UserError(error_message)
                record.l10n_bg_uic_type = "bg_non_eu"
                record.l10n_bg_uic = "99999999999"
                # Не изтриваме VAT, само маркираме като non-EU

        return True

    def _compute_l10n_bg_represent_contact_id(self):
        for record in self:
            l10n_bg_represent_contact_id = record.child_ids.filtered(
                lambda r: r.type == "represent"
            )
            if len(l10n_bg_represent_contact_id) > 1:
                l10n_bg_represent_contact_id = l10n_bg_represent_contact_id[0]

            record.l10n_bg_represent_contact_id = l10n_bg_represent_contact_id

    def _inverse_l10n_bg_represent_contact_id(self):
        for record in self:
            if record.l10n_bg_represent_contact_id:
                record.l10n_bg_represent_contact_id.type = "represent"
                record.child_ids = [
                    Command.link(record.l10n_bg_represent_contact_id.id)
                ]
            else:
                record.l10n_bg_represent_contact_id = False
                record.child_ids.filtered(lambda r: r.id == record.id).type = "contact"

    def get_api_key(self):
        l10n_bg_uic = self.l10n_bg_uic or '99999999999'
        return generate_key2(len(l10n_bg_uic))

    def _update_key(self, values):
        if values.get("l10n_bg_key") and (self.l10n_bg_uic or values.get("l10n_bg_uic")):
            return base64.b64encode(generate_encryption_keys(values.get("l10n_bg_uic") or self.l10n_bg_uic, values["l10n_bg_key"]))
        return False

    def write(self, values):
        # Проверка за промяна на parent_id с различен VAT
        if 'parent_id' in values and not self.env.context.get('skip_vat_check', False):
            for record in self:
                # Проверяваме дали партньорът има posted счетоводни записи
                posted_moves = self.env['account.move'].search([
                    ('partner_id', '=', record.id),
                    ('state', '=', 'posted')
                ], limit=1)

                if posted_moves:
                    new_parent = self.env['res.partner'].browse(values['parent_id']) if values['parent_id'] else False
                    old_vat = record.vat
                    new_parent_vat = new_parent.vat if new_parent else False

                    # Ако има различни VAT номера, вдигаме грешка
                    if new_parent_vat and old_vat and new_parent_vat != old_vat:
                        raise UserError(_(
                            "You cannot change the parent company for partner '%s' "
                            "because the parent has a different Tax ID. "
                            "Partner Tax ID: %s, Parent Tax ID: %s. "
                            "This is not allowed when there are posted accounting entries."
                        ) % (record.name, old_vat, new_parent_vat))

        # Проверка за промяна на VAT преди записване
        if 'vat' in values and not self.env.context.get('block_validate', False):
            for record in self:
                old_vat = record.vat
                new_vat = values['vat']

                # Ако има промяна на VAT и партньорът има свързани транзакции
                if old_vat != new_vat and old_vat and new_vat:
                    # Проверка за съществуващи счетоводни записи
                    posted_moves = self.env['account.move'].search([
                        ('partner_id', '=', record.id),
                        ('move_id.state', '=', 'posted')
                    ], limit=1)

                    if posted_moves:
                        raise UserError(_(
                            "You cannot change the Tax ID for partner '%s' "
                            "because there are already posted accounting entries. "
                            "Old Tax ID: %s, New Tax ID: %s"
                        ) % (record.name, old_vat, new_vat))

        # Актуализиране на криптиращия ключ
        l10n_bg_crypt_key = self._update_key(values)
        if l10n_bg_crypt_key:
            values['l10n_bg_crypt_key'] = l10n_bg_crypt_key

        res = super().write(values)

        # Актуализиране на представител
        if values.get("type") and values["type"] == "represent":
            company_id = self.env["res.company"].search(
                [("partner_id", "=", self.id)], limit=1
            )
            if company_id:
                company_id.l10n_bg_represent_contact_id = self.id
            elif not company_id and self.parent_id:
                self.parent_id.l10n_bg_represent_contact_id = self.id

        # Валидация на UIC след записване
        if "vat" in values and not self.env.context.get('block_validate', False):
            # Използваме нов контекст за да избегнем рекурсия
            self.with_context(block_validate=True)._validate_l10n_bg_uic()

        return res
