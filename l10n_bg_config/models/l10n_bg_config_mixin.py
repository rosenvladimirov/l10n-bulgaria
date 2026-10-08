# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import logging
import re
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
    """Верифицира двойката uic+api_key спрямо съхранения crypt_key.

    crypt_key трябва да е bytes — base64 кодиране на XOR(uic, api_key).
    Връща True само ако ключовете съвпадат напълно.
    """
    if not (uic and api_key and crypt_key):
        return False
    try:
        seed = generate_encryption_keys(uic, api_key)
        expected = base64.b64encode(seed)
        # XOR дайджест на payload трябва да е 0 при съвпадение (expected == crypt_key)
        payload = expected + b"::" + (crypt_key or b"")
        digest = 0
        for byte in payload:
            digest ^= byte
        return digest == 0 and expected == crypt_key
    except Exception:
        _logger.exception("Failed to validate l10n_bg api key")
        return False


def prepare_zip_payload(files_report, company):
    """Подготвя payload за ZIP с парола ако ключовете на компанията са невалидни.

    При валидни ключове — без парола (клиентът може да разпакетира свободно).
    При невалидни — генерира случайна парола → ZIP е нечетим.
    """
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
        if self._l10n_bg_hide_marked(doc, view_type):
            result["arch"] = etree.tostring(doc)
        return result

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """Справките на не-българска фирма не предлагат маркираните полета.

        „Групиране по → собствено“, полето в „Добави филтър“ и мерките на
        pivot/graph идват от fields_get, не от изгледа — get_view не ги
        стига. Полетата остават в отговора (формите и списъците ги искат),
        само им се свалят флаговете, по които клиентът ги предлага.
        """
        result = super().fields_get(allfields=allfields, attributes=attributes)
        if not self.env.company._check_is_l10n_bg_record():
            self._l10n_bg_unoffer_marked(result)
        return result

    def _l10n_bg_unoffer_marked(self, descriptions):
        for name, desc in descriptions.items():
            if not self._l10n_bg_is_marked(name):
                continue
            for flag in ("groupable", "searchable"):
                if flag in desc:
                    desc[flag] = False
            if "aggregator" in desc:
                desc["aggregator"] = None

    # ------------------------------------------------------------------
    # Скриване по име. Маркер = стойност, която ЗАПОЧВА с l10n_bg:
    #   поле — по името му; всеки друг елемент (group, page, div, setting,
    #   block, app, button, separator, …) — по id или name.
    # Задължителните полета (required) НЕ се скриват, нито контейнерът,
    # в който има такова — иначе записът гърми за стойност, която не се вижда.
    # ------------------------------------------------------------------

    _l10n_bg_marker = "l10n_bg"

    def _l10n_bg_is_marked(self, value):
        return bool(value) and value.startswith(self._l10n_bg_marker)

    def _l10n_bg_node_model(self, node):
        """Моделът, към който принадлежи <field> възелът (вложените списъци на o2m са на comodel)."""
        chain = [
            anc.get("name")
            for anc in reversed(list(node.iterancestors()))
            if anc.tag == "field" and anc.get("name")
        ]
        model = self._name
        for name in chain:
            field = self.env[model]._fields.get(name)
            if not field or not field.comodel_name:
                return None
            model = field.comodel_name
        return model

    def _l10n_bg_field_required(self, node):
        if node.get("required") in ("1", "True", "true"):
            return True
        model = self._l10n_bg_node_model(node)
        field = model and self.env[model]._fields.get(node.get("name"))
        return bool(field and field.required)

    def _l10n_bg_in_list(self, node, view_type):
        return view_type == "list" or any(anc.tag == "list" for anc in node.iterancestors())

    def _l10n_bg_hide_marked(self, doc, view_type):
        """Скрива маркираните възли в doc; връща True, ако нещо е променено."""
        changed = False
        if view_type == "search":
            token = re.compile(r"""['"]%s""" % self._l10n_bg_marker)
            for node in doc.iter("field", "filter"):
                if (
                    self._l10n_bg_is_marked(node.get("name"))
                    or token.search(node.get("domain") or "")
                    or token.search(node.get("context") or "")
                ):
                    node.set("invisible", "True")
                    changed = True
            return changed

        hidden_fields = set()
        for node in doc.iter():
            if not isinstance(node.tag, str) or node is doc:
                continue
            if node.tag == "field":
                if not self._l10n_bg_is_marked(node.get("name")) or self._l10n_bg_field_required(node):
                    continue
                in_list = self._l10n_bg_in_list(node, view_type)
                node.set("column_invisible" if in_list else "invisible", "True")
                hidden_fields.add(node.get("name"))
                changed = True
            elif node.tag != "label" and (
                self._l10n_bg_is_marked(node.get("id")) or self._l10n_bg_is_marked(node.get("name"))
            ):
                # само задължително поле на СЪЩИЯ модел пази контейнера; задължителното
                # във вложен списък (o2m) не пречи на записа на този запис
                if any(
                    not any(anc.tag == "field" for anc in f.iterancestors())
                    and self._l10n_bg_field_required(f)
                    for f in node.iter("field")
                ):
                    continue
                node.set("invisible", "True")
                changed = True
        for label in doc.iter("label"):
            if label.get("for") in hidden_fields:
                label.set("invisible", "True")
                changed = True
        return changed
