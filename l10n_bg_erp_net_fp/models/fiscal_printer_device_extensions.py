"""
Extra fields on fiscal.printer.device — added when the device is
served by an `Odoo.ErpNet.FP` Python proxy (which supports multiple
fiscal-printer protocol drivers + auxiliary peripherals beyond what
the upstream C# ErpNet.FP exposes).

This file ONLY ADDS fields and methods — it does not modify any
existing field, signature, or behaviour. Existing deployments that
ignore the new fields keep working exactly as before.
"""

import base64
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


# Per-call timeouts (seconds) for legacy push action_buttons. Datecs
# ISL drives the ceiling — bulk PLU sync and logo programming reach
# 60-90s end-to-end. The device default of 30s is too short for these
# flows. Constants are duplicated from fiscal_printer_device_external.py
# to avoid circular imports between the two extension modules.
PUSH_TIMEOUT_PLU_SYNC = 90
PUSH_TIMEOUT_LOGO = 60
PUSH_TIMEOUT_STAMP = 60
PUSH_TIMEOUT_TEMPLATE = 30


# Driver names mirror Odoo.ErpNet.FP server registry — adding a new
# vendor here means the proxy must understand the same key.
DRIVER_TYPES = [
    ("auto", "Auto-detect (legacy / ErpNet.FP)"),
    ("datecs.pm", "Datecs PM v2.11.4 (FP-700 MX series)"),
    ("datecs.isl", "Datecs ISL (DP-25 / DP-150X / FP-700X / FP-2000)"),
    ("daisy.isl", "Daisy ISL"),
    ("eltrade.isl", "Eltrade ISL"),
    ("incotex.isl", "Incotex ICP"),
    ("tremol.isl", "Tremol ISL"),
]


# Failure policy when device sync fails during pos.session opening.
ON_SYNC_FAIL = [
    ("block", "Block POS opening"),
    ("warning", "Warn but continue"),
    ("silent", "Silent — log only"),
]


class FiscalPrinterDevice(models.Model):
    _inherit = "fiscal.printer.device"

    # ─── Driver / vendor selection ─────────────────────────────────
    # `auto` keeps the original ErpNet.FP behaviour (driver inferred
    # by the server from its config). When set to a specific value,
    # admins document which protocol the device speaks — useful both
    # as a UI hint and for future proxy-side validation.
    driver_type = fields.Selection(
        DRIVER_TYPES,
        string="Driver / Protocol",
        default="auto",
        help="Which fiscal-printer protocol the device speaks. Leave on "
        "'Auto-detect' for backward compatibility with ErpNet.FP — the "
        "Python proxy infers the driver from its `config.yaml`.",
    )

    # ─── Unique-Sale-Number prefix ─────────────────────────────────
    # NSale (UNS) is the government-required unique sale identifier
    # in the form `LLDDDDDD-CCCC-DDDDDDD`. The first 2 letters are a
    # device prefix; defaulting it per device makes UNSes from
    # multiple devices in the same shop never collide.
    nsale_prefix = fields.Char(
        string="UNS prefix (2 letters)",
        size=2,
        help="2-letter prefix for Unique Sale Numbers "
        "(LLDDDDDD-CCCC-DDDDDDD). Per-device, ensures uniqueness "
        "across multiple devices in the same shop. Required for "
        "Datecs PM v2.11.4 syntax #2.",
    )

    # ─── Failure policy on POS-open sync ───────────────────────────
    on_sync_fail = fields.Selection(
        ON_SYNC_FAIL,
        string="On sync failure",
        default="block",
        help="What happens when the device fails health-check during "
        "POS session opening: block opening, warn but continue, or "
        "silently log. `block` is the production default for "
        "fiscal compliance.",
    )

    # ─── Receipt template (admin-managed via separate buttons) ─────
    # The proxy syncs these to the device on demand via a vendor-
    # specific endpoint. They live on the device record so they stay
    # tied to the physical hardware, not to the POS config.
    logo_image = fields.Image(
        string="Customer Logo",
        max_width=384,
        max_height=384,
        help="Top-of-receipt graphic. Pushed to the device by 'Upload "
        "logo' button. Capability marker [*32] required (most modern "
        "Datecs PM models support this).",
    )
    stamp_image = fields.Image(
        string="Stamp Image",
        max_width=384,
        max_height=384,
        help="Bottom-of-receipt seal. Same constraints as Customer Logo.",
    )
    header_lines = fields.Text(
        string="Receipt Header (10 lines)",
        help="Up to 10 lines of header text printed at the top of every "
        "fiscal receipt. Each line up to 32-64 chars depending on "
        "device print-column count.",
    )
    footer_lines = fields.Text(
        string="Receipt Footer (10 lines)",
        help="Up to 10 lines of footer text printed at the bottom.",
    )

    # ─── PLU sync bookkeeping ──────────────────────────────────────
    last_plu_sync = fields.Datetime(string="Last PLU sync", readonly=True)
    plu_capacity = fields.Integer(
        string="PLU capacity",
        default=4000,
        help="Maximum number of PLUs the device can hold. "
        "Defaults: Datecs ISL (DP-150X / FP-700X) = 10000, "
        "Datecs PM compact = 4000, others = 4000. "
        "Override here if your device firmware exposes a different "
        "limit. The pre-push guard refuses to send more PLUs than "
        "this number.",
    )
    plu_programmed = fields.Integer(
        string="PLU programmed",
        readonly=True,
        help="Number of PLUs currently stored on the device.",
    )

    # ─── НАП-compliant УНП брояч (Наредба Н-18, Прил. 29) ─────────
    # УНП формат: <ИН на ФУ 8 chars>-<оператор 4 chars>-<пореден 7 цифри>
    # Пример: DT737851-0001-0000001
    # `l10n_bg_uns_next_number` нараства с 1 при всяка продажба, **per
    # устройство** (не се нулира между сесии — НАП изискване за уникалност
    # и непрекъснатост в живота на ФУ).
    l10n_bg_device_serial = fields.Char(
        string="Device serial (ИН на ФУ)",
        readonly=True,
        copy=False,
        help="Real fiscal device individual number (ИН на ФУ — 2 letters + "
        "6 digits, assigned by NRA). Auto-populated from the proxy's "
        "/printers/<id> endpoint on the first UNS allocation. Used as the "
        "first part of the УНП per Наредба Н-18.",
    )
    l10n_bg_uns_next_number = fields.Integer(
        string="UNS counter (next)",
        default=1,
        copy=False,
        help="Next sale sequential number to be allocated. Increments +1 "
        "per sale, never resets (per НАП Прил. 29). Reset ONLY on device "
        "replacement.",
    )

    @api.model
    def l10n_bg_allocate_uns(self, printer_name, operator_code=None, device_serial=None):
        """Allocate next УНП for the named fiscal device.

        Atomically increments the counter and returns the full УНП string:
            <device_serial>-<operator 4 digits>-<counter 7 digits>

        Args:
            printer_name: device key from config.yaml (e.g., 'dp150').
            operator_code: cashier code (digits) — padded to 4 chars.
            device_serial: ИН на ФУ от проксито (JS-side fetch). Server-side
                fetch не сработва при browser-proxy topology (Odoo сървърът
                не може да достигне локалното прокси на касиера).

        Returns:
            * full УНП string on success (e.g., 'DT737851-0001-0000123')
            * None if device not found or serial cannot be obtained (JS
              falls back to local heuristic in that case).
        """
        if not printer_name:
            return None
        dev = self.search([("name", "=", printer_name)], limit=1)
        if not dev:
            _logger.warning("l10n_bg_allocate_uns: device %r not found", printer_name)
            return None

        # 1) Записваме serial-а ако е подаден (от JS) и още го нямаме записан
        if device_serial and not dev.l10n_bg_device_serial:
            dev.sudo().write({"l10n_bg_device_serial": device_serial.strip()[:32]})
            _logger.info("device serial cached от JS: %s = %s",
                         printer_name, device_serial.strip())
        # 2) Lazy server-side fetch (работи само ако сървърът достига проксито —
        # rare за browser-proxy topology, но опит)
        if not dev.l10n_bg_device_serial:
            try:
                dev._l10n_bg_refresh_device_serial()
            except Exception:  # noqa: BLE001
                _logger.exception("УНП allocate: serial refresh failed for %s", printer_name)
        if not dev.l10n_bg_device_serial:
            _logger.warning(
                "l10n_bg_allocate_uns: no device serial for %r, returning None "
                "(JS will fall back to local heuristic)", printer_name,
            )
            return None

        # 2) atomic increment + fetch (PostgreSQL UPDATE...RETURNING)
        self.env.cr.execute(
            """
            UPDATE fiscal_printer_device
            SET l10n_bg_uns_next_number = l10n_bg_uns_next_number + 1
            WHERE id = %s
            RETURNING l10n_bg_uns_next_number - 1
            """,
            (dev.id,),
        )
        counter = self.env.cr.fetchone()[0]

        # 3) форматираме УНП-то (op padded to 4 chars, counter to 7 digits)
        op = str(operator_code or "1").zfill(4)[-4:]
        uns = f"{dev.l10n_bg_device_serial}-{op}-{counter:07d}"
        _logger.info(
            "УНП allocate: %s op=%s counter=%d → %s",
            printer_name, op, counter, uns,
        )
        return uns

    def _l10n_bg_refresh_device_serial(self):
        """Lazy GET /printers/<name> на проксито и попълва l10n_bg_device_serial.
        Викан само вътрешно от l10n_bg_allocate_uns; не е public RPC."""
        self.ensure_one()
        if not self.host:
            return
        import requests  # local import — модулът се товари лениво
        url = self.host.rstrip("/") + "/printers/" + self.name
        try:
            r = requests.get(url, timeout=5)
            r.raise_for_status()
            data = r.json()
            serial = (data.get("serialNumber") or "").strip()
            if serial:
                self.sudo().write({"l10n_bg_device_serial": serial})
                _logger.info("device serial синхрониран от проксито: %s = %s",
                             self.name, serial)
        except Exception as exc:  # noqa: BLE001
            _logger.warning("Не успях да взема serial от %s: %s", url, exc)

    # ─── Convenience: helpers exposed to the JS layer ──────────────

    def _is_proxy_capable(self):
        """True if the device is served by Odoo.ErpNet.FP Python proxy
        (which supports multi-driver / pinpads / scales / readers).
        """
        return self.driver_type and self.driver_type != "auto"

    # ─── Soft-fail-aware action wrappers ───────────────────────────

    def action_apply_sync_failure(self, exc):
        """Route a sync exception through `on_sync_fail` policy."""
        self.ensure_one()
        msg = str(exc)[:240]
        if self.on_sync_fail == "block":
            raise UserError(
                _("Fiscal device '%(name)s' sync failed: %(msg)s") % {
                    "name": self.name, "msg": msg,
                }
            )
        # Both 'warning' and 'silent' just log + post a chatter note
        self.message_post(
            body=_("Sync failed: %(msg)s — policy: %(p)s") % {
                "msg": msg, "p": self.on_sync_fail,
            },
            message_type="notification",
        )

    # ─── Phase 2: explicit "push to proxy" buttons ─────────────────
    # All four buttons reuse the existing `_make_request()` HTTP
    # helper (see erp_net_fp.py:209). They never modify legacy
    # endpoints — they only call NEW endpoints exposed by the
    # Python proxy (Odoo.ErpNet.FP), which are no-ops on the
    # original C# ErpNet.FP server (returns 404 → caught and
    # routed through `on_sync_fail`).

    def _proxy_post(self, suffix, payload=None, log_endpoint=None,
                    timeout=None):
        """Wrapper around _make_request that records the call to the
        append-only frame log and applies on_sync_fail on errors.

        `timeout` (optional, seconds) — per-call override; PLU sync /
        VAT push / logo push need 60-90s on Datecs ISL devices.
        """
        self.ensure_one()
        endpoint = "printers/%s/%s" % (self.printer_id, suffix)
        log_ep = log_endpoint or endpoint
        try:
            result = self._make_request(
                "POST", endpoint, data=payload or {}, timeout=timeout)
        except Exception as exc:
            # `summary` is computed (store=True) — Odoo recomputes on
            # create. `error_code` is Integer (numeric device codes only);
            # free-text exceptions belong in error_message.
            self.env["fiscal.frame.log"].sudo().create({
                "device_id": self.id,
                "direction": "out",
                "endpoint": log_ep,
                "state": "failed",
                "error_message": str(exc),
                "payload": str(payload)[:2000] if payload else False,
            })
            self.action_apply_sync_failure(exc)
            return None
        self.env["fiscal.frame.log"].sudo().create({
            "device_id": self.id,
            "direction": "out",
            "endpoint": log_ep,
            "state": "ok",
            "payload": str(payload)[:2000] if payload else False,
        })
        return result

    def _l10n_bg_call_zreport_totals(self):
        """Invoke the proxy's `/printers/<id>/zreport-totals` endpoint
        which prints Z and parses out per-group totals when the driver
        cooperates. Returns the raw response dict on success, or a
        synthesized error dict on transport failure.

        Shape (success):
            {ok, report_number, totals_by_group: {group: turnover},
             device_returned_totals: bool, messages: []}
        """
        self.ensure_one()
        return self._proxy_post(
            "zreport-totals",
            timeout=PUSH_TIMEOUT_PLU_SYNC,
        ) or {
            "ok": False,
            "report_number": None,
            "totals_by_group": {},
            "device_returned_totals": False,
            "messages": ["proxy did not return a response"],
        }

    def action_open_plu_push_wizard(self):
        """Open the PLU push wizard pre-targeted to this device.
        Replaces the older `action_sync_plu` legacy fan-out — wizard
        offers preview, scope selection, and explicit per-device opt-in.
        """
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Push PLUs to %s") % self.name,
            "res_model": "l10n.bg.fiscal.plu.push.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_company_id": self.env.company.id,
                "default_device_ids": [(6, 0, [self.id])],
                "default_scope": "pending",
            },
        }

    def action_sync_plu(self):
        """Push all POS-enabled products with l10n_bg_fiscal_plu_number
        to the device. Updates last_plu_sync + plu_programmed.
        """
        self.ensure_one()
        Product = self.env["product.product"]
        products = Product.search([
            ("available_in_pos", "=", True),
            ("l10n_bg_fiscal_plu_number", "!=", False),
        ])
        plus = []
        for p in products:
            plus.append({
                "plu": p.l10n_bg_fiscal_plu_number,
                "name": (p.display_name or "")[:34],
                "price": p.list_price,
                "vat_group": p.l10n_bg_fiscal_vat_group or "B",
                "unit": p.l10n_bg_fiscal_measurement_unit or "pcs",
                "barcode": p.barcode or "",
            })
        result = self._proxy_post(
            "plu/sync", {"items": plus},
            timeout=PUSH_TIMEOUT_PLU_SYNC,
        )
        if result is not None:
            self.write({
                "last_plu_sync": fields.Datetime.now(),
                "plu_programmed": len(plus),
            })
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_upload_logo(self):
        self.ensure_one()
        if not self.logo_image:
            raise UserError(_("No logo uploaded — set Customer Logo first."))
        self._proxy_post("logo", {
            "image_b64": (self.logo_image or b"").decode("ascii")
            if isinstance(self.logo_image, bytes)
            else self.logo_image,
        }, log_endpoint="printers/.../logo",
           timeout=PUSH_TIMEOUT_LOGO)
        return True

    def action_upload_stamp(self):
        self.ensure_one()
        if not self.stamp_image:
            raise UserError(_("No stamp uploaded — set Stamp Image first."))
        self._proxy_post("stamp", {
            "image_b64": (self.stamp_image or b"").decode("ascii")
            if isinstance(self.stamp_image, bytes)
            else self.stamp_image,
        }, log_endpoint="printers/.../stamp",
           timeout=PUSH_TIMEOUT_STAMP)
        return True

    def action_sync_header_footer(self):
        self.ensure_one()
        header = (self.header_lines or "").splitlines()[:10]
        footer = (self.footer_lines or "").splitlines()[:10]
        self._proxy_post("template", {
            "header": header,
            "footer": footer,
        }, log_endpoint="printers/.../template",
           timeout=PUSH_TIMEOUT_TEMPLATE)
        return True

    # ─── Discovery: list printers from the proxy ───────────────────
    # `list_proxy_printers` е дефиниран в l10n_bg_erp_net_base (транспортен
    # слой) и се наследява през MRO — не се дублира тук (19.0.16.0.0).

    # ─── Phase 3: pinpad charge (called by POS frontend via RPC) ───
    @api.model
    def charge_pinpad(self, device_id, amount, currency="BGN", pinpad_id=None,
                      reference=None):
        """RPC entry-point — POS calls this when a payment line uses a
        pinpad-marked method. Delegates to the proxy /pinpads/{id}/charge.

        Returns dict {ok, transaction_id, message} for the JS layer to
        display. Never raises (keeps POS responsive); on failure returns
        {ok: False, message: <reason>}.
        """
        device = self.browse(device_id).exists()
        if not device:
            return {"ok": False, "message": _("Fiscal device not found.")}
        if not device._is_proxy_capable():
            return {"ok": False,
                    "message": _("Device is in legacy ErpNet.FP mode — "
                                 "no pinpad support.")}
        endpoint = "pinpads/%s/charge" % (pinpad_id or "default")
        payload = {
            "amount": float(amount),
            "currency": currency or "BGN",
            "reference": reference or "",
        }
        try:
            result = device._make_request("POST", endpoint, data=payload)
        except Exception as exc:
            # `error_code` е Integer (само числови кодове от устройството);
            # free-text грешката отива в `error_message`, иначе create()
            # гърми с ValueError и нарушаваме "Never raises".
            # `summary` е computed (store=True) — не се подава при create.
            self.env["fiscal.frame.log"].sudo().create({
                "device_id": device.id,
                "direction": "out",
                "endpoint": endpoint,
                "state": "failed",
                "error_message": str(exc),
                "payload": str(payload)[:2000],
            })
            return {"ok": False, "message": str(exc)[:240]}
        self.env["fiscal.frame.log"].sudo().create({
            "device_id": device.id,
            "direction": "out",
            "endpoint": endpoint,
            "payload": str(payload)[:2000],
        })
        return {
            "ok": True,
            "transaction_id": (result or {}).get("transaction_id", ""),
            "message": (result or {}).get("message", ""),
            "raw": result,
        }

    # ─── Bridge to native iot.box ─────────────────────────────────
    # Moved to `l10n_bg_erp_net_fp_iot` bridge module (in
    # l10n-bulgaria-ee, auto_install=True) in 18.0.10.1.0 so this
    # core file no longer references the EE-only `iot.box` /
    # `iot.device` models — keeping the core CE-installable.
