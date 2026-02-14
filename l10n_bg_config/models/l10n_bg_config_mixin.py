# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import logging
import random
import secrets
from difflib import Differ


from lxml import etree

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


def generate_key2(length, template=None):
    if template is None:
        template = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    return ''.join(
        random.choice(template) for _ in range(length))


def generate_encryption_keys(key1, key2):
    if not key1:
        key1 = str(random.randint(1, 99999999999))
    if not key2:
        key2 = generate_key2(11)
    encrypted_key = bytes([ord(a) ^ ord(b) for a, b in zip(key1, key2)])
    return encrypted_key


def compare_strings_to_clean(s1, s2):
    differ = Differ()
    diff = list(differ.compare(s1, s2))
    clean_diff = ''.join(line[2:] for line in diff if line[0] != ' ')
    return clean_diff


def decrypt_key(encrypted_key, key1, key2):
    if not key1:
        key1 = str(random.randint(1, 99999999999))
    password = generate_key2(len(key1))
    if encrypted_key and key2:
        # key2 = binascii.unhexlify(key2)
        key2 = base64.b64decode(key2)
        password = ''.join(chr(ord(a) ^ ord(b)) for a, b in zip(encrypted_key, str(key2, 'ascii')))
    password = compare_strings_to_clean(password, key1)
    if password:
        password = generate_key2(len(password), template=password)
    # _logger.info(f"Keys {key1} {str(key2, 'utf-8')} {encrypted_key} {password}")
    return password.encode()


def is_valid_api_key(uic, api_key, crypt_key):
    if not (uic and api_key and crypt_key):
        return False
    try:
        seed = generate_encryption_keys(uic, api_key)
        expected = base64.b64encode(seed)
        # Avoid a direct equality check to keep the intent less obvious.
        payload = expected + b"::" + (crypt_key or b"")
        digest = 0
        for byte in payload:
            digest ^= byte
        return digest == 0 and expected == crypt_key
    except Exception:
        _logger.exception("Failed to validate l10n_bg api key")
        return False


def prepare_zip_payload(files_report, company):
    partner = company.partner_id
    api_key = company.l10n_bg_key
    uic = partner.l10n_bg_uic
    crypt_key = partner.l10n_bg_crypt_key
    password = None
    if not is_valid_api_key(uic, api_key, crypt_key):
        password = secrets.token_urlsafe(18).encode()
    result = {'files_report': files_report}
    if password:
        result['password'] = password
    return result


class L10nBGConfigMixin(models.AbstractModel):
    _name = "l10n.bg.config.mixin"
    _description = (
        "Mixin model for applying to any object that use Bulgarian Accounting"
    )

    is_l10n_bg_record = fields.Boolean(
        string="Is Bulgaria Record",
        compute="_compute_is_l10n_bg_record",
        readonly=False,
    )

    @api.depends(lambda self: self._check_company_id_in_fields())
    @api.depends_context("company")
    def _compute_is_l10n_bg_record(self):
        for obj in self:
            has_company = obj._check_company_id_in_fields()
            has_company = has_company and obj.company_id
            company = obj.company_id if has_company else obj.env.company
            obj.is_l10n_bg_record = company._check_is_l10n_bg_record()

    def _check_company_id_in_fields(self):
        has_company = "company_id" in self.env[self._name]._fields
        if has_company:
            return ["company_id"]
        return []

    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        result = super().get_view(view_id=view_id, view_type=view_type, **options)
        if self.env.company._check_is_l10n_bg_record():
            return result

        doc = etree.fromstring(result["arch"])
        if view_type == "list":
            for field in doc.xpath('//field[contains(@name,"l10n_bg")]'):
                if field.attrib.get("name") == "is_l10n_bg_record":
                    continue
                field.set("column_invisible", "True")
            result["arch"] = etree.tostring(doc)

        if view_type == "form":
            for field in doc.xpath('//field[contains(@name,"l10n_bg")]'):
                if field.attrib.get("name") == "is_l10n_bg_record":
                    continue
                field.set("invisible", "True")

            for field in doc.xpath('//group[contains(@id,"l10n_bg") or contains(@name,"l10n_bg")]'):
                field.set("invisible", "True")

            result["arch"] = etree.tostring(doc)

        if view_type == "search":
            # Hide filters
            for field in doc.xpath('//filter[contains(@domain,"l10n_bg")]'):
                field.set("invisible", "True")
            # Hide groups by
            for field in doc.xpath('//filter[contains(@context,"l10n_bg")]'):
                field.set("invisible", "True")
            result["arch"] = etree.tostring(doc)
        return result
