/** @odoo-module **/

/**
 * Browser-side bus handler for server-initiated IoT actions.
 *
 * Mirror of `fiscal_browser_proxy_action.js` but for arbitrary
 * iot.device actions (scale read, display update, scanner queries,
 * etc.) — not just fiscal printer commands.
 *
 * Flow:
 *   1. Server method `iot.device.action_via_proxy()` sends a bus
 *      message on channel "iot.device.request" with shape:
 *         {type, request_id, iot_device_id, iot_box_id,
 *          device_identifier, host, ssl_verify, data}
 *   2. THIS handler receives the message, fetches `host/iot_drivers/action`
 *      (POSTs the payload), and writes the response into
 *      iot.device.response with the matching request_id.
 *   3. Server poller picks up iot.device.response and returns its data.
 *
 * Multiple browser tabs may receive the same message — duplicates are
 * harmless because iot.device.response.request_id is unique-keyed and
 * the server unlinks the row on consume; a second browser writing the
 * same row will succeed and the server will read the first one (race
 * is benign).
 */

import { registry } from "@web/core/registry";

const BUS_CHANNEL = "iot.device.request";
const FETCH_TIMEOUT_MS = 15000;


async function _fetchWithTimeout(url, options, timeoutMs) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
        return await fetch(url, { ...options, signal: controller.signal });
    } finally {
        clearTimeout(timer);
    }
}


async function _onIotDeviceRequest(message, env) {
    if (!message || message.type !== "iot_device_action") {
        return;
    }
    const {
        request_id,
        iot_device_id,
        device_identifier,
        host,
        data,
    } = message;

    if (!host || !device_identifier || !request_id) {
        return;
    }

    // ErpNet.FP accepts both v18 and v19 wire formats. We always send
    // v19 (flat body) since this handler runs in modern (v18 EE+) UIs.
    const url = `${host.replace(/\/+$/, "")}/iot_drivers/action`;
    const body = {
        session_id: request_id,
        device_identifier,
        data: data || {},
    };

    let success = false;
    let responseData = null;
    let errorMessage = "";

    try {
        const resp = await _fetchWithTimeout(
            url,
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            },
            FETCH_TIMEOUT_MS
        );
        if (!resp.ok) {
            errorMessage = `HTTP ${resp.status}: ${await resp.text().catch(() => "")}`;
        } else {
            responseData = await resp.json();
            success = true;
        }
    } catch (e) {
        errorMessage = e.name === "AbortError"
            ? `Timeout fetching ${url} (${FETCH_TIMEOUT_MS}ms)`
            : `Fetch failed: ${e.message || e}`;
    }

    // Write the response back to iot.device.response so the polling
    // server method on `iot.device.action_via_proxy` can see it.
    try {
        await env.services.orm.create("iot.device.response", [{
            request_id,
            iot_device_id,
            success,
            data: success ? JSON.stringify(responseData) : "",
            error_message: errorMessage,
        }]);
    } catch (e) {
        console.error(
            "iot_browser_proxy_handler: failed to write iot.device.response",
            e
        );
    }
}


registry.category("services").add("iot_browser_proxy_handler", {
    dependencies: ["bus_service", "orm"],
    start(env, { bus_service, orm }) {
        bus_service.addChannel(BUS_CHANNEL);
        bus_service.subscribe(BUS_CHANNEL, (payload) =>
            _onIotDeviceRequest(payload, env)
        );
        return {};
    },
});
