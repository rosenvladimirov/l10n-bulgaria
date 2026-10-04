# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
import re
from collections import defaultdict

from lxml import etree

from odoo import Command, api, fields, models

# Ключът на шаблона на продуктовата страница. Зоните, в които уеб редакторът
# пуска блокове „за всички продукти“, се пазят като наследяващи изгледи с ключ
# „<ключ>_<id на зоната>“ (html_editor ir.ui.view.save_oe_structure).
PRODUCT_PAGE_KEY = "website_sale.product"

# Обвивките на целия сайт (хедър, футър, меню) не са част от продуктовата
# страница — превеждат се веднъж за сайта, затова не влизаме в тях.
EXCLUDED_TEMPLATES = frozenset(
    {
        "website.layout",
        "web.layout",
        "web.frontend_layout",
        "portal.frontend_layout",
    }
)

# Само статичен t-call („модул.шаблон“); динамичните („{{ ... }}“) се прескачат.
STATIC_TEMPLATE_KEY = re.compile(r"^[\w-]+\.[\w.-]+$")

SECTIONS = [
    ("product", "Product"),
    ("attribute", "Attributes"),
    ("category", "Categories and Tags"),
    ("page", "Page Layout"),
]


class ProductPageTranslateWizard(models.TransientModel):
    _name = "product.page.translate.wizard"
    _description = "Product Page Translation Wizard"

    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Product",
        required=True,
        readonly=True,
        ondelete="cascade",
    )
    website_id = fields.Many2one(
        "website",
        compute="_compute_website_id",
        store=True,
        precompute=True,
        readonly=False,
        required=True,
        help="The page layout terms are taken from the views of this website.",
    )
    lang_ids = fields.Many2many(
        "res.lang",
        string="Languages",
        compute="_compute_lang_ids",
        store=True,
        precompute=True,
        readonly=False,
        domain=[("active", "=", True)],
    )
    with_product = fields.Boolean(string="Product Fields", default=True)
    with_attributes = fields.Boolean(string="Attributes", default=True)
    with_categories = fields.Boolean(string="Categories and Tags", default=True)
    with_page = fields.Boolean(
        string="Page Layout",
        default=True,
        help="Terms of every template the product page is rendered from, "
        "including the page options and the blocks dropped with the website "
        "editor. The site-wide header and footer are not included.",
    )
    only_missing = fields.Boolean(string="Only Untranslated")
    line_ids = fields.One2many(
        "product.page.translate.wizard.line", "wizard_id", string="Terms"
    )

    @api.depends("product_tmpl_id")
    def _compute_website_id(self):
        for wizard in self:
            wizard.website_id = (
                wizard.product_tmpl_id.website_id
                or self.env["website"].get_current_website()
            )

    @api.depends("website_id")
    def _compute_lang_ids(self):
        for wizard in self:
            website = wizard.website_id
            # Изходът е винаги en_US (както в родния диалог за превод), затова
            # по подразбиране даваме езиците на сайта без основния му език.
            langs = website.language_ids - website.default_lang_id
            wizard.lang_ids = langs or self.env["res.lang"].search(
                [("active", "=", True), ("code", "!=", "en_US")]
            )

    # ------------------------------------------------------------------
    # Какво се превежда
    # ------------------------------------------------------------------

    def _get_page_views(self):
        """Всички изгледи, от които се рендира продуктовата страница.

        Тръгваме от website_sale.product и следваме статичните t-call. За всеки
        шаблон взимаме изгледа, който избраният сайт реално ползва (COW копието
        му, ако има такова), заедно с активните му наследници за сайта — там са
        опциите на страницата и зоните на уеб редактора.
        """
        self.ensure_one()
        View = self.env["ir.ui.view"].with_context(website_id=self.website_id.id)
        views = View.browse()
        seen = set()
        queue = [PRODUCT_PAGE_KEY]
        while queue:
            key = queue.pop(0)
            if key in seen or key in EXCLUDED_TEMPLATES:
                continue
            seen.add(key)
            root = View._get_template_view(key, raise_if_not_found=False)
            if not root:
                continue
            for view in root | root._get_inheriting_views():
                if view in views:
                    continue
                views |= view
                queue += self._get_called_templates(view.arch_db)
        return views

    @api.model
    def _get_called_templates(self, arch):
        """Ключовете на шаблоните, извикани със статичен t-call в arch."""
        if not arch:
            return []
        try:
            root = etree.fromstring(arch.encode())
        except etree.XMLSyntaxError:
            return []
        return [
            node.get("t-call")
            for node in root.iter(tag=etree.Element)
            if STATIC_TEMPLATE_KEY.match(node.get("t-call") or "")
        ]

    def _get_translation_targets(self):
        """Връща списък от (раздел, записи, полета) за превод.

        Точка за разширение: наследниците добавят свои елементи на страницата.
        Полета, които не съществуват или не са преводими, се прескачат.
        """
        self.ensure_one()
        tmpl = self.product_tmpl_id
        targets = []
        if self.with_product:
            targets += [
                (
                    "product",
                    tmpl,
                    [
                        "name",
                        "description_sale",
                        "description_ecommerce",
                        "website_description",
                        "website_meta_title",
                        "website_meta_description",
                        "website_meta_keywords",
                        "seo_name",
                    ],
                ),
                ("product", tmpl.website_ribbon_id, ["name"]),
                ("product", tmpl.base_unit_id, ["name"]),
            ]
        if self.with_attributes:
            lines = tmpl.attribute_line_ids
            targets += [
                ("attribute", lines.attribute_id, ["name"]),
                ("attribute", lines.value_ids, ["name"]),
            ]
        if self.with_categories:
            # Трохите на страницата показват и родителите на категорията.
            categories = self.env["product.public.category"].search(
                [("id", "parent_of", tmpl.public_categ_ids.ids)]
            )
            targets += [
                ("category", categories, ["name"]),
                ("category", tmpl.product_tag_ids, ["name"]),
            ]
        if self.with_page and self.env["ir.ui.view"].has_access("write"):
            targets.append(("page", self._get_page_views(), ["arch_db"]))
        return targets

    def _record_label(self, record):
        if record._name == "ir.ui.view":
            website_name = record.website_id.name or self.env._("All websites")
            return f"{record.name} ({website_name})"
        return record.display_name

    def _prepare_line_vals(self):
        self.ensure_one()
        lang_codes = self.lang_ids.mapped("code")
        if not lang_codes:
            return []
        lang_ids = {lang.code: lang.id for lang in self.lang_ids}
        lang_order = {code: index for index, code in enumerate(lang_codes)}
        vals_list = []
        for section, records, fnames in self._get_translation_targets():
            for record in records:
                for fname in fnames:
                    field = record._fields.get(fname)
                    if not field or not field.translate:
                        continue
                    vals_list += self._prepare_field_line_vals(
                        section, record, field, lang_codes, lang_ids, lang_order
                    )
        for sequence, vals in enumerate(vals_list, start=1):
            vals["sequence"] = sequence
        return vals_list

    def _prepare_field_line_vals(
        self, section, record, field, lang_codes, lang_ids, lang_order
    ):
        translations, _context = record.get_field_translations(
            field.name, langs=lang_codes
        )
        is_term = callable(field.translate)
        # get_field_translations връща езиците в произволен ред — подреждаме
        # по реда на термините в изходния текст, после по реда на езиците.
        sources = dict.fromkeys(t["source"] for t in translations)
        term_order = {source: index for index, source in enumerate(sources)}
        translations.sort(
            key=lambda t: (term_order[t["source"]], lang_order[t["lang"]])
        )
        record_label = self._record_label(record)
        field_label = field._description_string(self.env)
        vals_list = []
        for translation in translations:
            source = translation["source"]
            if not source:
                continue
            if is_term and not any(char.isalpha() for char in source):
                # Термини само от пунктуация („:“, „,“) нямат какво да се
                # превежда, а задръстват списъка.
                continue
            lang = translation["lang"]
            value = translation["value"] or ""
            if lang == "en_US":
                # en_US е самият изход — редът служи за поправка на оригинала.
                value = source
            elif not is_term and value == source:
                # Липсващият превод на обикновено поле се чете като en_US
                # стойността; показваме го като празен, за да личи.
                value = ""
            if self.only_missing and value:
                continue
            vals_list.append(
                {
                    "section": section,
                    "res_model": record._name,
                    "res_id": record.id,
                    "record_name": record_label,
                    "field_name": field.name,
                    "field_label": field_label,
                    "is_term": is_term,
                    "lang_id": lang_ids[lang],
                    "source": source,
                    "value": value,
                    "original_value": value,
                }
            )
        return vals_list

    # ------------------------------------------------------------------
    # Действия
    # ------------------------------------------------------------------

    def _load_lines(self):
        for wizard in self:
            wizard.line_ids = [Command.clear()] + [
                Command.create(vals) for vals in wizard._prepare_line_vals()
            ]

    def _action_reopen(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Translate Product Page"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_load(self):
        self._load_lines()
        return self._action_reopen()

    def _collect_changes(self):
        """Групира променените редове в аргументи за update_field_translations.

        Обикновено поле: {език: стойност}; празно маха превода (False).
        Поле с термини (HTML, arch_db): {език: {изходен термин: превод}};
        празен низ маха превода на термина.
        """
        self.ensure_one()
        changes = defaultdict(dict)
        for line in self.line_ids:
            new_value = line.value or ""
            if new_value == (line.original_value or ""):
                continue
            key = (line.res_model, line.res_id, line.field_name)
            lang = line.lang_id.code
            if line.is_term:
                changes[key].setdefault(lang, {})[line.source] = new_value
            else:
                changes[key][lang] = new_value or False
        return changes

    def action_save(self):
        self.ensure_one()
        for (model, res_id, fname), translations in self._collect_changes().items():
            self.env[model].browse(res_id).update_field_translations(
                fname, translations
            )
        self._load_lines()
        return self._action_reopen()


class ProductPageTranslateWizardLine(models.TransientModel):
    _name = "product.page.translate.wizard.line"
    _description = "Product Page Translation Term"
    _order = "sequence, id"

    wizard_id = fields.Many2one(
        "product.page.translate.wizard", required=True, ondelete="cascade"
    )
    sequence = fields.Integer()
    section = fields.Selection(SECTIONS, readonly=True)
    res_model = fields.Char(string="Model", readonly=True)
    res_id = fields.Many2oneReference(
        string="Record ID", model_field="res_model", readonly=True
    )
    record_name = fields.Char(string="Element", readonly=True)
    field_name = fields.Char(string="Technical Field Name", readonly=True)
    field_label = fields.Char(string="Field", readonly=True)
    is_term = fields.Boolean(readonly=True)
    lang_id = fields.Many2one("res.lang", string="Language", readonly=True)
    source = fields.Text(readonly=True)
    value = fields.Text(string="Translation")
    original_value = fields.Text(readonly=True)
