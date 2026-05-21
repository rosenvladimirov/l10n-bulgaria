# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Разширение на Odoo db manager-а с две български полета + background
install на l10n_bg cascade.

`/web/database/manager` е **nodb** страница — рендерира се през
`qweb_render` (standalone), затова модулна `<template inherit_id>` НЕ се
прилага. Единственият надежден начин = override на `web` `Database`
контролера + lxml пост-обработка на върнатия HTML (самият core
database.py ползва lxml по същата причина).

Поток (при Country=Bulgaria):
1. super().create() — създава DB с base+web (~5s)
2. seed-ва pending VAT/EIK + KID в ir.config_parameter
3. стартира background thread за `l10n_bg.button_immediate_install`
   (cascade → l10n_bg_config → l10n_bg_db_installer → l10n_bg_onboarding
   ако е налично)
4. response = progress page с JS poller към /web/database/l10n_bg_install_status
5. при завършване: poller вижда status='ready' → redirect към /odoo?db=<name>;
   ако l10n_bg_onboarding е в server_wide_modules → OWL onboarding wizard
   тригерира автоматично; ако не → ir.actions.todo stepper wizard.

CF 100s timeout: cascade install отнема 80-120s. Background thread +
JS poll page държи всеки HTTP request под 100s.
"""

import logging
import threading

import werkzeug.utils
import werkzeug.wrappers
from lxml import html as lxml_html

import odoo
from odoo import SUPERUSER_ID, api, http
from odoo.addons.web.controllers.database import Database

_logger = logging.getLogger(__name__)

# Tracking на активни background install threads, ключ = dbname. Daemon
# threads, killед при server stop. _install_lock пази dict-а от race.
_install_lock = threading.Lock()
_install_threads = {}

# ICP keys — централизирани за избягване на typos при четене/писане.
_ICP_STATUS = "l10n_bg.install_status"
_ICP_MESSAGE = "l10n_bg.install_message"
_ICP_PENDING_VAT = "l10n_bg.pending_vat_eik"
_ICP_PENDING_KID = "l10n_bg.pending_kid"

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

# Progress page — JS poller извиква /web/database/l10n_bg_install_status
# на всеки 2s. При status='ready' → redirect; при 'error' → червен bar.
_PROGRESS_HTML = """<!DOCTYPE html>
<html><head>
<meta charset="utf-8"/>
<title>Setting up Bulgarian Odoo localization...</title>
<link rel="stylesheet" href="/web/static/lib/bootstrap/dist/css/bootstrap.min.css"/>
<style>body{padding:3rem 1rem;max-width:680px;margin:auto}</style>
</head><body>
<h3>Setting up your Bulgarian Odoo database</h3>
<p class="text-muted">Database: <code>__DBNAME__</code></p>
<div class="progress my-4" style="height:1.5rem">
  <div id="bar" class="progress-bar progress-bar-striped progress-bar-animated bg-primary" style="width:100%">Installing modules...</div>
</div>
<pre id="log" class="bg-light p-3 small" style="max-height:280px;overflow:auto"></pre>
<p id="status" class="text-info">Starting installation...</p>
<script>
const dbname = "__DBNAME__";
const logEl = document.getElementById("log");
const statusEl = document.getElementById("status");
const barEl = document.getElementById("bar");
let lastMsg = "";
function append(msg){
  if (msg && msg !== lastMsg){
    const t = new Date().toLocaleTimeString();
    logEl.textContent += "[" + t + "] " + msg + "\\n";
    logEl.scrollTop = logEl.scrollHeight;
    lastMsg = msg;
  }
}
function poll(){
  fetch("/web/database/l10n_bg_install_status?dbname=" + encodeURIComponent(dbname))
    .then(r => r.json())
    .then(d => {
      const s = (d && d.status) || "unknown";
      const m = (d && d.message) || "";
      statusEl.textContent = m || s;
      append(m);
      if (s === "ready"){
        barEl.classList.remove("progress-bar-animated", "bg-primary");
        barEl.classList.add("bg-success");
        barEl.textContent = "Done!";
        setTimeout(() => window.location = "/odoo?db=" + encodeURIComponent(dbname), 1200);
      } else if (s === "error"){
        barEl.classList.remove("progress-bar-animated", "bg-primary");
        barEl.classList.add("bg-danger");
        barEl.textContent = "Failed";
      } else {
        setTimeout(poll, 2000);
      }
    })
    .catch(() => setTimeout(poll, 5000));
}
poll();
</script>
</body></html>
"""


def _set_status(dbname, status, message=""):
    """Update install status в ir.config_parameter (нов cursor, idempotent)."""
    try:
        registry = odoo.modules.registry.Registry(dbname)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            ICP = env["ir.config_parameter"].sudo()
            ICP.set_param(_ICP_STATUS, status)
            if message:
                ICP.set_param(_ICP_MESSAGE, message)
    except Exception:  # noqa: BLE001 — status writes never fatal
        _logger.exception(
            "l10n_bg_db_installer: status update failed (db=%s)", dbname
        )


def _background_install(dbname):
    """Cascade install на l10n_bg + apply pending VAT/KID. Изпълнява се
    в daemon thread; обновява status през ir.config_parameter, който JS
    poller-ът чете.
    """
    try:
        _set_status(dbname, "running", "Updating module list...")
        registry = odoo.modules.registry.Registry(dbname)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            M = env["ir.module.module"].sudo()
            try:
                M.update_list()
            except Exception:  # noqa: BLE001
                _logger.exception(
                    "l10n_bg_db_installer: update_list failed on %s",
                    dbname,
                )
            l10n_bg = M.search(
                [
                    ("name", "=", "l10n_bg"),
                    ("state", "in", ("uninstalled", "to install")),
                ],
                limit=1,
            )
            if l10n_bg:
                _set_status(
                    dbname, "running",
                    "Installing l10n_bg (cascade: config + db_installer + "
                    "onboarding)...",
                )
                _logger.info(
                    "l10n_bg_db_installer: cascade install on %s", dbname
                )
                # button_immediate_install commit-ва вътрешно и презарежда
                # registry; cursor-ът ни остарява веднага след това.
                l10n_bg.button_immediate_install()
            else:
                _set_status(dbname, "running", "l10n_bg already installed")

        # Apply pending VAT/KID върху главната компания. Свеж registry
        # cursor — l10n_bg_config поста-installation вече дефинира
        # res.company.vat и l10n_bg_kid_codes полета.
        _set_status(dbname, "running", "Applying VAT/EIK + KID...")
        registry = odoo.modules.registry.Registry(dbname)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            ICP = env["ir.config_parameter"].sudo()
            vat_eik = ICP.get_param(_ICP_PENDING_VAT) or ""
            kid = ICP.get_param(_ICP_PENDING_KID) or ""
            if vat_eik or kid:
                company = env.ref(
                    "base.main_company", raise_if_not_found=False
                ) or env["res.company"].search([], order="id", limit=1)
                if company:
                    vals = {}
                    fields = env["res.company"]._fields
                    if vat_eik and "vat" in fields:
                        vals["vat"] = vat_eik
                    if kid and "l10n_bg_kid_codes" in fields:
                        vals["l10n_bg_kid_codes"] = kid
                    if vals:
                        company.write(vals)
                # Cleanup pending: empty string е достатъчно (set_param
                # с '' изтрива записа в Odoo 19 ir.config_parameter).
                ICP.set_param(_ICP_PENDING_VAT, "")
                ICP.set_param(_ICP_PENDING_KID, "")

        _set_status(dbname, "ready", "Installation complete")
        _logger.info(
            "l10n_bg_db_installer: cascade install completed on %s", dbname
        )
    except Exception as exc:  # noqa: BLE001
        _logger.exception(
            "l10n_bg_db_installer: cascade install failed on %s", dbname
        )
        _set_status(dbname, "error", f"{type(exc).__name__}: {exc}")


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
        is_bg = country_code == "bg" and odoo.service.db.exp_db_exist(name)
        if not is_bg:
            return response
        try:
            self._l10n_bg_seed_new_db(name, vat_eik, kid)
        except Exception:  # noqa: BLE001 — seed не бива да чупи create-а
            _logger.exception(
                "l10n_bg_db_installer: seed/spawn failed for db %s", name
            )
            return response
        # Замени стандартния redirect с progress page (JS poll).
        return werkzeug.wrappers.Response(
            _PROGRESS_HTML.replace("__DBNAME__", name),
            content_type="text/html; charset=utf-8",
        )

    @http.route(
        "/web/database/l10n_bg_install_status",
        type="http",
        auth="none",
        methods=["GET"],
        csrf=False,
    )
    def l10n_bg_install_status(self, dbname=None, **kw):
        """JSON status за JS poller-а на progress page-а."""
        import json
        if not dbname or not odoo.service.db.exp_db_exist(dbname):
            payload = {"status": "error", "message": "DB does not exist"}
        else:
            try:
                registry = odoo.modules.registry.Registry(dbname)
                with registry.cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, {})
                    ICP = env["ir.config_parameter"].sudo()
                    payload = {
                        "status": ICP.get_param(_ICP_STATUS) or "unknown",
                        "message": ICP.get_param(_ICP_MESSAGE) or "",
                    }
            except Exception as exc:  # noqa: BLE001
                payload = {"status": "error", "message": str(exc)}
        return werkzeug.wrappers.Response(
            json.dumps(payload),
            content_type="application/json",
        )

    def _l10n_bg_seed_new_db(self, dbname, vat_eik, kid):
        """Seed VAT/EIK + KID в ir.config_parameter и старира background
        cascade install. JS poller на progress page-а чете статуса.

        Daemon thread → killед при server stop. _install_lock защитава
        global dict-а от race conditions (double-create или paralleс
        race).
        """
        # Записваме pending data + initial status (тук sync,
        # за да е готово преди progress page да започне да polls-ва).
        registry = odoo.modules.registry.Registry(dbname)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            ICP = env["ir.config_parameter"].sudo()
            if vat_eik:
                ICP.set_param(_ICP_PENDING_VAT, vat_eik)
            if kid:
                ICP.set_param(_ICP_PENDING_KID, kid)
            ICP.set_param(_ICP_STATUS, "starting")
            ICP.set_param(_ICP_MESSAGE, "Background install starting...")

        # Старира background install в daemon thread (защитен от race).
        with _install_lock:
            existing = _install_threads.get(dbname)
            if existing and existing.is_alive():
                _logger.warning(
                    "l10n_bg_db_installer: install already running for %s",
                    dbname,
                )
                return
            t = threading.Thread(
                target=_background_install,
                args=(dbname,),
                name=f"l10n_bg_install_{dbname}",
                daemon=True,
            )
            _install_threads[dbname] = t
            t.start()
        _logger.info(
            "l10n_bg_db_installer: spawned background install thread "
            "for %s (vat=%s, kid=%s)",
            dbname, bool(vat_eik), bool(kid),
        )
