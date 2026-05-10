/** @odoo-module **/

/**
 * Device proxy service — browser-side fetch wrapper to ErpNet.FP.
 *
 * The Odoo server cannot reach ErpNet.FP when it sits behind a
 * private LAN at the merchant's site (`erpnet.lan.mcpworks.net`).
 * The browser, however, IS on that LAN — so all fiscal-device I/O
 * goes through THIS service, not through the Odoo backend.
 *
 * Per-operation timeouts mirror the constants on the Python side:
 *   PLU sync   — 90s
 *   X / Z      — 90s
 *   VAT push   — 30s
 *   Operators  — 30s
 *   Status     —  5s
 */

import { registry } from "@web/core/registry";


export const PROXY_TIMEOUTS = {
    plu_sync: 90000,
    z_report: 90000,
    x_report: 90000,
    vat_rates: 30000,
    operators: 30000,
    status: 5000,
    journal: 60000,
};


export const deviceProxyService = {
    dependencies: [],

    start() {
        async function _fetchJson(
            baseUrl, path, { method = "GET", body, timeoutMs }
        ) {
            if (!baseUrl) {
                throw new Error("Device has no host URL configured.");
            }
            const url = baseUrl.replace(/\/+$/, "") + "/"
                + path.replace(/^\/+/, "");
            const ctl = new AbortController();
            const tid = setTimeout(() => ctl.abort(), timeoutMs);
            try {
                const resp = await fetch(url, {
                    method,
                    headers: {
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    body: body !== undefined
                        ? JSON.stringify(body) : undefined,
                    credentials: "omit",
                    signal: ctl.signal,
                });
                const text = await resp.text();
                let json = null;
                try { json = text ? JSON.parse(text) : null; }
                catch (_e) { /* keep null */ }
                if (!resp.ok) {
                    const detail = json
                        ? (json.detail || JSON.stringify(json))
                        : (text || `HTTP ${resp.status}`);
                    const err = new Error(
                        `HTTP ${resp.status}: ${detail}`);
                    err.status = resp.status;
                    err.url = url;
                    throw err;
                }
                return json;
            } catch (err) {
                if (err.name === "AbortError") {
                    const tErr = new Error(
                        `Timeout after ${timeoutMs / 1000}s on ${url}`);
                    tErr.code = "timeout";
                    tErr.url = url;
                    throw tErr;
                }
                throw err;
            } finally {
                clearTimeout(tid);
            }
        }

        function _printerPath(printer_id, suffix) {
            return `printers/${encodeURIComponent(printer_id)}/`
                + suffix.replace(/^\/+/, "");
        }

        return {
            // ─── status / pre-flight ─────────────────────────────
            async status(device) {
                return _fetchJson(
                    device.host,
                    _printerPath(device.printer_id, "status"),
                    { method: "GET", timeoutMs: PROXY_TIMEOUTS.status },
                );
            },

            // ─── reports ─────────────────────────────────────────
            async xReport(device) {
                return _fetchJson(
                    device.host,
                    _printerPath(device.printer_id, "xreport"),
                    { method: "POST", timeoutMs: PROXY_TIMEOUTS.x_report },
                );
            },

            async zReport(device) {
                return _fetchJson(
                    device.host,
                    _printerPath(device.printer_id, "zreport"),
                    { method: "POST", timeoutMs: PROXY_TIMEOUTS.z_report },
                );
            },

            async zReportTotals(device) {
                return _fetchJson(
                    device.host,
                    _printerPath(device.printer_id, "zreport-totals"),
                    { method: "POST", timeoutMs: PROXY_TIMEOUTS.z_report },
                );
            },

            async journal(device, fromTs = null, toTs = null) {
                let path = _printerPath(device.printer_id, "journal");
                const params = new URLSearchParams();
                if (fromTs) params.set("fromDate", fromTs);
                if (toTs) params.set("toDate", toTs);
                if ([...params].length) {
                    path = `${path}?${params.toString()}`;
                }
                return _fetchJson(device.host, path, {
                    method: "GET", timeoutMs: PROXY_TIMEOUTS.journal,
                });
            },

            // ─── push (config) ───────────────────────────────────
            async pushPluBulk(device, items) {
                return _fetchJson(
                    device.host,
                    _printerPath(device.printer_id, "plu/sync"),
                    {
                        method: "POST",
                        body: { items },
                        timeoutMs: PROXY_TIMEOUTS.plu_sync,
                    },
                );
            },

            async pushVatRates(device, groups) {
                return _fetchJson(
                    device.host,
                    _printerPath(device.printer_id, "vat-rates"),
                    {
                        method: "POST",
                        body: { groups },
                        timeoutMs: PROXY_TIMEOUTS.vat_rates,
                    },
                );
            },

            async pushOperators(device, operators) {
                return _fetchJson(
                    device.host,
                    _printerPath(device.printer_id, "operators"),
                    {
                        method: "POST",
                        body: { operators },
                        timeoutMs: PROXY_TIMEOUTS.operators,
                    },
                );
            },
        };
    },
};

registry.category("services").add(
    "l10n_bg_external_shift.device_proxy", deviceProxyService);
