# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Разширение на Odoo db manager-а с две български полета.

`/web/database/manager` е **nodb** страница — рендерира се през
`qweb_render` (standalone), затова модулна `<template inherit_id>` НЕ се
прилага. Единственият надежден начин = override на `web` `Database`
контролера + lxml пост-обработка на върнатия HTML (самият core
database.py ползва lxml по същата причина).

Поток: при Country=Bulgaria + попълнени полета → след като core-ът
създаде базата (Odoo авто-инсталира l10n_bg → l10n_bg_config (auto) →
този модул (auto)), записваме ЕИК/ДДС + KID върху главната фирма.
`ir.actions.todo` (в data/) после отваря водения инсталатор при първи
вход на админа.
"""

import logging

from lxml import html as lxml_html

import odoo
from odoo import SUPERUSER_ID, api, http
from odoo.addons.web.controllers.database import Database

_logger = logging.getLogger(__name__)

# Двете BG полета — инжектират се в края на create-формата. UI стрингове
# на английски (правило); видими винаги, но се консумират само при
# country_code == 'bg'.
_BG_FIELDS_HTML = """
<div class="mb-3 row field-l10n-bg" id="l10n_bg_db_installer_fields">
  <label for="l10n_bg_vat_eik" class="col-md-4 col-form-label">
    VAT / UIC (Bulgaria)
  </label>
  <div class="col-md-8">
    <input type="text" name="l10n_bg_vat_eik" id="l10n_bg_vat_eik"
           class="form-control"
           placeholder="BG123456789 or 123456789"/>
  </div>
</div>
<div class="mb-3 row field-l10n-bg">
  <label for="l10n_bg_kid" class="col-md-4 col-form-label">
    KID codes (Bulgaria)
  </label>
  <div class="col-md-8">
    <input type="text" name="l10n_bg_kid" id="l10n_bg_kid"
           class="form-control" placeholder="e.g. 41, 43.21 or 6201"/>
  </div>
</div>
"""


class L10nBgDatabase(Database):
    """Надгражда web `Database` — добавя 2 BG полета и seed-ва новата
    база. Route-овете са идентични на core (verified Odoo 19)."""

    def _l10n_bg_inject_fields(self, response):
        """lxml инжекция на 2-те полета в create-формата."""
        try:
            payload = response.get_data(as_text=True)
        except Exception:  # noqa: BLE001 — напр. redirect без тяло
            return response
        if not payload or "/web/database/create" not in payload:
            return response
        try:
            doc = lxml_html.fromstring(payload)
            forms = doc.xpath(
                '//form[contains(@action, "/web/database/create")]'
            )
            if not forms:
                return response
            frag = lxml_html.fragment_fromstring(
                _BG_FIELDS_HTML, create_parent="div"
            )
            bg_rows = list(frag)
            # Намери row-а с country_code select-а и вмъкни BG полетата
            # СЛЕД него, ПРЕДИ Demo Data row-а (Rosen 2026-05-20: „двете
            # нови полета трябва да са преди демо датата след кънтри").
            # addnext() слага immediate next sibling → за да запазим
            # реда на двете BG полета iterate-ваме в обратен ред.
            country_rows = forms[0].xpath(
                './/div[contains(@class, "row")]'
                '[.//*[@name="country_code"]]'
            )
            if country_rows:
                anchor = country_rows[0]
                for child in reversed(bg_rows):
                    anchor.addnext(child)
            else:
                # Fallback (анкерът липсва) → в края на формата.
                for child in bg_rows:
                    forms[0].append(child)
            response.set_data(lxml_html.tostring(doc, encoding="unicode"))
        except Exception:  # noqa: BLE001 — UI nicety; не чупи manager-а
            _logger.exception(
                "l10n_bg_db_installer: BG fields injection failed"
            )
        return response

    @http.route("/web/database/manager", type="http", auth="none")
    def manager(self, **kw):
        response = super().manager(**kw)
        return self._l10n_bg_inject_fields(response)

    @http.route(
        "/web/database/create",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
    )
    def create(self, master_pwd, name, lang, password, **post):
        vat_eik = (post.get("l10n_bg_vat_eik") or "").strip()
        kid = (post.get("l10n_bg_kid") or "").strip()
        country_code = post.get("country_code") or False
        response = super().create(
            master_pwd, name, lang, password, **post
        )
        if (
            country_code == "bg"
            and (vat_eik or kid)
            and odoo.service.db.exp_db_exist(name)
        ):
            try:
                self._l10n_bg_seed_new_db(name, vat_eik, kid)
            except Exception:  # noqa: BLE001 — seed-ът не бива да чупи
                _logger.exception(
                    "l10n_bg_db_installer: post-create seeding "
                    "failed for db %s",
                    name,
                )
        return response

    def _l10n_bg_seed_new_db(self, dbname, vat_eik, kid):
        """Записва ЕИК/ДДС + KID върху главната фирма на новата база.
        Стъперът V0 'Fetch from Trade Register' ползва company.vat;
        KID отива в l10n_bg_kid_codes (free-text bootstrap го резолвира
        при зареждане на сметкоплана)."""
        registry = odoo.modules.registry.Registry(dbname)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            company = env.ref(
                "base.main_company", raise_if_not_found=False
            ) or env["res.company"].search([], order="id", limit=1)
            if not company:
                return
            vals = {}
            if vat_eik:
                vals["vat"] = vat_eik
            if kid and "l10n_bg_kid_codes" in env["res.company"]._fields:
                vals["l10n_bg_kid_codes"] = kid
            if vals:
                company.write(vals)
