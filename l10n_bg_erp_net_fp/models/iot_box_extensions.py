"""
Extends `iot.box` with a `connection_mode` (direct / proxy), an
ErpNet.FP URL field, and a one-way bridge from `fiscal.printer.device`
records — see `fiscal_printer_device_id` field below.

Why extend instead of replace:

  Native Odoo `iot.box` assumes the browser can reach the box directly
  on its IP (`https://<box>/iot_drivers/action`). That assumption breaks
  for cloud-hosted Odoo (Odoo.sh, our poligroup-hosted clients) when
  the IoT box (ErpNet.FP) lives in the client's LAN at 192.168.x.x —
  the cloud server cannot reach it AND the browser may or may not be
  on the same LAN.

  The custom `fiscal.printer.device` flow already solved this with a
  bus.bus-based browser proxy. We lift the same idea up to the iot.box
  level so EVERY native iot.device interaction (scale / scanner /
  display / printer / pinpad) can use it transparently — no per-device
  configuration.

ALL existing behaviour is preserved. `connection_mode` defaults to
`direct`, which is the native Odoo flow. Setting it to `proxy` opts in
to bus-based browser fetching.
"""

from urllib.parse import urlparse

from odoo import _, api, fields, models


class IotBox(models.Model):
    _inherit = "iot.box"

    connection_mode = fields.Selection(
        [
            ("direct", "Direct (browser → IoT Box on same network)"),
            ("proxy", "Browser Proxy (server signals browser via bus)"),
        ],
        string="Connection Mode",
        default="direct",
        required=True,
        tracking=True,
        help="Direct: standard native Odoo flow — browser fetches the "
             "IoT Box URL directly. Use when both browser and IoT Box "
             "are reachable on the same network.\n\n"
             "Browser Proxy: server-initiated actions (cron, methods) "
             "send a bus.bus message; the browser fetches the IoT Box "
             "URL on the server's behalf and writes the result back to "
             "iot.device.response. Use when Odoo runs in the cloud and "
             "the IoT Box is in a private LAN.",
    )

    erp_net_fp_url = fields.Char(
        string="ErpNet.FP URL",
        help="If this IoT Box is actually an ErpNet.FP instance, this "
             "is the base URL we hit for /scales, /displays, /readers, "
             "/printers — used by the auto-discovery wizard. Falls "
             "back to the standard `ip` field if blank.",
    )

    erp_net_fp_ssl_verify = fields.Boolean(
        string="Verify SSL",
        default=False,
        help="Disable for self-signed certificates in client LANs.",
    )

    fiscal_printer_device_id = fields.Many2one(
        "fiscal.printer.device",
        string="Linked legacy Fiscal Printer Device",
        help="Optional one-way link: an iot.box can be created from an "
             "existing fiscal.printer.device so both legacy and native "
             "iot flows reach the same physical printer. The "
             "fiscal.printer.device record stays the source of truth "
             "for host / printer_id; iot.box mirrors them on save.",
    )

    @api.onchange("ip", "erp_net_fp_url")
    def _onchange_host_autodetect_mode(self):
        """Set connection_mode based on host type — same logic as the
        existing fiscal.printer.device._onchange_host. Local IP / .local
        host → proxy; public host → direct."""
        for box in self:
            host = box.erp_net_fp_url or box.ip or ""
            if not host:
                continue
            try:
                hostname = urlparse(host).hostname or host
            except Exception:
                hostname = host
            hostname = hostname.lower()
            is_local = (
                hostname in ("localhost", "127.0.0.1", "::1")
                or hostname.startswith("192.168.")
                or hostname.startswith("10.")
                or any(hostname.startswith(f"172.{i}.") for i in range(16, 32))
                or hostname.endswith(".local")
            )
            box.connection_mode = "proxy" if is_local else "direct"

    def _get_erp_net_fp_base_url(self):
        """Returns base URL for ErpNet.FP HTTP API — checks
        erp_net_fp_url first, falls back to constructing from ip."""
        self.ensure_one()
        if self.erp_net_fp_url:
            return self.erp_net_fp_url.rstrip("/")
        if self.ip:
            # Reuse iot.box._compute_ip_url logic minimally
            return f"http://{self.ip}:8069".rstrip("/")
        return ""

    @api.model
    def _rpc_proxy_to_iot(self, iot_ip, route, payload):
        """Browser-side IoTLongpolling patch calls this when the box
        is in `connection_mode == proxy` and the browser itself can't
        reach the IoT Box. The server makes the HTTP fetch on the
        browser's behalf and returns the response.

        Use case: Odoo on cloud + ErpNet.FP behind Cloudflare tunnel.
        Browser sees Odoo at https://odoo.client.com but the IoT Box
        is on https://erp-net-fp.client.com — accessible from server
        but not necessarily from every browser network. Tunneling
        through the server is the universal-fallback path.

        :param iot_ip: the IP/hostname the browser tried.
        :param route: relative path, e.g. "/iot_drivers/action".
        :param payload: full request body shape (already wrapped per
                        v18 / v19 conventions by the caller).
        :return: dict — the IoT Box's response, ready for the browser.
        """
        import requests
        box = self.search([("ip", "=", iot_ip)], limit=1)
        if not box:
            box = self.search(
                [("erp_net_fp_url", "ilike", iot_ip)], limit=1)
        if not box:
            return {"result": False,
                    "error": f"No iot.box configured for {iot_ip!r}"}
        base_url = box._get_erp_net_fp_base_url()
        if not base_url:
            return {"result": False,
                    "error": f"iot.box {box.name!r} has no URL"}
        url = f"{base_url.rstrip('/')}{route if route.startswith('/') else '/' + route}"
        verify = box.erp_net_fp_ssl_verify
        try:
            resp = requests.post(url, json=payload, timeout=15, verify=verify)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as exc:
            return {"result": False, "error": str(exc)}
