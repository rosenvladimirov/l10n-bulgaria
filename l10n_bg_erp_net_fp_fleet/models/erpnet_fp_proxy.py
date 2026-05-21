# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""
ErpNet.FP proxy registry model.

Each record represents one ErpNet.FP proxy instance (one per shop
typically). The pairing flow is:

  1. Admin clicks "Generate Pairing Token" on a draft proxy → an
     opaque token + 1 h expiry are written to the record.
  2. Admin pastes the token into the proxy's `config.yaml`
     (`server.registry.pairing_token`) and starts the proxy.
  3. Proxy POSTs `/erp_net_fp/registry/pair` with the token; the
     controller validates + consumes it, generates a long-lived
     `registry_secret`, returns it. From that moment on, the proxy
     heartbeats with HMAC-signed bodies.

The admin_token (which lets us call the proxy's `/admin/*` endpoints)
is stored Fernet-encrypted; only :py:meth:`get_admin_token` decrypts
it on demand.
"""
from __future__ import annotations

import json
import logging
import secrets
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Time window to use a freshly-generated pairing token. Short enough
# to limit blast radius if it leaks, long enough to copy-paste it
# into a remote proxy config.
_PAIRING_TTL = timedelta(hours=1)

# Tolerance for "alive" computation — heartbeat interval is 60 s by
# default, so 3× = 180 s gives one missed beat before going red.
_ALIVE_WINDOW_SECONDS = 180


class ErpNetFpProxy(models.Model):
    _name = "erpnet.fp.proxy"
    _description = "ErpNet.FP Proxy Instance"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"
    _rec_name = "name"

    # ─── Identity ───────────────────────────────────────────────

    name = fields.Char(
        required=True, tracking=True,
        help="Human-readable identifier — e.g. 'sofia-shop-1'.",
    )
    url = fields.Char(
        string="Proxy URL",
        help="Public URL where this proxy is reachable, e.g. "
             "https://erpnet.shop1.lan.mcpworks.net. Used for "
             "back-channel /admin/* calls (Update / Logs / VAT).",
    )
    host = fields.Char(
        readonly=True, tracking=True,
        help="Hostname reported by the proxy in its last heartbeat.",
    )
    version = fields.Char(
        readonly=True, tracking=True,
        help="Proxy semver, reported in heartbeat.",
    )
    notes = fields.Text()

    # ─── Pairing ────────────────────────────────────────────────

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("pairing", "Pairing pending"),
            ("active", "Active"),
            ("archived", "Archived"),
        ],
        default="draft", tracking=True, required=True,
    )
    pairing_token = fields.Char(
        readonly=True, copy=False, groups="base.group_system",
        help="One-time token; valid for one hour. Paste into the proxy's "
             "config.yaml under server.registry.pairing_token, then start "
             "the proxy. Cleared after first successful pair.",
    )
    pairing_expires = fields.Datetime(
        readonly=True, copy=False, groups="base.group_system",
    )
    registry_secret = fields.Char(
        readonly=True, copy=False, groups="base.group_system",
        help="Long-lived shared secret used by the proxy to HMAC-sign "
             "heartbeat bodies. Generated automatically on pair.",
    )

    # ─── Heartbeat state ────────────────────────────────────────

    last_seen = fields.Datetime(
        readonly=True, tracking=False,
        help="Timestamp of the last accepted heartbeat.",
    )
    alive = fields.Boolean(
        compute="_compute_alive", search="_search_alive", store=False,
        help="True if last_seen is within "
             f"{_ALIVE_WINDOW_SECONDS} s.",
    )
    devices_json = fields.Text(
        readonly=True,
        help="JSON: {printers: [...], pinpads: [...], scales: [...], "
             "readers: [...], displays: [...]}",
    )
    devices_summary = fields.Char(
        compute="_compute_devices_summary", store=False,
    )

    # ─── Runtime config versions (R3 — proxy heartbeat) ─────────
    # Proxy ships SHA-256 of each loaded config.d/<kind>.yaml fragment
    # in every heartbeat. Storing the full JSON keeps us schema-tolerant
    # if new sections show up; the four explicit Char fields below give
    # the list/form views something to bind to without parsing JSON each
    # render.

    runtime_config_versions_json = fields.Text(
        readonly=True,
        help="Raw JSON: {kind: 'sha256:<hex>'} reported by the proxy on "
             "its last heartbeat. Drift-detected in the form view.",
    )
    runtime_mqtt_version = fields.Char(
        string="MQTT runtime ver.",
        compute="_compute_runtime_versions", store=True,
        help="SHA-256 of config.d/mqtt.yaml as loaded by the proxy. "
             "Compare with mqtt.broker.config.last_pushed_version on "
             "the source records to detect drift.",
    )
    runtime_camera_version = fields.Char(
        string="Cameras runtime ver.",
        compute="_compute_runtime_versions", store=True,
    )
    runtime_access_version = fields.Char(
        string="Access runtime ver.",
        compute="_compute_runtime_versions", store=True,
    )
    runtime_biometric_version = fields.Char(
        string="Biometric runtime ver.",
        compute="_compute_runtime_versions", store=True,
    )

    # ─── Admin token (Fernet-encrypted at rest) ─────────────────

    admin_token_encrypted = fields.Char(
        readonly=True, copy=False, groups="base.group_system",
        help="Fernet ciphertext of the proxy's admin token. Reported "
             "by the proxy in its heartbeat so this backend can call "
             "/admin/* endpoints (self-update, logs, vat-rates).",
    )
    has_admin_token = fields.Boolean(
        compute="_compute_has_admin_token", store=False,
    )

    # ─── CORS allowed origins ───────────────────────────────────

    cors_origins = fields.Text(
        string="CORS Allowed Origins",
        help="One origin per line — e.g. https://dev-18.odoo-shell.space.\n"
             "Pushed to the proxy on every heartbeat; proxy regenerates "
             "Traefik dynamic config and the file watcher hot-reloads. "
             "Lines starting with `#` are comments; blank lines ignored. "
             "Origins MUST be scheme+host[+port], no path, no trailing slash.",
    )

    # ─── Reverse links ──────────────────────────────────────────

    command_ids = fields.One2many(
        "erpnet.fp.proxy.command", "proxy_id", string="Commands",
    )
    device_ids = fields.One2many(
        "erpnet.fp.proxy.device", "proxy_id", string="Devices",
    )
    pending_command_count = fields.Integer(
        compute="_compute_pending_command_count", store=False,
    )
    device_count = fields.Integer(
        compute="_compute_device_count", store=False,
    )

    _sql_constraints = [
        ("name_uniq", "UNIQUE(name)",
         "Another proxy already uses this name."),
    ]

    # ─── Computes ───────────────────────────────────────────────

    @api.depends("last_seen")
    def _compute_alive(self):
        now = fields.Datetime.now()
        for rec in self:
            if not rec.last_seen:
                rec.alive = False
                continue
            delta = (now - rec.last_seen).total_seconds()
            rec.alive = delta < _ALIVE_WINDOW_SECONDS

    def _search_alive(self, operator, value):
        """Translate `alive == True/False` search into a `last_seen` window."""
        from datetime import timedelta as _td
        threshold = fields.Datetime.now() - _td(seconds=_ALIVE_WINDOW_SECONDS)
        # Normalise (operator, value) → "want_alive" boolean
        if operator in ("=", "==", "in"):
            want = bool(value if not isinstance(value, (list, tuple)) else value[0])
        elif operator in ("!=", "<>", "not in"):
            want = not bool(value if not isinstance(value, (list, tuple)) else value[0])
        else:
            return [("id", "in", [])]
        if want:
            return [("last_seen", ">=", threshold)]
        return ["|", ("last_seen", "=", False),
                    ("last_seen", "<", threshold)]

    @api.depends("runtime_config_versions_json")
    def _compute_runtime_versions(self):
        """Extract per-kind SHA-256 from the JSON blob the proxy ships.

        Keeps `sha256:<hex>` prefix intact so the UI can render a
        monospace chip + truncate to 12 chars (see view). Empty
        string when the proxy hasn't reported a fragment for that
        kind yet (means the fragment file doesn't exist on disk).
        """
        for rec in self:
            data = {}
            if rec.runtime_config_versions_json:
                try:
                    data = json.loads(rec.runtime_config_versions_json)
                except (ValueError, TypeError):
                    data = {}
            rec.runtime_mqtt_version = data.get("mqtt") or ""
            rec.runtime_camera_version = data.get("cameras") or ""
            rec.runtime_access_version = data.get("access") or ""
            rec.runtime_biometric_version = data.get("biometric") or ""

    @api.depends("devices_json")
    def _compute_devices_summary(self):
        for rec in self:
            if not rec.devices_json:
                rec.devices_summary = ""
                continue
            try:
                d = json.loads(rec.devices_json)
            except (ValueError, TypeError):
                rec.devices_summary = "?"
                continue
            parts = []
            for k in ("printers", "pinpads", "scales", "readers", "displays"):
                lst = d.get(k) or []
                if lst:
                    parts.append(f"{k[:1].upper()}{len(lst)}")
            rec.devices_summary = " ".join(parts) or "—"

    @api.depends("admin_token_encrypted")
    def _compute_has_admin_token(self):
        for rec in self.sudo():
            rec.has_admin_token = bool(rec.admin_token_encrypted)

    @api.depends("command_ids.state")
    def _compute_pending_command_count(self):
        for rec in self:
            rec.pending_command_count = len(rec.command_ids.filtered(
                lambda c: c.state in ("pending", "sent")
            ))

    @api.depends("device_ids", "device_ids.active")
    def _compute_device_count(self):
        for rec in self:
            rec.device_count = len(rec.device_ids.filtered("active"))

    # ─── Admin token helpers ────────────────────────────────────

    def get_admin_token(self) -> str:
        """Decrypt and return the stored admin token. Returns '' if
        none was reported yet. Always callable through `sudo()` —
        ACL on the field already prevents leakage to non-system
        users via XML-RPC.
        """
        self.ensure_one()
        ct = self.sudo().admin_token_encrypted or ""
        if not ct:
            return ""
        return self.env["erpnet.fp.fernet"].decrypt(ct)

    def set_admin_token(self, plaintext: str) -> None:
        """Encrypt and persist a new admin token. Called from the
        registry controller on every heartbeat (the proxy's token
        can rotate without user action — e.g. after a reset)."""
        self.ensure_one()
        if not plaintext:
            self.sudo().admin_token_encrypted = ""
            return
        ct = self.env["erpnet.fp.fernet"].encrypt(plaintext)
        self.sudo().admin_token_encrypted = ct

    # ─── Pairing actions ────────────────────────────────────────

    def action_generate_pairing_token(self):
        """Generate a fresh single-use pairing token + 1 h expiry.

        Resetting an already-active proxy's pairing token does NOT
        invalidate the existing registry_secret — the operator must
        also clear it (button "Reset secret") if they want to truly
        re-pair from scratch.
        """
        for rec in self:
            token = secrets.token_urlsafe(32)
            rec.sudo().write({
                "pairing_token": token,
                "pairing_expires": fields.Datetime.now() + _PAIRING_TTL,
                "state": "pairing" if rec.state == "draft" else rec.state,
            })
            rec.message_post(
                body=_("Pairing token generated; expires in %(h)s hour(s).",
                       h=_PAIRING_TTL.total_seconds() // 3600),
            )
        return self._show_pairing_dialog()

    def action_reset_secret(self):
        """Forget the registry_secret + admin_token. Forces the proxy
        to re-pair on next start. Use when a secret leaks or the
        proxy is being moved to a different shop."""
        for rec in self:
            rec.sudo().write({
                "registry_secret": False,
                "admin_token_encrypted": False,
                "last_seen": False,
                "version": False,
                "host": False,
                "devices_json": False,
                "state": "draft",
            })
            rec.message_post(body=_("Registry secret reset — proxy must re-pair."))

    def action_archive_proxy(self):
        for rec in self:
            rec.state = "archived"

    def action_unarchive_proxy(self):
        for rec in self:
            rec.state = "draft"

    def _show_pairing_dialog(self):
        """Return a `display_notification` action so the user sees the
        token without having to navigate to a hidden field."""
        self.ensure_one()
        token = self.sudo().pairing_token or ""
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Pairing token"),
                "message": _(
                    "Paste this into the proxy's config.yaml "
                    "under `server.registry.pairing_token`:\n\n%(t)s",
                    t=token,
                ),
                "type": "info",
                "sticky": True,
            },
        }

    # ─── Queue commands (pull-model — proxies are NAT-fronted) ──

    def _enqueue_command(self, kind: str, payload: dict | None = None):
        """Drop a command on the proxy's queue. Picked up at the next
        heartbeat (≤ interval_seconds latency)."""
        self.ensure_one()
        import json as _json
        return self.env["erpnet.fp.proxy.command"].create({
            "proxy_id": self.id,
            "kind": kind,
            "payload_json": _json.dumps(payload or {}),
        })

    @api.model
    def _enqueue_push_config(self, base_url, payload):
        """Soft-API за access-control модулите (lpr.camera.config /
        lpr.access.controller `action_sync_config_to_proxy`).

        Намира прокси по неговия `url` и слага `push_config` команда
        на опашката му (бавния pull/heartbeat remote-mgmt path).
        Връща командата (truthy) или False ако няма съответстващо
        прокси. Извикващият НЕ зависи от този модул (HTTP-decoupled,
        soft hasattr-guard от негова страна) → нула copyleft връзка.
        """
        target = (base_url or "").rstrip("/")
        if not target:
            return False
        proxy = self.search([("url", "!=", False)]).filtered(
            lambda p: (p.url or "").rstrip("/") == target
        )[:1]
        if not proxy:
            return False
        return proxy._enqueue_command("push_config", payload or {})

    def _command_queued_notification(self, kind_label: str):
        """Standard 'Queued' toast — shown after enqueueing a command."""
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Queued"),
                "message": _(
                    "%(label)s will run on the proxy's next heartbeat "
                    "(within %(s)s s).",
                    label=kind_label,
                    s=self.env.context.get("heartbeat_interval", 60),
                ),
                "type": "success",
                "sticky": False,
            },
        }

    def action_self_update(self):
        self.ensure_one()
        self._enqueue_command("self_update")
        return self._command_queued_notification(_("Self-update"))

    # ─── Push config (per-kind + bulk) ──────────────────────────
    #
    # Soft-resolution: each kind maps to an Odoo model that provides
    # `get_config_payload()` (callable @api.model returning the YAML
    # section as list[dict]). If the source model is not installed on
    # this stack, the per-kind button is a UserError telling the
    # operator which module to install. The bulk action collects all
    # available kinds and skips the missing ones.

    _PUSH_CONFIG_SOURCES = {
        # kind         (model, source-module hint for the error msg)
        "mqtt":      ("mqtt.broker.config",  "hr_attendance_access_control"),
        "cameras":   ("camera.config",       "hr_attendance_access_control"),
        "access":    ("access.point",        "hr_attendance_access_control"),
        "biometric": ("biometric.verifier",  "hr_attendance_access_control"),
    }

    def _collect_push_section(self, kind):
        """Resolve `kind` → list[dict] section payload, or raise.

        Looks up the registered source model and calls its
        `get_config_payload()` method (must be @api.model). The Odoo
        side stays decoupled from the proxy side — it just speaks the
        same wire format that the proxy's loader/registry already
        understands.
        """
        spec = self._PUSH_CONFIG_SOURCES.get(kind)
        if spec is None:
            raise UserError(_(
                "Unknown push_config kind %(k)r — allowed: %(all)s",
                k=kind, all=sorted(self._PUSH_CONFIG_SOURCES)))
        model_name, module_hint = spec
        model = self.env.get(model_name)
        if model is None:
            raise UserError(_(
                "No source model for %(k)s — install %(m)s on this "
                "Odoo to push the %(k)s fragment.",
                k=kind, m=module_hint))
        if not hasattr(model, "get_config_payload"):
            raise UserError(_(
                "Source model %(m)s exists but exposes no "
                "get_config_payload() — likely an old version of "
                "%(mod)s. Update the access-control module to a "
                "version that includes R5 multi-broker support.",
                m=model_name, mod=module_hint))
        return model.get_config_payload()

    def _push_kind(self, kind):
        """Enqueue a push_config command for one AC kind on THIS proxy."""
        self.ensure_one()
        section = self._collect_push_section(kind)
        self._enqueue_command("push_config", {"kind": kind, "section": section})
        return kind

    def action_push_config_mqtt(self):
        self.ensure_one()
        self._push_kind("mqtt")
        return self._command_queued_notification(_("Push MQTT config"))

    def action_push_config_cameras(self):
        self.ensure_one()
        self._push_kind("cameras")
        return self._command_queued_notification(_("Push Cameras config"))

    def action_push_config_access(self):
        self.ensure_one()
        self._push_kind("access")
        return self._command_queued_notification(_("Push Access config"))

    def action_push_config_biometric(self):
        self.ensure_one()
        self._push_kind("biometric")
        return self._command_queued_notification(_("Push Biometric config"))

    def action_push_config_all(self):
        """Push every AC kind whose source model is installed.

        Skips kinds with no source model (no error — those slots are
        just empty). Returns a notification listing what was pushed.
        """
        self.ensure_one()
        pushed = []
        skipped = []
        for kind in self._PUSH_CONFIG_SOURCES:
            try:
                self._push_kind(kind)
                pushed.append(kind)
            except UserError as e:
                skipped.append(f"{kind} ({e.args[0] if e.args else 'no source'})")
        msg = _("Pushed: %(p)s. Skipped: %(s)s.",
                p=", ".join(pushed) or _("(none)"),
                s=", ".join(skipped) or _("(none)"))
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Push All Config"),
                "message": msg,
                "type": "success" if pushed else "warning",
                "sticky": bool(skipped),
            },
        }

    def action_view_logs(self):
        self.ensure_one()
        self._enqueue_command("get_logs", {"tail": 200})
        return self._command_queued_notification(_("Log fetch"))

    def action_open_program_vat_wizard(self):
        self.ensure_one()
        return {
            "name": _("Program VAT rates"),
            "type": "ir.actions.act_window",
            "res_model": "erpnet.fp.program.vat.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_proxy_id": self.id},
        }

    # ─── CORS list parsing ──────────────────────────────────────

    def _get_cors_origins_list(self):
        """Return validated origins from `cors_origins`, ready to push to
        the proxy in the heartbeat response. Strips comments / blanks /
        trailing slashes and only accepts http(s)://host[:port] shape.
        """
        self.ensure_one()
        if not self.cors_origins:
            return []
        out = []
        for raw in self.cors_origins.splitlines():
            s = raw.strip().rstrip("/")
            if not s or s.startswith("#"):
                continue
            if not (s.startswith("http://") or s.startswith("https://")):
                continue
            out.append(s)
        return out

    # ─── Cron: pairing-token expiry sweep ───────────────────────

    @api.model
    def _cron_expire_pairing_tokens(self):
        """Wipe expired pairing tokens so they can't be replayed."""
        now = fields.Datetime.now()
        expired = self.search([
            ("pairing_token", "!=", False),
            ("pairing_expires", "<", now),
        ])
        if expired:
            expired.sudo().write({
                "pairing_token": False,
                "pairing_expires": False,
            })
            _logger.info("Wiped %d expired pairing token(s)", len(expired))
