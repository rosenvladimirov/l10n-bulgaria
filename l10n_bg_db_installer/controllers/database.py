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
import time

import psycopg2.errors
import werkzeug.utils
import werkzeug.wrappers
from lxml import html as lxml_html

import odoo
from odoo import SUPERUSER_ID, api, http
from odoo.addons.web.controllers.database import Database
from odoo.tools import config

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

# Progress page — self-contained, без external CSS (някои Odoo 19
# Bootstrap paths не работят за nodb routes). JS poller извиква
# /web/database/l10n_bg_install_status на всеки ~1.5s. При status='ready'
# → confetti + redirect; при 'error' → червен bar.
_PROGRESS_HTML = r"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8"/>
<title>Bulgarian Odoo Setup</title>
<style>
:root {
  --bg-white: #ffffff;
  --bg-green: #00966E;
  --bg-red:   #D62718;
}
* { box-sizing: border-box; }
body {
  font-family: -apple-system, "Segoe UI", system-ui, sans-serif;
  background: linear-gradient(135deg, #f6f8fa 0%, #fff 50%, #f1f5fa 100%);
  margin: 0; padding: 2rem 1rem; min-height: 100vh;
  color: #2c2c2c;
}
.flag-stripe {
  position: fixed; top: 0; left: 0; right: 0; height: 8px;
  background: linear-gradient(to right,
    var(--bg-white) 0% 33%,
    var(--bg-green) 33% 66%,
    var(--bg-red)   66% 100%);
  box-shadow: 0 2px 6px rgba(0,0,0,0.06);
  z-index: 1000;
}
.container {
  max-width: 680px; margin: 2rem auto 0;
  background: white; border-radius: 16px;
  padding: 2rem 2.2rem;
  box-shadow: 0 10px 40px rgba(0,0,0,0.07);
}
h1 {
  margin: 0 0 0.3rem; font-size: 1.45rem; font-weight: 700;
  background: linear-gradient(135deg, var(--bg-green) 0%, var(--bg-red) 100%);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;
}
.subtitle { color: #999; font-size: 0.88rem; margin: 0 0 1.5rem; }
.dbname { font-family: ui-monospace, monospace;
  background: #f3f4f6; padding: 2px 8px; border-radius: 5px;
  font-size: 0.85rem; }
.modules {
  display: flex; gap: 0.6rem; justify-content: center; margin: 1.4rem 0;
  flex-wrap: wrap;
}
.module {
  width: 90px; padding: 0.7rem 0.4rem;
  background: white; border: 2px solid #e8eaef;
  border-radius: 12px;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 4px; font-size: 0.68rem; color: #888;
  transition: all 0.4s cubic-bezier(.34,1.56,.64,1);
  position: relative;
}
.module .icon { font-size: 1.9rem; line-height: 1; filter: grayscale(0.5); transition: filter .4s; }
.module.active {
  border-color: var(--bg-green);
  background: #fafffd;
  transform: translateY(-6px);
  box-shadow: 0 10px 24px rgba(0,150,110,0.18);
  color: #00966E;
  font-weight: 600;
}
.module.active .icon { filter: none; animation: bounce 0.55s ease infinite alternate; }
.module.done {
  border-color: var(--bg-green); background: #e9f8f3;
  color: #00966E; font-weight: 600;
}
.module.done .icon { filter: none; }
.module.done::after {
  content: "✓"; position: absolute; top: -8px; right: -8px;
  width: 22px; height: 22px; background: var(--bg-green); color: white;
  border-radius: 50%; font-size: 0.85rem; font-weight: bold;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 2px 6px rgba(0,150,110,0.4);
}
@keyframes bounce { 0% { transform: translateY(0); } 100% { transform: translateY(-9px); } }

.progress-wrap {
  background: #eef1f4; border-radius: 999px; height: 14px;
  overflow: hidden; margin: 1.3rem 0; position: relative;
}
.progress {
  height: 100%; width: 4%;
  transition: width 0.8s ease-out;
  background: linear-gradient(90deg,
    var(--bg-white) 0%,
    var(--bg-green) 40%,
    var(--bg-red)   80%);
  background-size: 220% 100%;
  animation: shimmer 2.4s linear infinite;
  border-radius: 999px;
  box-shadow: inset 0 -2px 4px rgba(0,0,0,0.08);
}
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: 0% 0; } }

#status {
  text-align: center; font-weight: 500; margin: 1rem 0;
  min-height: 1.5rem; color: #555;
}
.spinner {
  display: inline-block; width: 14px; height: 14px;
  border: 2px solid #e0e0e0; border-top-color: var(--bg-green);
  border-radius: 50%; animation: spin 0.7s linear infinite;
  margin-right: 0.6rem; vertical-align: middle;
}
@keyframes spin { to { transform: rotate(360deg); } }

.log {
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 0.78rem;
  background: #fafbfc;
  border-left: 3px solid var(--bg-green);
  padding: 0.7rem 1rem; margin-top: 1.2rem;
  max-height: 180px; overflow-y: auto; border-radius: 6px;
}
.log-entry { margin: 0.25rem 0; line-height: 1.4; }
.log-time { color: #b8bcc4; }
.log-msg { color: #3a3a3a; }

.confetti {
  position: fixed; top: -20px; font-size: 1.6rem;
  pointer-events: none; animation: fall linear forwards;
  z-index: 999; user-select: none;
}
@keyframes fall {
  0% { transform: translateY(0) rotate(0); opacity: 1; }
  100% { transform: translateY(110vh) rotate(720deg); opacity: 0; }
}
.flag-wave {
  position: fixed; bottom: 1.2rem; right: 1.5rem; font-size: 3rem;
  animation: wave 1.8s ease-in-out infinite alternate;
  pointer-events: none;
  filter: drop-shadow(0 3px 8px rgba(0,0,0,0.12));
}
@keyframes wave {
  0%   { transform: rotate(-7deg) translateY(0); }
  100% { transform: rotate(7deg) translateY(-4px); }
}
</style>
</head><body>
<div class="flag-stripe"></div>
<div class="container">
  <h1>🇧🇬 Setting up your Bulgarian Odoo</h1>
  <p class="subtitle">Database: <span class="dbname">__DBNAME__</span></p>

  <div class="modules">
    <div class="module" data-mod="l10n_bg">
      <div class="icon">📊</div><span>l10n_bg</span>
    </div>
    <div class="module" data-mod="l10n_bg_config">
      <div class="icon">⚙️</div><span>config</span>
    </div>
    <div class="module" data-mod="l10n_bg_db_installer">
      <div class="icon">🪄</div><span>installer</span>
    </div>
    <div class="module" data-mod="l10n_bg_onboarding">
      <div class="icon">🎓</div><span>onboarding</span>
    </div>
  </div>

  <div class="progress-wrap"><div class="progress" id="bar"></div></div>
  <div id="status"><span class="spinner"></span>Starting installation...</div>

  <div class="log" id="log"></div>
</div>
<div class="flag-wave">🇧🇬</div>

<script>
const dbname = "__DBNAME__";
const MODS = ["l10n_bg", "l10n_bg_config", "l10n_bg_db_installer", "l10n_bg_onboarding"];
// stage detection — съчетава message текст в progressing.
const STAGES = [
  { match: "starting",        pct:  5, mod:  null },
  { match: "Updating module", pct: 18, mod: "l10n_bg" },
  { match: "Installing l10n_bg", pct: 65, mod: "l10n_bg_config" },
  { match: "Applying VAT",    pct: 92, mod: "l10n_bg_db_installer" },
  { match: "complete",        pct:100, mod: "l10n_bg_onboarding" },
];
const logEl = document.getElementById("log");
const statusEl = document.getElementById("status");
const barEl = document.getElementById("bar");
let lastMsg = "";

function append(msg) {
  if (!msg || msg === lastMsg) return;
  lastMsg = msg;
  const t = new Date().toLocaleTimeString();
  const e = document.createElement("div");
  e.className = "log-entry";
  const tEl = document.createElement("span");
  tEl.className = "log-time"; tEl.textContent = "[" + t + "] ";
  const mEl = document.createElement("span");
  mEl.className = "log-msg"; mEl.textContent = msg;
  e.appendChild(tEl); e.appendChild(mEl);
  logEl.appendChild(e);
  logEl.scrollTop = logEl.scrollHeight;
}

function updateStage(msg, status) {
  let stage = null;
  for (const s of STAGES) {
    if (msg && msg.toLowerCase().indexOf(s.match.toLowerCase()) !== -1) {
      stage = s;
    }
  }
  if (status === "ready") stage = STAGES[STAGES.length - 1];
  if (!stage) return;
  barEl.style.width = stage.pct + "%";
  const idx = stage.mod ? MODS.indexOf(stage.mod) : -1;
  MODS.forEach((m, i) => {
    const el = document.querySelector('[data-mod="' + m + '"]');
    if (!el) return;
    el.classList.remove("active", "done");
    if (status === "ready" || i < idx) el.classList.add("done");
    else if (i === idx) el.classList.add("active");
  });
}

function celebrate() {
  const emojis = ["🎉", "🎊", "✨", "🇧🇬", "💎", "⭐", "🌟"];
  for (let i = 0; i < 60; i++) {
    setTimeout(function () {
      const c = document.createElement("div");
      c.className = "confetti";
      c.textContent = emojis[Math.floor(Math.random() * emojis.length)];
      c.style.left = Math.random() * 100 + "vw";
      c.style.animationDuration = (1.8 + Math.random() * 3) + "s";
      document.body.appendChild(c);
      setTimeout(function () { c.remove(); }, 5500);
    }, i * 55);
  }
}

function poll() {
  fetch("/web/database/l10n_bg_install_status?dbname=" + encodeURIComponent(dbname))
    .then(function (r) { return r.json(); })
    .then(function (d) {
      const s = (d && d.status) || "unknown";
      const m = (d && d.message) || "";
      append(m);
      updateStage(m, s);
      if (s === "ready") {
        statusEl.innerHTML = "🎉 All set! Redirecting to your fresh Odoo...";
        celebrate();
        setTimeout(function () {
          window.location = "/odoo?db=" + encodeURIComponent(dbname);
        }, 2800);
      } else if (s === "error") {
        statusEl.innerHTML = "❌ " + (m || "Installation failed");
        barEl.style.background = "var(--bg-red)";
        barEl.style.animation = "none";
      } else {
        const span = document.createElement("span");
        span.className = "spinner";
        statusEl.innerHTML = "";
        statusEl.appendChild(span);
        statusEl.appendChild(document.createTextNode(m || s));
        setTimeout(poll, 1500);
      }
    })
    .catch(function () { setTimeout(poll, 4000); });
}
poll();
</script>
</body></html>
"""


def _grant_admin_full_access(env):
    """Add internal admin user към всички НЕ-portal/public групи.

    Стратегия: search всички res.groups, изключи:
      - base.group_portal (Portal user — external clients)
      - base.group_public (Public — anonymous website visitor)
      - category 'Hidden' (internal system tags, не са user-facing)
      - групи с име съдържащо 'Portal', 'Public', 'Share', 'External'
        (защита срещу third-party модули които дефинират подобни групи
        без явен xml_id към base.group_portal)

    ВАЖНО: вътре в Odoo, добавянето на portal/public група към internal
    user превключва неговата res.users.share=True → user-ът губи Internal
    User права (counter-intuitively). Затова филтрираме строго.

    Returns: брой добавени групи.
    """
    admin = env.ref("base.user_admin", raise_if_not_found=False)
    if not admin:
        return 0
    excluded_ids = []
    for xmlid in ("base.group_portal", "base.group_public"):
        g = env.ref(xmlid, raise_if_not_found=False)
        if g:
            excluded_ids.append(g.id)
    Group = env["res.groups"].sudo()
    domain = [("id", "not in", excluded_ids)]
    hidden_cat = env.ref(
        "base.module_category_hidden", raise_if_not_found=False
    )
    if hidden_cat:
        domain.append(("category_id", "!=", hidden_cat.id))
    candidates = Group.search(domain)
    blocked = ("portal", "public", "share", "external")
    safe = candidates.filtered(
        lambda g: not any(
            kw in (g.name or "").lower() for kw in blocked
        )
    )
    # Изключи и групите, които вече има (за чисти logs)
    existing = set(admin.groups_id.ids)
    new_ids = [gid for gid in safe.ids if gid not in existing]
    if new_ids:
        admin.sudo().write(
            {"groups_id": [(4, gid) for gid in new_ids]}
        )
    return len(new_ids)


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

        # button_immediate_install заключва ir_cron с FOR UPDATE NOWAIT.
        # На свежа DB cron-ите стартират едновременно (Base: Auto-vacuum,
        # Portal Users Deletion и др.) и държат lock-а 1-3s. NOWAIT
        # fail-ва веднага → psycopg2.errors.SerializationFailure → нашият
        # cursor се аborт-ва. Retry с пауза до cron-ите свършат.
        max_retries = 20
        for attempt in range(max_retries):
            try:
                registry = odoo.modules.registry.Registry(dbname)
                with registry.cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, {})
                    M = env["ir.module.module"].sudo()
                    l10n_bg = M.search(
                        [
                            ("name", "=", "l10n_bg"),
                            (
                                "state", "in",
                                ("uninstalled", "to install"),
                            ),
                        ],
                        limit=1,
                    )
                    if not l10n_bg:
                        _set_status(
                            dbname, "running",
                            "l10n_bg already installed",
                        )
                        break
                    _set_status(
                        dbname, "running",
                        "Installing l10n_bg (cascade: config + "
                        "db_installer + onboarding)..."
                        + (f" [retry {attempt}]" if attempt else ""),
                    )
                    _logger.info(
                        "l10n_bg_db_installer: cascade install on %s "
                        "(attempt %d)",
                        dbname, attempt + 1,
                    )
                    l10n_bg.button_immediate_install()
                break  # success
            except (
                psycopg2.errors.SerializationFailure,
                psycopg2.errors.InFailedSqlTransaction,
            ) as exc:
                # ir_cron заключен от concurrent cron job.
                # SerializationFailure = direct NOWAIT fail.
                # InFailedSqlTransaction = Odoo bug при render на UserError
                # за cron lock — внутрешният cursor абортира при
                # translation lookup и грешката се wrap-ва.
                # И двете → wait + retry.
                if attempt + 1 < max_retries:
                    _set_status(
                        dbname, "running",
                        f"Cron busy, waiting "
                        f"(attempt {attempt + 1}/{max_retries})...",
                    )
                    _logger.warning(
                        "l10n_bg_db_installer: cron lock contention "
                        "(%s) on %s (attempt %d) — retry in 3s",
                        type(exc).__name__, dbname, attempt + 1,
                    )
                    time.sleep(3)
                    continue
                raise

        # Apply pending VAT/KID върху главната компания. Свеж registry
        # cursor — l10n_bg_config поста-installation вече дефинира
        # res.company.vat и l10n_bg_kid_codes полета.
        _set_status(dbname, "running", "Applying VAT/EIK + KID...")
        vat_eik_for_fetch = ""
        registry = odoo.modules.registry.Registry(dbname)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            ICP = env["ir.config_parameter"].sudo()
            vat_eik = ICP.get_param(_ICP_PENDING_VAT) or ""
            kid = ICP.get_param(_ICP_PENDING_KID) or ""
            vat_eik_for_fetch = vat_eik
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

        # Auto Trade Register fetch — за registry_fetch стъпката на
        # V0 (l10n.bg.vertical.step.registry_fetch=True). Това попълва
        # company name/address/representative от търговския регистър по
        # VAT/UIC, без user-ът да го прави ръчно през wizard-а после.
        #
        # ВАЖНО: action_registry_fetch е 2-фазен:
        #  1-ва call: ако l10n_bg_company_registry липсва → install + early
        #             return (без fetch — модулът е installed едва сега).
        #  2-ра call: модулът installed → действителен fetch + populate.
        # Затова правим 2 call-а в отделни cursor-и (между тях
        # button_immediate_install commit-ва и registry се reload-ва).
        if vat_eik_for_fetch:
            _set_status(
                dbname, "running",
                f"Fetching company data from Trade Register "
                f"(VAT/UIC={vat_eik_for_fetch})...",
            )
            try:
                registry_step_vid = None
                for attempt in range(2):
                    registry = odoo.modules.registry.Registry(dbname)
                    with registry.cursor() as cr:
                        env = api.Environment(cr, SUPERUSER_ID, {})
                        Step = env["l10n.bg.vertical.step"].sudo()
                        # step.done е computed (не store) → filter в Python.
                        candidates = Step.search(
                            [("registry_fetch", "=", True)],
                            order="vertical_id, sequence, id",
                        )
                        registry_step = candidates.filtered(
                            lambda s: not s.done
                        )[:1]
                        if not registry_step:
                            break  # already done — skip
                        registry_step_vid = (
                            registry_step.vertical_id.id
                        )
                        Wiz = env["l10n.bg.vertical.wizard"].sudo()
                        wiz = Wiz.create(
                            {
                                "vertical_id": registry_step_vid,
                                "registry_vat_eik": vat_eik_for_fetch,
                            }
                        )
                        wiz.action_registry_fetch()
                        _logger.info(
                            "l10n_bg_db_installer: Trade Register call "
                            "%d/2 OK (VAT=%s, step=%s)",
                            attempt + 1, vat_eik_for_fetch,
                            registry_step.id,
                        )
            except Exception:  # noqa: BLE001 — fetch failure не блокира
                _logger.exception(
                    "l10n_bg_db_installer: Trade Register fetch failed "
                    "on %s", dbname,
                )

        # Install ALL required plan modules (V0-V12). Cascade на l10n_bg
        # покрива auto_install chain (config/db_installer/onboarding).
        # Plan-а включва още ~25 модула (l10n_bg_tax_offices,
        # l10n_bg_api_nra, l10n_bg_bank_wallet, l10n_bg_infopay,
        # l10n_bg_intrastat, l10n_bg_hr_payroll, l10n_bg_tax_admin, ...)
        # които НЕ са auto_install. Преди тях се очакваше client wizard
        # да ги install-не чрез action_install, но client-side ORM call
        # пада на cron lock → wizard виси. Решение: install в backend
        # със retry pattern → client wizard вижда "all done" и recurse
        # безшумно през всички V0-V12 до finale.
        _set_status(
            dbname, "running",
            "Installing remaining BG plan modules...",
        )
        plan_max_retries = 20
        for plan_attempt in range(plan_max_retries):
            try:
                registry = odoo.modules.registry.Registry(dbname)
                with registry.cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, {})
                    Step = env["l10n.bg.vertical.step"].sudo()
                    required_steps = Step.search(
                        [
                            ("step_type", "=", "install_module"),
                            ("optional", "=", False),
                        ]
                    )
                    mod_names = sorted(set(
                        n for n in required_steps.mapped("module_name")
                        if n
                    ))
                    if not mod_names:
                        break
                    M = env["ir.module.module"].sudo()
                    plan_mods = M.search(
                        [
                            ("name", "in", mod_names),
                            (
                                "state", "in",
                                ("uninstalled", "to install"),
                            ),
                        ]
                    )
                    if not plan_mods:
                        break  # всички вече installed
                    _logger.info(
                        "l10n_bg_db_installer: installing plan "
                        "modules: %s (attempt %d)",
                        plan_mods.mapped("name"), plan_attempt + 1,
                    )
                    plan_mods.button_immediate_install()
                break  # success
            except (
                psycopg2.errors.SerializationFailure,
                psycopg2.errors.InFailedSqlTransaction,
            ) as exc:
                if plan_attempt + 1 < plan_max_retries:
                    _set_status(
                        dbname, "running",
                        f"Plan: cron busy, waiting "
                        f"({plan_attempt + 1}/{plan_max_retries})...",
                    )
                    _logger.warning(
                        "l10n_bg_db_installer: plan modules cron lock "
                        "(%s) on %s (attempt %d) — retry in 3s",
                        type(exc).__name__, dbname, plan_attempt + 1,
                    )
                    time.sleep(3)
                    continue
                _logger.exception(
                    "l10n_bg_db_installer: plan modules install "
                    "failed on %s after %d attempts",
                    dbname, plan_max_retries,
                )
                break
            except Exception:  # noqa: BLE001
                _logger.exception(
                    "l10n_bg_db_installer: plan modules install "
                    "failed on %s", dbname,
                )
                break

        # Допълнителни модули от odoo.conf [l10n_bg_onboarding] секция.
        # Това е extension hook — Rosen: "освен модулите на wizard-а
        # искам да зареждаш допълнително и модулите от конфига". Plan-а
        # (V0-V12) install-ва BG-специфичните модули; config extras
        # покрива общи Odoo модули за демо setup-и (sale, purchase, crm,
        # mrp, pos, и т.н.). Pattern в odoo.conf:
        #   [l10n_bg_onboarding]
        #   extra_modules = sale_management,purchase,crm,mrp,point_of_sale
        # config.misc е сменян между Odoo версиите (понякога dict,
        # понякога module, понякога липсва). Чета odoo.conf-а директно
        # през configparser за пълна предсказуемост.
        extras_raw = ""
        try:
            import configparser
            rcfile = config.rcfile or "/etc/odoo/odoo.conf"
            parser = configparser.ConfigParser(strict=False)
            parser.read(rcfile)
            if parser.has_section("l10n_bg_onboarding"):
                extras_raw = parser.get(
                    "l10n_bg_onboarding",
                    "extra_modules",
                    fallback="",
                ) or ""
        except Exception:  # noqa: BLE001
            _logger.exception(
                "l10n_bg_db_installer: reading [l10n_bg_onboarding] "
                "from %s failed",
                getattr(config, "rcfile", "<no rcfile>"),
            )
        extras = [m.strip() for m in extras_raw.split(",") if m.strip()]
        if extras:
            _set_status(
                dbname, "running",
                f"Installing extras from odoo.conf: "
                f"{', '.join(extras)}...",
            )
            # Същия retry pattern като l10n_bg cascade — cron lock може
            # да хване и extras install (нов wave от crons стартира при
            # registry reload след cascade-а).
            extras_max_retries = 20
            for ex_attempt in range(extras_max_retries):
                try:
                    registry = odoo.modules.registry.Registry(dbname)
                    with registry.cursor() as cr:
                        env = api.Environment(cr, SUPERUSER_ID, {})
                        M = env["ir.module.module"].sudo()
                        extra_mods = M.search(
                            [
                                ("name", "in", extras),
                                (
                                    "state", "in",
                                    ("uninstalled", "to install"),
                                ),
                            ]
                        )
                        missing = (
                            set(extras) - set(extra_mods.mapped("name"))
                        )
                        if missing:
                            _logger.warning(
                                "l10n_bg_db_installer: extras not found "
                                "or already installed: %s",
                                sorted(missing),
                            )
                        if extra_mods:
                            _logger.info(
                                "l10n_bg_db_installer: installing "
                                "extras: %s (attempt %d)",
                                extra_mods.mapped("name"), ex_attempt + 1,
                            )
                            extra_mods.button_immediate_install()
                    break  # success
                except (
                    psycopg2.errors.SerializationFailure,
                    psycopg2.errors.InFailedSqlTransaction,
                ) as exc:
                    if ex_attempt + 1 < extras_max_retries:
                        _set_status(
                            dbname, "running",
                            f"Extras: cron busy, waiting "
                            f"({ex_attempt + 1}/{extras_max_retries})...",
                        )
                        _logger.warning(
                            "l10n_bg_db_installer: extras cron lock "
                            "(%s) on %s (attempt %d) — retry in 3s",
                            type(exc).__name__, dbname, ex_attempt + 1,
                        )
                        time.sleep(3)
                        continue
                    _logger.exception(
                        "l10n_bg_db_installer: extras install failed "
                        "on %s after %d attempts",
                        dbname, extras_max_retries,
                    )
                    break
                except Exception:  # noqa: BLE001 — други грешки → log + skip
                    _logger.exception(
                        "l10n_bg_db_installer: extras install failed "
                        "on %s", dbname,
                    )
                    break

        # Финален hook: дай на admin user-а ВСИЧКИ съдържателни групи
        # на инсталираните модули. ВНИМАНИЕ: portal/public/share групи
        # СЕ ИЗКЛЮЧВАТ — добавянето им на internal admin user сменя
        # неговата природа от Internal към Portal (счупва ACL flows).
        _set_status(
            dbname, "running",
            "Granting admin access to installed modules...",
        )
        try:
            registry = odoo.modules.registry.Registry(dbname)
            with registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                granted = _grant_admin_full_access(env)
                _logger.info(
                    "l10n_bg_db_installer: granted admin %d "
                    "groups on %s",
                    granted, dbname,
                )
        except Exception:  # noqa: BLE001 — permissions не блокира flow
            _logger.exception(
                "l10n_bg_db_installer: admin permission grant failed "
                "on %s", dbname,
            )

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
            # Odoo 19 DB manager-а рендерира ДВЕ форми за create:
            # form 1 = top-level (показва се ако няма DB-та)
            # form 2 = вътре в .modal-fade.o_database_create (Bootstrap
            #   модал, отваря се с бутон "Create Database" при налични
            #   DB-та). И двете трябва да имат BG полетата.
            for form in forms:
                frag = lxml_html.fragment_fromstring(
                    _BG_FIELDS_HTML, create_parent="div"
                )
                bg_rows = list(frag)
                # Намери row-а с country_code select-а и вмъкни BG
                # полетата СЛЕД него, ПРЕДИ Demo Data row-а. addnext()
                # слага immediate next sibling → за да запазим реда на
                # двете BG полета iterate-ваме в обратен ред.
                country_rows = form.xpath(
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
                        form.append(child)
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

    @http.route("/web/database/selector", type="http", auth="none")
    def selector(self, **kw):
        # Odoo 19 separate controller — рендерира List + Create form-и
        # когато има налични DB-та (при липсващи /web/database/manager е
        # default route). Същата HTML структура: 2 форми за
        # /web/database/create; inject-а минава през _l10n_bg_inject_fields.
        response = super().selector(**kw)
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
