# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
"""„Предложи КН от името“ — ревю от човек, никога автоматичен запис.

При част от артикулите кодът стои в началото на името („48171000_Плик …“).
Уизардът изважда кода като предложение и записва само редовете, които
потребителят е отметнал. По подразбиране са отметнати само артикулите
без код; при разминаване с вече записан код редът е неотметнат и
маркиран (решение на Росен, 10.10.2026 — разминаванията се гледат от
човек). Всеки запис оставя бележка в историята на шаблона.
"""
import re

from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..models.commodity_code_utils import is_valid_commodity_code

# Код в началото на името, следван от долна черта: 8 (КН8) или 10 (TARIC10) цифри
NAME_CODE_RE = re.compile(r"^\s*(\d{10}|\d{8})_")


def code_from_name(name):
    match = NAME_CODE_RE.match(name or "")
    return match.group(1) if match else False


class L10nBgCnSuggestWizard(models.TransientModel):
    _name = "l10n.bg.cn.suggest.wizard"
    _description = "Suggest Commodity Codes from Product Names"

    line_ids = fields.One2many(
        comodel_name="l10n.bg.cn.suggest.line",
        inverse_name="wizard_id",
        string="Suggestions",
    )
    line_count = fields.Integer(compute="_compute_line_count")

    @api.depends("line_ids")
    def _compute_line_count(self):
        for wizard in self:
            wizard.line_count = len(wizard.line_ids)

    @api.model
    def _l10n_bg_candidate_products(self):
        """Вариантите за преглед: избраните (вариант/шаблон) или всички стоки."""
        ctx = self.env.context
        Product = self.env["product.product"]
        active_ids = ctx.get("active_ids") or []
        if ctx.get("active_model") == "product.product" and active_ids:
            return Product.browse(active_ids)
        if ctx.get("active_model") == "product.template" and active_ids:
            return self.env["product.template"].browse(active_ids).product_variant_ids
        return Product.search([("type", "!=", "service")])

    @api.model
    def _l10n_bg_suggestion_vals(self, products):
        vals_list = []
        for product in products:
            if product.type == "service":
                continue
            suggested = code_from_name(product.name)
            if not suggested or suggested == product.l10n_bg_commodity_code:
                continue
            differs = bool(product.l10n_bg_commodity_code)
            vals_list.append({
                "product_id": product.id,
                "suggested_code": suggested,
                "differs": differs,
                "apply": not differs,
            })
        return vals_list

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if "line_ids" in fields_list:
            products = self._l10n_bg_candidate_products()
            res["line_ids"] = [
                (0, 0, vals) for vals in self._l10n_bg_suggestion_vals(products)
            ]
        return res

    def action_apply(self):
        self.ensure_one()
        lines = self.line_ids.filtered("apply")
        if not lines:
            raise UserError(_("Select at least one suggestion to apply."))
        for line in lines:
            if not is_valid_commodity_code(line.suggested_code):
                raise UserError(_(
                    "The suggested code '%(code)s' for '%(product)s' is not "
                    "8 or 10 digits.",
                    code=line.suggested_code,
                    product=line.product_id.display_name,
                ))
        for line in lines:
            product = line.product_id
            old = product.l10n_bg_commodity_code
            product.l10n_bg_commodity_code = line.suggested_code
            product.product_tmpl_id.message_post(
                body=Markup("%s<br/>%s") % (
                    escape(_(
                        "Commodity code of %(product)s set to %(code)s from "
                        "the product name (suggestion reviewed by %(user)s).",
                        product=product.display_name,
                        code=line.suggested_code,
                        user=self.env.user.name,
                    )),
                    escape(_("Previous code: %s", old or "-")),
                ),
                subtype_xmlid="mail.mt_note",
            )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Commodity codes"),
                "message": _("%s commodity code(s) applied.", len(lines)),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }


class L10nBgCnSuggestLine(models.TransientModel):
    _name = "l10n.bg.cn.suggest.line"
    _description = "Commodity Code Suggestion"

    wizard_id = fields.Many2one(
        comodel_name="l10n.bg.cn.suggest.wizard",
        required=True,
        ondelete="cascade",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        required=True,
    )
    current_code = fields.Char(
        string="Current Code",
        related="product_id.l10n_bg_commodity_code",
    )
    suggested_code = fields.Char(string="Suggested Code", required=True)
    differs = fields.Boolean(
        string="Differs from Current",
        help="The product already has a different commodity code — "
             "review before applying.",
    )
    apply = fields.Boolean(string="Apply")
