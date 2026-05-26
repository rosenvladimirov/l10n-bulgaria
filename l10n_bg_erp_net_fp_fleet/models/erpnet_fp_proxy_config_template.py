# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Config template — raw YAML fragment ready to push to a proxy.

Конфигурацията на проксито основно живее в самото прокси
(`config.yaml` + `config.d/<kind>.yaml` фрагменти). Odoo пази:

  * **Реално** хардуерно знание — нула. Прокси знае всичките детайли
    (Hikvision vs Dahua vs ONVIF, Polimex bus layout, ALPR endpoint).
  * **YAML текст** — този модел: едно поле `yaml_text` с пълното
    съдържание на бъдещия `config.d/<kind>.yaml` файл.
  * **Абстрактен индекс** — `kind` (cameras/access/mqtt/biometric/…)
    + `name` за човешка четивност + `proxy_id` за owner-а.

Plugin модулите (планирани) добавят convenience UI над този модел —
напр. `l10n_bg_erp_net_fp_plugin_camera_hikvision` ще покаже structured
fields (IP, ONVIF user/pwd) и при save ще регенерира `yaml_text`.

Push flow:
  template.action_push_to_proxy() → enqueue `push_config` команда
  с payload `{kind, section: yaml.safe_load(yaml_text)}`. Прокси-то
  атомично записва `config.d/<kind>.yaml` + hot-reload-ва само
  засегнатия registry. Тук Odoo НЕ парсва YAML-а — просто го изпраща;
  validation се случва на прокси страна.
"""
from __future__ import annotations

import hashlib
import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


# AC-only kinds — fiscal sections (printers/pinpads/scales/displays/
# readers) са под manual control на customer-IT и не се rewrite-ват
# от Odoo. Whitelist-ът съвпада с proxy-side PUSH_CONFIG_AC_KINDS.
_KIND_SELECTION = [
    ("mqtt", "MQTT"),
    ("cameras", "Cameras"),
    ("access", "Access"),
    ("biometric", "Biometric"),
]


class ErpNetFpProxyConfigTemplate(models.Model):
    _name = "erpnet.fp.proxy.config.template"
    _description = "ErpNet.FP Proxy Config Template (raw YAML fragment)"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "proxy_id, kind, sequence, name"
    _rec_name = "display_name"

    proxy_id = fields.Many2one(
        "erpnet.fp.proxy", required=True, ondelete="cascade",
        index=True, tracking=True,
        help="Proxy this fragment belongs to. One template = one proxy = "
             "one kind (cameras/access/mqtt/biometric).",
    )
    name = fields.Char(
        required=True, tracking=True,
        help="Human label, e.g. 'parking-cameras' or 'main-broker'. "
             "Within (proxy, kind) the name should be unique.",
    )
    kind = fields.Selection(
        _KIND_SELECTION, required=True, tracking=True, default="mqtt",
        help="Which AC fragment file this template owns on the proxy. "
             "The push action writes <proxy>/config.d/<kind>.yaml.",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True, tracking=True)

    yaml_text = fields.Text(
        string="YAML",
        required=True,
        default="# Raw YAML for this config.d/<kind>.yaml fragment.\n"
                "# Example for kind=mqtt:\n"
                "#\n"
                "# mqtt:\n"
                "#   - name: parking\n"
                "#     host: mqtt-broker.local\n"
                "#     enabled: true\n"
                "#     topics: [lpr, lpr/+]\n",
        help="Raw YAML content. Sent verbatim to the proxy on push; "
             "Odoo does not parse it — validation is proxy-side. "
             "The top-level key MUST match `kind` (e.g. for kind=mqtt "
             "the YAML should declare `mqtt:`).",
    )

    notes = fields.Html()

    # ─── Sync state ─────────────────────────────────────────────

    last_pushed_at = fields.Datetime(readonly=True, tracking=True)
    last_pushed_version = fields.Char(
        readonly=True,
        help="SHA-256 hex of the YAML text last pushed. Compared with "
             "the proxy's runtime_*_version (from heartbeat) to detect "
             "drift.",
    )
    # Stamp the wall-clock the yaml_text was last meaningfully changed.
    # We can't depend on write_date for drift detection because every
    # `action_push_to_proxy` calls self.write(last_pushed_at=...), which
    # touches write_date and would mark the record out_of_sync immediately
    # after a push. Touching `yaml_text_changed_at` only happens when
    # yaml_text actually changes (see _onchange / create / write override
    # below) — that's the meaningful clock for "did the operator alter
    # the payload since the last push".
    yaml_text_changed_at = fields.Datetime(
        readonly=True,
        help="Wall-clock of the last meaningful yaml_text change. "
             "Used by sync_status — not write_date — so post-push "
             "metadata writes don't trigger false drift.",
    )
    sync_status = fields.Selection([
        ("never",       "Never pushed"),
        ("in_sync",     "In sync"),
        ("out_of_sync", "Out of sync — record changed since last push"),
    ], compute="_compute_sync_status", store=True,
        # Stored so search filters + group_by + kanban progressbar
        # all work without a custom search method.
    )

    display_name = fields.Char(compute="_compute_display_name")

    _name_proxy_kind_uniq = models.Constraint(
        "UNIQUE(proxy_id, kind, name)",
        "Another template on this proxy already has that name + kind.",
    )

    @api.depends("name", "kind")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = (
                f"{rec.kind or '?'} · {rec.name or ''}".strip(" ·"))

    @api.depends("last_pushed_at", "yaml_text_changed_at")
    def _compute_sync_status(self):
        for rec in self:
            if not rec.last_pushed_at:
                rec.sync_status = "never"
            elif (rec.yaml_text_changed_at
                  and rec.yaml_text_changed_at > rec.last_pushed_at):
                rec.sync_status = "out_of_sync"
            else:
                rec.sync_status = "in_sync"

    @api.model_create_multi
    def create(self, vals_list):
        # New record with explicit yaml_text → stamp the change clock so
        # sync_status reads `never` correctly (never pushed yet) and
        # flips to `out_of_sync` immediately after the first push if the
        # operator edits before pushing.
        for vals in vals_list:
            if "yaml_text" in vals and "yaml_text_changed_at" not in vals:
                vals["yaml_text_changed_at"] = fields.Datetime.now()
        return super().create(vals_list)

    def write(self, vals):
        # Only the meaningful payload key bumps the change clock.
        # `last_pushed_at` / `last_pushed_version` writes from the
        # push action do NOT touch it, so post-push state stays in_sync.
        if "yaml_text" in vals and "yaml_text_changed_at" not in vals:
            vals = dict(vals)
            vals["yaml_text_changed_at"] = fields.Datetime.now()
        return super().write(vals)

    # ─── Push action ────────────────────────────────────────────

    def _yaml_to_section(self) -> object:
        """Best-effort parse: return the dict/list under the top-level
        kind key. Raises UserError if YAML is malformed or doesn't
        declare the expected top-level key.
        """
        self.ensure_one()
        try:
            import yaml as _yaml
        except ImportError as e:  # noqa: BLE001
            raise UserError(_(
                "PyYAML is required to push templates. "
                "Install python3-yaml on the Odoo host.")) from e
        try:
            data = _yaml.safe_load(self.yaml_text or "") or {}
        except _yaml.YAMLError as e:
            raise UserError(_("Invalid YAML: %s", e)) from e
        if not isinstance(data, dict):
            raise UserError(_(
                "Top level of yaml_text must be a dict — got %s.",
                type(data).__name__))
        if self.kind not in data:
            raise UserError(_(
                "YAML doesn't declare the expected top-level key "
                "%(k)r — got %(keys)s.",
                k=self.kind, keys=sorted(data.keys())))
        return data[self.kind]

    def action_push_to_proxy(self):
        """Enqueue a push_config command with this template's yaml content."""
        self.ensure_one()
        if not self.proxy_id:
            raise UserError(_("Template has no proxy assigned."))
        if self.proxy_id.state != "active":
            raise UserError(_(
                "Proxy %s is not active (state=%s) — cannot push.",
                self.proxy_id.name, self.proxy_id.state))
        section = self._yaml_to_section()
        # SHA-256 of the canonical JSON payload — portable version key
        # the proxy can echo back as runtime_<kind>_version. We hash the
        # JSON form (not raw yaml text) so whitespace tweaks don't churn
        # the version.
        canon = json.dumps(section, sort_keys=True,
                           separators=(",", ":")).encode("utf-8")
        version = "sha256:" + hashlib.sha256(canon).hexdigest()

        self.proxy_id._enqueue_command(
            "push_config", {"kind": self.kind, "section": section})

        self.write({
            "last_pushed_at": fields.Datetime.now(),
            "last_pushed_version": version,
        })
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Queued"),
                "message": _(
                    "%(k)s template queued on proxy %(p)s — applied on "
                    "next heartbeat.",
                    k=self.kind, p=self.proxy_id.name),
                "type": "success",
                "sticky": False,
            },
        }
