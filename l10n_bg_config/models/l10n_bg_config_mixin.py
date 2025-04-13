# Part of Odoo. See LICENSE file for full copyright and licensing details.
import binascii
import logging
import random
from difflib import Differ


from lxml import etree

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


def generate_key2(length):
    return ''.join(
        random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789') for _ in range(length))


def generate_encryption_keys(key1, key2):
    if not key1:
        key1 = random.randint(1, 99999999999)
    if not key2:
        key2 = generate_key2(11)
    encrypted_key = bytes([ord(a) ^ ord(b) for a, b in zip(key1, key2)])
    return binascii.hexlify(encrypted_key).decode('utf-8')


def compare_strings_to_clean(s1, s2):
    differ = Differ()
    diff = list(differ.compare(s1, s2))
    clean_diff = ''.join(line[2:] for line in diff)
    return clean_diff


def decrypt_key(encrypted_key, key1, key2):
    password = ''
    if encrypted_key and key2:
        password = ''.join(chr(a ^ ord(b)) for a, b in zip(encrypted_key, key2))
    password = compare_strings_to_clean(password, key1)
    return password.encode()


class L10nBGConfigMixin(models.AbstractModel):
    _name = "l10n.bg.config.mixin"
    _description = (
        "Mixin model for applying to any object that use Bulgarian Accounting"
    )

    is_l10n_bg_record = fields.Boolean(
        string="Is Romanian Record",
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
        if view_type == "tree":
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

            for field in doc.xpath('//group[contains(@id,"l10n_bg")]'):
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
