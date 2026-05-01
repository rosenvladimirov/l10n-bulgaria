"""
l10n.bg.fp.device — Datecs PM fiscal printer config + thin proxy client.

This addon does NOT speak the binary fiscal protocol directly — that's
handled by the `Odoo.ErpNet.FP` Python service running on the shop
machine (or near the device). The Odoo addon stores configuration and
exposes business-level actions, all of which translate to HTTP calls
into the proxy via the ErpNet.FP-compatible API.

Architecture:
    Browser (POS UI) ──fetch()──▶ proxy_url (shop-local)
    Odoo backend     ──requests─▶ proxy_url (admin actions, X/Z, status)
                                 │
                                 └──serial/TCP──▶ Datecs FP-700 MX
"""

import json
import logging

import requests
from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class L10nBgFpDevice(models.Model):
    _name = "l10n.bg.fp.device"
    _description = "Datecs PM Fiscal Printer Device"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda s: s.env.company
    )

    # ---- Proxy connection ----------------------------------------------
    # The shop-local Odoo.ErpNet.FP service that actually talks to the
    # device. Any PEM-trusted host works (Cloudflare Origin, Let's
    # Encrypt, self-signed via Step-CA, plain HTTP for development).
    proxy_url = fields.Char(
        string="Proxy URL",
        default="http://localhost:8001",
        required=True,
        tracking=True,
        help="Base URL of the Odoo.ErpNet.FP service running on the "
        "shop machine. Browser POS UI also fetches this URL directly.",
    )
    printer_id = fields.Char(
        string="Printer ID on Proxy",
        default="fp1",
        required=True,
        tracking=True,
        help="The printer's id as configured in the proxy's config.yaml "
        "(`printers[].id`). This becomes part of every URL: "
        "`{proxy_url}/printers/{printer_id}/status`, etc.",
    )
    proxy_timeout = fields.Integer(
        default=30,
        help="HTTP timeout in seconds for backend → proxy calls.",
    )
    proxy_verify_ssl = fields.Boolean(
        default=True,
        help="Verify the proxy's TLS certificate. Disable only for "
        "development with self-signed certs.",
    )

    # ---- Operator credentials (passed to proxy on receipt prints) -----
    operator_code = fields.Integer(default=1)
    operator_password = fields.Char(default="0000", groups="base.group_system")
    till_number = fields.Integer(default=1)

    # NSale prefix — first 2 letters of LLDDDDDD-CCCC-DDDDDDD.
    # The proxy / driver picks one if not set; this lets ops override.
    nsale_prefix = fields.Char(
        string="NSale Prefix",
        size=2,
        help="Two-letter prefix for Unique Sale Numbers.",
    )

    # ---- Failure policy applied during pos.session opening ------------
    on_sync_fail = fields.Selection(
        [
            ("block", "Block POS opening"),
            ("warning", "Warn but continue"),
            ("silent", "Silent — log only"),
        ],
        default="block",
        required=True,
        tracking=True,
        string="On sync failure",
    )

    # ---- Auto-Z scheduling --------------------------------------------
    auto_z_report = fields.Boolean(string="Automatic Z report", default=False, tracking=True)
    z_report_hour = fields.Integer(string="Z hour", default=23)
    z_report_minute = fields.Integer(string="Z minute", default=59)
    last_z_report = fields.Datetime(string="Last Z report", readonly=True)
    last_x_report = fields.Datetime(string="Last X report", readonly=True)

    # ---- Last-known state from /status -------------------------------
    last_status_check = fields.Datetime(readonly=True)
    last_status_ok = fields.Boolean(readonly=True)
    last_status_message = fields.Char(readonly=True)
    fiscalized = fields.Boolean(readonly=True)
    serial_number = fields.Char(readonly=True)
    fm_number = fields.Char(readonly=True)

    @api.constrains("z_report_hour", "z_report_minute")
    def _check_z_time(self):
        for rec in self:
            if not 0 <= rec.z_report_hour <= 23:
                raise UserError(_("Z report hour must be 0..23."))
            if not 0 <= rec.z_report_minute <= 59:
                raise UserError(_("Z report minute must be 0..59."))

    # ---- Proxy HTTP helpers -------------------------------------------

    def _proxy_endpoint(self, suffix=""):
        self.ensure_one()
        base = (self.proxy_url or "").rstrip("/")
        return f"{base}/printers/{self.printer_id}{suffix}"

    def _proxy_request(self, method, suffix, *, body=None, params=None):
        """Single point of contact for proxy HTTP calls.

        Returns the parsed JSON body. Raises UserError on transport-
        level failures with a descriptive message; does NOT raise on
        application-level `ok: false` envelopes — the caller decides.
        """
        self.ensure_one()
        url = self._proxy_endpoint(suffix)
        try:
            response = requests.request(
                method,
                url,
                json=body,
                params=params,
                timeout=self.proxy_timeout,
                verify=self.proxy_verify_ssl,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.SSLError as exc:
            raise UserError(
                _("TLS error talking to fiscal proxy %(url)s: %(err)s",
                  url=url, err=str(exc))
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise UserError(
                _("Cannot reach fiscal proxy at %(url)s. Make sure the "
                  "Odoo.ErpNet.FP service is running on the shop machine.",
                  url=url)
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise UserError(
                _("Fiscal proxy at %(url)s timed out after %(s)ds.",
                  url=url, s=self.proxy_timeout)
            ) from exc
        except (requests.exceptions.HTTPError, json.JSONDecodeError) as exc:
            raise UserError(
                _("Fiscal proxy returned an unexpected response: %s",
                  str(exc))
            ) from exc

    # ---- Public actions (all delegate to proxy) -----------------------

    def action_check_status(self):
        """GET /printers/{id}/status — health check."""
        for rec in self:
            try:
                result = rec._proxy_request("GET", "/status")
            except UserError as exc:
                rec.write({
                    "last_status_check": fields.Datetime.now(),
                    "last_status_ok": False,
                    "last_status_message": str(exc)[:240],
                })
                continue
            messages = result.get("messages") or []
            critical = [m for m in messages if m.get("type") == "error"]
            rec.write({
                "last_status_check": fields.Datetime.now(),
                "last_status_ok": bool(result.get("ok")) and not critical,
                "last_status_message": (
                    "; ".join(m.get("text", "") for m in messages) or "OK"
                )[:240],
            })
        return True

    def action_print_x_report(self):
        """POST /printers/{id}/xreport."""
        self.ensure_one()
        result = self._proxy_request("POST", "/xreport")
        if result.get("ok"):
            self.last_x_report = fields.Datetime.now()
            self.message_post(body=_("X report printed via proxy"))
            return self._notify_success(_("X report"), _("X report printed."))
        return self._notify_failure(_("X report"), self._error_text(result))

    def action_print_z_report(self):
        """POST /printers/{id}/zreport."""
        self.ensure_one()
        result = self._proxy_request("POST", "/zreport")
        if result.get("ok"):
            self.last_z_report = fields.Datetime.now()
            self.message_post(body=_("Z report printed via proxy"))
            return self._notify_success(
                _("Z report"), _("Z report printed. Daily totals reset.")
            )
        return self._notify_failure(_("Z report"), self._error_text(result))

    def action_print_duplicate(self):
        """POST /printers/{id}/duplicate."""
        self.ensure_one()
        result = self._proxy_request("POST", "/duplicate")
        if result.get("ok"):
            return self._notify_success(_("Duplicate"), _("Duplicate printed."))
        return self._notify_failure(_("Duplicate"), self._error_text(result))

    def cash_in(self, amount, reason=""):
        """POST /printers/{id}/deposit — returns parsed result dict."""
        self.ensure_one()
        result = self._proxy_request(
            "POST", "/deposit", body={"amount": float(amount), "text": reason or ""}
        )
        if not result.get("ok"):
            raise UserError(
                _("Cash in failed: %s") % self._error_text(result)
            )
        self.message_post(
            body=_("Cash in: %(amt).2f (%(reason)s)",
                   amt=amount, reason=reason or _("no reason"))
        )
        return result

    def cash_out(self, amount, reason=""):
        """POST /printers/{id}/withdraw."""
        self.ensure_one()
        result = self._proxy_request(
            "POST", "/withdraw", body={"amount": float(amount), "text": reason or ""}
        )
        if not result.get("ok"):
            raise UserError(
                _("Cash out failed: %s") % self._error_text(result)
            )
        self.message_post(
            body=_("Cash out: %(amt).2f (%(reason)s)",
                   amt=amount, reason=reason or _("no reason"))
        )
        return result

    # ---- Notification helpers -----------------------------------------

    @staticmethod
    def _error_text(result):
        msgs = result.get("messages") or []
        errors = [m.get("text", "") for m in msgs if m.get("type") == "error"]
        return "; ".join(errors) or _("Unknown error from proxy")

    @staticmethod
    def _notify_success(title, message):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"title": title, "message": message, "type": "success"},
        }

    @staticmethod
    def _notify_failure(title, message):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": "danger",
                "sticky": True,
            },
        }

    # ---- Auto-Z cron ---------------------------------------------------

    @api.model
    def _cron_generate_z_reports(self):
        now = fields.Datetime.now()
        devices = self.search([
            ("active", "=", True),
            ("auto_z_report", "=", True),
            ("z_report_hour", "=", now.hour),
        ])
        for device in devices:
            if now.minute != device.z_report_minute:
                continue
            try:
                result = device._proxy_request("POST", "/zreport")
                if result.get("ok"):
                    device.last_z_report = fields.Datetime.now()
                    device.message_post(body=_("Auto Z report OK"))
                    device.env.cr.commit()
                else:
                    raise UserError(self._error_text(result))
            except Exception as exc:
                _logger.exception("Auto-Z failed for device %s", device.name)
                device.env.cr.rollback()
                device.message_post(
                    body=_("Auto Z failed: %(err)s", err=str(exc))
                )
