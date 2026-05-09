"""
OCA-side counterpart of the stock Odoo EE `/iot/setup` endpoint.

Why this exists: Odoo EE's iot module ships an `/iot/setup` JSON-RPC
endpoint that an IoT box hits on boot to register itself as an
`iot.box` record + populate `iot.device` records. OCA's `iot_oca`
module ships an analogous data model (`iot.communication.system` +
`iot.device`) but no HTTP endpoint to feed it — downstream modules
are expected to subclass `iot.communication.system.action` and call
into the device on demand.

This controller adds an `/iot_oca/setup` endpoint that accepts the
EXACT same payload shape as EE's `/iot/setup` (so the same proxy
client code can announce against either), and translates it into
OCA records:

    iot_box.identifier         → iot.communication.system.name
                                 (no separate identifier on OCA)
    iot_box.ip                 → iot.communication.system.erp_net_fp_url
                                 (from `l10n_bg_erp_net_fp_iot_oca`)
    iot_box.token              → matched against `iot_token` system
                                 param on first registration
    devices[<kind>.<id>].name  → iot.device.name
    devices[<kind>.<id>].type  → ignored (OCA doesn't have a typed
                                 selection; downstream subclasses
                                 distinguish by erp_net_fp_kind)

Token check happens only on first system registration. Existing
records are matched by `name` and updated in place.
"""
import logging
from urllib.parse import urlparse

from odoo import _, http
from odoo.http import request

_logger = logging.getLogger(__name__)


# Map from the EE-style devices payload keys (e.g. "scale.cas1") to
# the OCA `erp_net_fp_kind` selection. Mirrors the table in the proxy
# (odoo_erpnet_fp/server/iot_setup.py:_KIND_TO_IOT_TYPE).
_KIND_PREFIX_TO_OCA = {
    "printer": "printer",
    "reader": "reader",
    "scale": "scale",
    "display": "display",
    "pinpad": "pinpad",
}


class IotOcaSetupController(http.Controller):

    @http.route("/iot_oca/setup", type="json", auth="public", csrf=False)
    def update_system(self, **kwargs):
        """OCA mirror of EE iot's `/iot/setup`. Same payload shape."""
        if kwargs:
            iot_box = kwargs.get("iot_box") or {}
            devices = kwargs.get("devices") or {}
        else:
            try:
                data = request.get_json_data()
            except Exception:
                _logger.warning("/iot_oca/setup: invalid JSON body")
                return {"error": "Invalid JSON body"}
            iot_box = data
            devices = (data or {}).get("devices") or {}

        identifier = (iot_box.get("identifier") or "").strip()
        if not identifier:
            return {"error": "identifier required"}
        name = (iot_box.get("name") or identifier).strip()
        ip = (iot_box.get("ip") or "").strip()
        token = (iot_box.get("token") or "").strip()

        # Build full URL from `ip` if it's a bare hostname, else use
        # as-is. The proxy advertises just a hostname; the OCA
        # `read_weight` etc. helpers expect a full URL with scheme.
        if ip and "://" not in ip:
            erp_net_fp_url = f"https://{ip}/"
        else:
            erp_net_fp_url = ip.rstrip("/") + "/" if ip else ""

        System = request.env["iot.communication.system"].sudo()
        Device = request.env["iot.device"].sudo()
        ICP = request.env["ir.config_parameter"].sudo()

        # Match an existing system by its identifier-as-name. OCA has no
        # dedicated identifier field on iot.communication.system, so we
        # use `name` as the stable key.
        system = System.search([("name", "=", identifier)], limit=1)
        if not system:
            iot_token = (ICP.get_param("iot_token") or "").strip("\n").strip()
            if not iot_token or iot_token != token:
                _logger.warning(
                    "/iot_oca/setup: token mismatch for %s "
                    "(expected something, got %r)",
                    identifier, token[:8] + "..." if token else "(empty)",
                )
                return {"error": "token mismatch"}
            system = System.create({
                "name": identifier,
                "erp_net_fp_url": erp_net_fp_url,
                "erp_net_fp_ssl_verify": False,
            })
            _logger.info(
                "/iot_oca/setup: created iot.communication.system %s "
                "with %d device(s)", identifier, len(devices),
            )
        else:
            updates = {}
            if erp_net_fp_url and system.erp_net_fp_url != erp_net_fp_url:
                updates["erp_net_fp_url"] = erp_net_fp_url
            if updates:
                system.write(updates)

        # Create / update device records. Match by `erp_net_fp_identifier`
        # (the full <kind>.<id> string the proxy uses internally) so
        # repeated announcements are idempotent.
        for device_identifier, info in (devices or {}).items():
            if not isinstance(info, dict):
                continue
            kind_prefix = device_identifier.split(".", 1)[0].lower()
            erp_kind = _KIND_PREFIX_TO_OCA.get(kind_prefix, kind_prefix)
            dev_name = info.get("name") or device_identifier
            existing = Device.search([
                ("communication_system_id", "=", system.id),
                ("erp_net_fp_identifier", "=", device_identifier),
            ], limit=1)
            vals = {
                "communication_system_id": system.id,
                "name": dev_name,
                "erp_net_fp_kind": erp_kind,
                "erp_net_fp_identifier": device_identifier,
                "model": info.get("manufacturer") or "ErpNet.FP",
            }
            if existing:
                existing.write(vals)
            else:
                Device.create(vals)

        # Mark stale devices (registered before but not in this
        # announcement) inactive so the operator sees them disappear.
        seen = set(devices.keys() or [])
        stale = Device.search([
            ("communication_system_id", "=", system.id),
            ("erp_net_fp_identifier", "!=", False),
            ("erp_net_fp_identifier", "not in", list(seen)),
            ("active", "=", True),
        ])
        if stale:
            stale.write({"active": False})

        return {"system_id": system.id, "devices_count": len(devices or {})}
