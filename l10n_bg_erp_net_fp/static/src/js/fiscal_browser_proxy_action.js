/** @odoo-module **/

/**
 * Client action `l10n_bg_fiscal_browser_proxy`
 *
 * Backend buttons (Z report, X report, drawer, ...) on a proxy-mode
 * fiscal device return THIS action instead of doing the proxy round-
 * trip on the server. The browser fetches the printer URL directly,
 * shows the result as a notification, and (if requested) calls back
 * to ORM to update bookkeeping fields like `last_z_report`.
 *
 * Why: server-side bus-channel proxy round-trip times out frequently
 * even with a connected browser (Odoo 18 bus delivery is unreliable
 * for one-off RPC-style use). Direct browser fetch is the same code
 * path the POS already uses and works whenever the browser tab can
 * reach the printer host.
 */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

async function fiscalBrowserProxyAction(env, action) {
    const params = action.params || {};
    const {
        device_id,
        host,
        printer_id,
        method = "POST",
        endpoint,
        ssl_verify = false,  // browsers ignore this; informational only
        success_title = _t("Success"),
        success_message = _t("Operation completed"),
        on_success,  // optional ORM method on fiscal.printer.device to call after
    } = params;

    if (!host || !endpoint) {
        env.services.notification.add(
            _t("Missing host or endpoint in fiscal proxy action."),
            { type: "danger" },
        );
        return;
    }

    const url = host.replace(/\/+$/, "") + "/" + endpoint.replace(/^\/+/, "");
    let result = null;
    try {
        const resp = await fetch(url, {
            method,
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            credentials: "omit",
        });
        result = await resp.json().catch(() => ({}));
        if (!resp.ok) {
            throw new Error("HTTP " + resp.status + ": " + JSON.stringify(result));
        }
    } catch (err) {
        env.services.notification.add(
            _t("Browser fetch to %s failed: %s", url, err.message || err),
            { type: "danger", sticky: true },
        );
        return;
    }

    if (result && result.ok === false) {
        const messages = (result.messages || [])
            .map((m) => `${m.code || ""} ${m.text || ""}`)
            .join("; ");
        env.services.notification.add(
            _t("Printer error: %s", messages || _t("unknown")),
            { type: "danger", sticky: true },
        );
        return;
    }

    // success path
    env.services.notification.add(success_message, {
        type: "success",
        title: success_title,
    });

    // optional bookkeeping callback on the device record
    if (on_success && device_id) {
        try {
            await env.services.orm.call(
                "fiscal.printer.device", on_success, [[device_id]]);
        } catch (err) {
            console.warn(
                "[FiscalBrowserProxy] on_success call failed:", err);
        }
    }

    return result;
}

registry.category("actions").add(
    "l10n_bg_fiscal_browser_proxy", fiscalBrowserProxyAction);
