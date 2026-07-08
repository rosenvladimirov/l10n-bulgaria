/** @odoo-module **/

/**
 * ErpNet.FP barcode-reader bridge (community alternative to Enterprise
 * `iot` + `pos_iot`).
 *
 * Subscribes to one or more proxy readers via WebSocket
 * (`/readers/<id>/ws`) and emits Owl events of shape:
 *   { reader_id, barcode, timestamp }
 *
 * Consumers (POS frontend, backend form bridge, etc.) call
 *   const sub = svc.subscribe((scan) => { ... });
 *   sub.unsubscribe();
 *
 * Auto-discovery: on start the service GETs /readers and connects
 * to every active one. On WS disconnect it retries with exponential
 * backoff capped at 30s.
 *
 * Host resolution — single source of truth is `fiscal.printer.device.host`
 * (the URL of the Odoo.ErpNet.FP proxy in front of the hardware). The
 * service picks it up automatically; no separate config to set:
 *
 *   POS context     → pos.config.l10n_bg_erp_net_fp_host  (computed
 *                     from pos.config.l10n_bg_fiscal_printer_id.host)
 *   Backend context → searchRead the first active fiscal.printer.device
 *                     with connection_mode='proxy' and use its host.
 *
 * If neither is configured the service stays silent (no readers).
 *
 * Designed to live in BOTH POS asset bundle and web.assets_backend.
 *
 * NOT YET IMPLEMENTED: writes to the reader (we only consume scans).
 */

import { EventBus } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { resolveProxyHost } from "@l10n_bg_erp_net_base/services/proxy_host";


const RECONNECT_MIN_MS = 1_000;
const RECONNECT_MAX_MS = 30_000;
const POLL_INTERVAL_MS = 30_000;   // re-scan /readers periodically
                                    // for hot-plugged devices


/** Inert service object — returned when no proxy host is configured,
 * so consumers can still call .subscribe() without crashing. */
function _disabledService() {
    return {
        subscribe(_handler) {
            return { unsubscribe() {} };
        },
        list() { return []; },
        async refresh() {},
        bus: null,
    };
}


class ErpNetReader {
    constructor(host, info) {
        this.host = host.replace(/\/+$/, "");
        this.id = info.id;
        this.name = info.name || info.id;
        this.transport = info.transport || "unknown";
        this.bus = new EventBus();   // emits "scan"
        this._ws = null;
        this._backoff = RECONNECT_MIN_MS;
        this._closing = false;
    }

    connect() {
        if (this._ws || this._closing) return;
        // ws[s]://host/readers/<id>/ws
        const wsUrl =
            this.host.replace(/^http/, "ws") +
            `/readers/${encodeURIComponent(this.id)}/ws`;
        try {
            this._ws = new WebSocket(wsUrl);
        } catch (e) {
            console.error("[ErpNetReader]",
                          this.id, "WS construct failed:", e);
            this._scheduleReconnect();
            return;
        }
        this._ws.onopen = () => {
            console.log("[ErpNetReader]", this.id, "WS open");
            this._backoff = RECONNECT_MIN_MS;
        };
        this._ws.onmessage = (ev) => {
            let payload;
            try {
                payload = JSON.parse(ev.data);
            } catch (_) {
                payload = { barcode: String(ev.data || "") };
            }
            const barcode = (payload && (
                payload.barcode || payload.value || payload.data)) || "";
            if (!barcode) return;
            this.bus.trigger("scan", {
                reader_id: this.id,
                barcode: String(barcode),
                timestamp: payload.timestamp || Date.now(),
                raw: payload,
            });
        };
        this._ws.onerror = (ev) => {
            console.warn("[ErpNetReader]", this.id, "WS error:", ev);
        };
        this._ws.onclose = (ev) => {
            console.log("[ErpNetReader]", this.id,
                        "WS closed code=", ev.code);
            this._ws = null;
            if (!this._closing) {
                this._scheduleReconnect();
            }
        };
    }

    _scheduleReconnect() {
        const delay = this._backoff;
        this._backoff = Math.min(this._backoff * 2, RECONNECT_MAX_MS);
        setTimeout(() => this.connect(), delay);
    }

    close() {
        this._closing = true;
        if (this._ws) {
            try { this._ws.close(); } catch (_) {}
            this._ws = null;
        }
    }
}


export const erpnetReaderService = {
    dependencies: ["orm"],

    async start(env, { orm }) {
        // ─── host resolution ─────────────────────────────────────
        // Single source of truth is `fiscal.printer.device.host`, via the
        // shared base helper (POS-session shortcut + backend RPC fallback).
        const baseUrl = await resolveProxyHost(env, orm, "ErpNetReaderService");
        if (!baseUrl) {
            console.warn("[ErpNetReaderService] no fiscal.printer.device "
                         + "host configured — readers disabled");
            return _disabledService();
        }

        const readers = new Map();   // id → ErpNetReader
        const globalBus = new EventBus();   // emits "scan" — fan-out

        async function rescan() {
            let known;
            try {
                const resp = await fetch(`${baseUrl}/readers`, {
                    credentials: "omit",
                });
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                known = await resp.json();
            } catch (e) {
                console.warn("[ErpNetReaderService] rescan failed:", e);
                return;
            }
            // Hot-plug: add new readers, leave existing alone, prune gone
            const seen = new Set();
            for (const [id, info] of Object.entries(known || {})) {
                seen.add(id);
                if (readers.has(id)) continue;
                const reader = new ErpNetReader(baseUrl, { id, ...info });
                reader.bus.addEventListener("scan", (ev) => {
                    globalBus.trigger("scan", ev.detail);
                });
                readers.set(id, reader);
                reader.connect();
                console.log("[ErpNetReaderService] +reader:", id);
            }
            for (const id of [...readers.keys()]) {
                if (!seen.has(id)) {
                    readers.get(id).close();
                    readers.delete(id);
                    console.log("[ErpNetReaderService] -reader:", id);
                }
            }
        }

        await rescan();
        setInterval(rescan, POLL_INTERVAL_MS);

        return {
            /**
             * Subscribe to ALL scans from ALL readers.
             * Returns an object with .unsubscribe() to detach.
             */
            subscribe(handler) {
                const wrap = (ev) => handler(ev.detail);
                globalBus.addEventListener("scan", wrap);
                return {
                    unsubscribe() {
                        globalBus.removeEventListener("scan", wrap);
                    },
                };
            },

            /** List active reader IDs. */
            list() {
                return [...readers.keys()];
            },

            /** Force a re-scan (e.g. after adding a new reader). */
            async refresh() {
                await rescan();
            },

            /** Bare bus access (advanced). */
            bus: globalBus,
        };
    },
};

registry.category("services").add(
    "l10n_bg_erp_net_fp.reader", erpnetReaderService);
