# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
"""Справочник на Комбинираната номенклатура (КН8) по години.

КН се приема наново всяка година (регламент до 31.10, в сила от 1.01),
затова един и същи код се пази по веднъж за всяка година. Справочникът се
зарежда от файл (листът NC8_TARIC на НАП или CN_<година>.xlsx на НСИ) през
уизарда за импорт — модулът не носи вградени чужди данни.
"""
import re

from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError

_CN8_RE = re.compile(r"^\d{8}$")


class L10nBgCnCode(models.Model):
    _name = "l10n.bg.cn.code"
    _description = "Combined Nomenclature Code (CN8) by Year"
    _order = "year desc, code"
    _rec_names_search = ["code", "name"]

    code = fields.Char(
        string="CN8 Code",
        size=8,
        required=True,
        index=True,
        help="Eight-digit Combined Nomenclature code, digits only.",
    )
    year = fields.Integer(
        string="Year",
        required=True,
        index=True,
        default=lambda self: fields.Date.context_today(self).year,
        help="Year in which this version of the Combined Nomenclature "
             "is in force.",
    )
    name = fields.Char(
        string="Description",
        translate=True,
    )
    supplementary_unit = fields.Char(
        string="Supplementary Unit",
        help="Supplementary unit foreseen by the CN for this code "
             "(e.g. p/st, m2, l, kg …). Empty when only the net mass "
             "is declared.",
    )
    hs6 = fields.Char(
        string="HS6 Code",
        compute="_compute_hs6",
        store=True,
        index=True,
    )
    active = fields.Boolean(default=True)

    _code_year_unique = models.Constraint(
        "UNIQUE (code, year)",
        "A CN8 code can appear only once per year.",
    )

    @api.depends("code")
    def _compute_hs6(self):
        for rec in self:
            rec.hs6 = rec.code[:6] if rec.code else False

    @api.depends("code", "name")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = (
                f"{rec.code} {rec.name}" if rec.name else (rec.code or "")
            )

    @api.constrains("code", "year")
    def _check_code(self):
        for rec in self:
            if not rec.code or not _CN8_RE.match(rec.code):
                raise ValidationError(_(
                    "The CN8 code '%s' must contain exactly 8 digits.",
                    rec.code or "",
                ))
            if rec.year < 1988 or rec.year > 2999:
                raise ValidationError(_(
                    "The year %s is not a valid Combined Nomenclature year.",
                    rec.year,
                ))

    # ------------------------------------------------------------------
    # Кеширан достъп: множеството кодове за година
    # ------------------------------------------------------------------
    @api.model
    @tools.ormcache("year")
    def _l10n_bg_codes_for_year(self, year):
        """Множеството активни КН8 за годината (frozenset; празно = няма справочник).

        Кешът се чисти при всяка промяна на справочника (create/write/unlink),
        затова SAF-T и проверките не правят по една заявка на артикул.
        """
        self.flush_model(["code", "year", "active"])
        self.env.cr.execute(
            "SELECT code FROM l10n_bg_cn_code WHERE year = %s AND active",
            (year,),
        )
        return frozenset(row[0] for row in self.env.cr.fetchall())

    @api.model
    def _l10n_bg_has_year(self, year):
        """Има ли зареден справочник за годината."""
        return bool(self._l10n_bg_codes_for_year(year))

    @api.model
    def _l10n_bg_is_known(self, cn8, year):
        """Валиден ли е КН8 за годината.

        Празен справочник за годината = няма с какво да се сравни;
        тогава форматът решава (връща True), както е решено от Росен.
        """
        codes = self._l10n_bg_codes_for_year(year)
        return not codes or cn8 in codes

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env.registry.clear_cache()
        return records

    def write(self, vals):
        res = super().write(vals)
        if {"code", "year", "active"} & set(vals):
            self.env.registry.clear_cache()
        return res

    def unlink(self):
        res = super().unlink()
        self.env.registry.clear_cache()
        return res
