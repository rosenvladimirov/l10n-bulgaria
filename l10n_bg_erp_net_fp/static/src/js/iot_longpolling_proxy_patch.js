/** @odoo-module **/

/**
 * Patch the native Odoo 19 `IoTLongpolling` service so when an iot.box
 * is in `connection_mode === "proxy"`, all `_rpcIoT` traffic (action +
 * long-poll) goes via the Odoo `bus.bus` instead of a direct fetch
 * from the browser.
 *
 * v19 import path differs from v18:
 *   v18: import { IoTLongpolling } from "@iot/iot_longpolling";
 *   v19: import { IoTLongpolling } from "@iot/network_utils/iot_longpolling";
 *
 * Behaviour is identical — see the v18 file for the full design
 * narrative. Keeping the two files separate (rather than try/catch
 * over imports) makes the version target obvious from the file path.
 */

import { patch } from "@web/core/utils/patch";
import { IoTLongpolling } from "@iot/network_utils/iot_longpolling";


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
        return "direct";
    }
}


patch(IoTLongpolling.prototype, {
    async _rpcIoT(iot_ip, route, params, timeout = undefined, fallback = false, useLna = false) {
        const orm = this._ormForProxy || null;
        if (!orm) {
            return await super._rpcIoT(iot_ip, route, params, timeout, fallback, useLna);
        }
        const mode = await _resolveConnectionMode(orm, iot_ip);
        if (mode !== "proxy") {
            return await super._rpcIoT(iot_ip, route, params, timeout, fallback, useLna);
        }
        try {
            const response = await orm.call(
                "iot.box",
                "_rpc_proxy_to_iot",
                [],
                { iot_ip, route, payload: params }
            );
            return response;
        } catch (e) {
            return await super._rpcIoT(iot_ip, route, params, timeout, fallback, useLna);
        }
    },
});


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
