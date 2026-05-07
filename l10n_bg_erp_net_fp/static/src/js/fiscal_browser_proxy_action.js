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

// Default per-action timeout. Cmds like Z-report can take a few s of
// serial round-trips, but if it exceeds 30s the device is most likely
// blocked (paper end, cover open, fiscal-mode lock) — better to abort
// the fetch and surface a clear error than freeze the form.
const DEFAULT_TIMEOUT_MS = 30000;

// Error-status codes that classically indicate operator-actionable
// faults. Used for friendlier notification text.
const FRIENDLY_ERROR_HINTS = {
    "E101": _t("Device unreachable. Check serial cable / power."),
    "E199": _t("General device error. Check the next code for detail."),
    "E401": _t("Syntax error in data sent to the device."),
    "E404": _t("Command not allowed in the current fiscal mode."),
    "E411": _t("Unsupported tax group on this device."),
};

function _humanizeMessages(messages) {
    if (!Array.isArray(messages) || !messages.length) {
        return _t("Unknown printer error.");
    }
    const parts = messages.map((m) => {
        const code = (m.code || "").trim();
        const text = (m.text || "").trim();
        const hint = FRIENDLY_ERROR_HINTS[code];
        if (hint) return `${code} ${text} — ${hint}`;
        return code || text ? `${code} ${text}` : "?";
    });
    return parts.join(" · ");
}

async function _fetchWithTimeout(url, options, timeoutMs) {
    // AbortController + setTimeout — guarantees the fetch resolves
    // (success or AbortError) within `timeoutMs`, no matter whether
    // the proxy actually replies.
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    try {
        return await fetch(url, { ...options, signal: controller.signal });
    } finally {
        clearTimeout(timeoutId);
    }
}

async function _checkStatusAndMaybeBlock(env, host, printerId, timeoutMs) {
    // Probe /printers/{id}/status. If the device reports a blocking
    // condition (paper out, cover open, fiscal-mode lock) we surface
    // it BEFORE attempting the actual operation — cheaper to fail
    // here than to leave a half-printed receipt on a paper-out roll.
    const url = host.replace(/\/+$/, "") + "/printers/"
        + encodeURIComponent(printerId) + "/status";
    let r;
    try {
        const resp = await _fetchWithTimeout(url, {
            method: "GET",
            headers: { "Accept": "application/json" },
            credentials: "omit",
        }, timeoutMs);
        r = await resp.json().catch(() => ({}));
        if (!resp.ok) {
            return { blocking: true, reason:
                _t("Printer status check returned HTTP %s", resp.status) };
        }
    } catch (err) {
        const reason = err.name === "AbortError"
            ? _t("Status check timed out after %ss", Math.round(timeoutMs / 1000))
            : err.message || String(err);
        return { blocking: true, reason };
    }
    // The proxy normalizes errors into messages[]. Anything in there
    // with type='error' is blocking.
    const errors = (r.messages || []).filter((m) => m.type === "error");
    if (errors.length) {
        return { blocking: true, reason: _humanizeMessages(errors) };
    }
    if (r.ok === false) {
        return { blocking: true, reason: _humanizeMessages(r.messages || []) };
    }
    return { blocking: false };
}

async function fiscalBrowserProxyAction(env, action) {
    const params = action.params || {};
    const {
        device_id,
        host,
        printer_id,
        method = "POST",
        endpoint,
        ssl_verify = false,  // browsers ignore this; informational only
        timeout_ms = DEFAULT_TIMEOUT_MS,
        skip_status_check = false,
        success_title = _t("Success"),
        success_message = _t("Operation completed"),
        on_success,  // optional ORM method on fiscal.printer.device to call after
    } = params;

    // NOTE on returns: Odoo's ActionManager treats a client action's
    // return value as a chained follow-up action when it's a non-null
    // object. Returning ad-hoc status dicts like `{ok: false, ...}`
    // here crashes the manager with "actions of type undefined" — fix:
    // never return a plain object, only `undefined` (no follow-up) or
    // a real `{type: "ir.actions.<...>", ...}` descriptor.

    if (!host || !endpoint) {
        env.services.notification.add(
            _t("Missing host or endpoint in fiscal proxy action."),
            { type: "danger" },
        );
        return;
    }

    // 1) Pre-flight status — catches paper-out / cover-open BEFORE
    //    we send the actual operation that would otherwise hang.
    if (!skip_status_check) {
        const pre = await _checkStatusAndMaybeBlock(
            env, host, printer_id, Math.min(timeout_ms, 10000));
        if (pre.blocking) {
            env.services.notification.add(
                _t("Printer not ready: %s", pre.reason),
                { type: "danger", sticky: true,
                  title: _t("Operation aborted") },
            );
            return;
        }
    }

    // 2) The real operation, with hard timeout.
    const url = host.replace(/\/+$/, "") + "/" + endpoint.replace(/^\/+/, "");
    let result = null;
    try {
        const resp = await _fetchWithTimeout(url, {
            method,
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            credentials: "omit",
        }, timeout_ms);
        result = await resp.json().catch(() => ({}));
        if (!resp.ok) {
            throw new Error("HTTP " + resp.status + ": "
                + JSON.stringify(result));
        }
    } catch (err) {
        const msg = err.name === "AbortError"
            ? _t("Operation timed out after %ss — printer unresponsive.",
                 Math.round(timeout_ms / 1000))
            : (err.message || String(err));
        env.services.notification.add(msg, {
            type: "danger", sticky: true,
            title: _t("Browser fetch failed (%s)", url),
        });
        return;
    }

    if (result && result.ok === false) {
        env.services.notification.add(
            _humanizeMessages(result.messages || []),
            { type: "danger", sticky: true, title: _t("Printer error") },
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
    // No return — ActionManager would try to chain a non-action object
    // and crash with "actions of type undefined".
}

registry.category("actions").add(
    "l10n_bg_fiscal_browser_proxy", fiscalBrowserProxyAction);
