/** @odoo-module **/

/**
 * Patch the native Odoo `IoTLongpolling` service so when an iot.box
 * is in `connection_mode === "proxy"`, all `_rpcIoT` traffic (action +
 * long-poll) goes via the Odoo `bus.bus` instead of a direct fetch
 * from the browser.
 *
 * Why: cloud-hosted Odoo + LAN-hosted IoT Box (= ErpNet.FP at
 * 192.168.x.x in the client's store). The browser may or may not be
 * on the same LAN; the cloud server cannot reach the LAN at all. The
 * existing `fiscal.printer.device` flow already uses this pattern
 * for fiscal printers — we generalise it here so EVERY native iot
 * widget (scale, scanner, customer display, payment terminal) works
 * transparently.
 *
 * Direct mode (default): unchanged — calls super._rpcIoT().
 * Proxy mode: server methods call `iot.device.action_via_proxy`
 * which sends a bus message; THIS patch isn't involved in that path.
 * Browser-initiated calls (POS scale button, scanner long-poll) are
 * routed THROUGH the server when proxy mode is set, by calling an
 * RPC method on iot.device that opens a server-side fetch on behalf
 * of the browser.
 *
 * Net result: one mental model — "browser asks Odoo for IoT data, Odoo
 * routes the request" — works in every deployment topology.
 *
 * Backward compat: if the iot.box for the requested ip is in `direct`
 * mode (default), the patch passes through to the native fetch. Old
 * behaviour is preserved.
 */

import { patch } from "@web/core/utils/patch";
import { IoTLongpolling } from "@iot/iot_longpolling";


// In-memory cache of {iot_ip: connection_mode} so we don't RPC for
// every action. Filled once per session by the iot_box_form_view or
// at first action; invalidated when /web reloads.
const _modeCache = new Map();


async function _resolveConnectionMode(orm, iot_ip) {
    if (_modeCache.has(iot_ip)) {
        return _modeCache.get(iot_ip);
    }
    try {
        const result = await orm.searchRead(
            "iot.box",
            [["ip", "=", iot_ip]],
            ["connection_mode"],
            { limit: 1 }
        );
        const mode = (result?.[0]?.connection_mode) || "direct";
        _modeCache.set(iot_ip, mode);
        return mode;
    } catch (e) {
        // If we can't resolve, assume direct — keeps native behaviour
        // intact when this overlay isn't fully wired yet.
        return "direct";
    }
}


patch(IoTLongpolling.prototype, {
    /**
     * @override
     * Routes through Odoo server when iot.box.connection_mode==='proxy'.
     */
    async _rpcIoT(iot_ip, route, data, options) {
        // Setup: lazy import the orm service so we don't change the
        // service's static deps list.
        const orm = window.odoo?.__odoo_session__?.env?.services?.orm
                  || this._ormForProxy
                  || null;
        // Without ORM access, we can't check connection_mode — fall
        // through to native fetch. This is the case very early at
        // boot before services are wired.
        if (!orm) {
            return await super._rpcIoT(iot_ip, route, data, options);
        }
        const mode = await _resolveConnectionMode(orm, iot_ip);
        if (mode !== "proxy") {
            return await super._rpcIoT(iot_ip, route, data, options);
        }
        // Proxy mode → tunnel through Odoo server. The server method
        // `iot.box._rpc_proxy_to_iot` does the HTTP fetch on behalf
        // of the browser and returns the IoT Box's response. This is
        // useful when the browser CAN'T reach 192.168.x.x but the
        // server-via-cloudflare-tunnel path works (or vice-versa).
        try {
            const response = await orm.call(
                "iot.box",
                "_rpc_proxy_to_iot",
                [],
                { iot_ip, route, payload: data }
            );
            return response;
        } catch (e) {
            // Fallback to native fetch — better to try than to fail
            // silently when the proxy method is unavailable.
            return await super._rpcIoT(iot_ip, route, data, options);
        }
    },
});


/**
 * Inject the ORM service into the IoTLongpolling instance once it
 * exists. The native `iotLongpollingService.start` doesn't accept ORM,
 * so we pull it from the registry on demand.
 */
import { registry } from "@web/core/registry";
registry.category("services").add("iot_longpolling_orm_bridge", {
    dependencies: ["orm", "iot_longpolling"],
    start(env, { orm, iot_longpolling }) {
        if (iot_longpolling) {
            iot_longpolling._ormForProxy = orm;
        }
        return {};
    },
});
