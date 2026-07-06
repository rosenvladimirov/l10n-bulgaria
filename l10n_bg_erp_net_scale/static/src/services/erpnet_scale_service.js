/** @odoo-module **/

/**
 * ErpNet.FP weighing-scale service (community/direct-proxy alternative
 * to the Enterprise `iot` + `pos_iot_adam_scale` path).
 *
 * Reads weight ON DEMAND from the Odoo.ErpNet.FP proxy:
 *   GET /scales                 → { "<id>": {id, driver, port}, ... }
 *   GET /scales/<id>/weight     → { ok, weightKg (alias weight_kg),
 *                                   status:[...], error }
 *
 * Consumers call:
 *   const svc = useService("l10n_bg_erp_net_fp.scale");
 *   const res = await svc.readWeight();        // first/only scale
 *   const res = await svc.readWeight("scale1"); // explicit id
 *   // → { ok, weight_kg, status, error, scale_id }
 *
 * Host resolution mirrors the reader service — single source of truth is
 * `fiscal.printer.device.host` (the proxy URL). If none is configured the
 * service stays inert (readWeight → { ok:false }), so callers never crash.
 *
 * Unlike the reader (push over WebSocket), the scale is polled on demand:
 * a weight makes sense only at the moment the operator asks for it.
 */

import { registry } from "@web/core/registry";
import { resolveProxyHost } from "@l10n_bg_erp_net_base/services/proxy_host";


/** Inert service — returned when no proxy host is configured. */
function _disabledService() {
    return {
        async list() {
            return [];
        },
        async readWeight() {
            return { ok: false, error: "no proxy host configured" };
        },
        get host() {
            return "";
        },
    };
}


export const erpnetScaleService = {
    dependencies: ["orm"],

    async start(env, { orm }) {
        // ─── host resolution — shared base helper ────────────────────
        const baseUrl = await resolveProxyHost(env, orm, "ErpNetScaleService");
        if (!baseUrl) {
            console.warn("[ErpNetScaleService] no fiscal.printer.device "
                         + "host configured — scales disabled");
            return _disabledService();
        }

        /** List configured scale IDs on the proxy. */
        async function list() {
            try {
                const resp = await fetch(`${baseUrl}/scales`, {
                    credentials: "omit",
                });
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                const data = await resp.json();
                return Object.keys(data || {});
            } catch (e) {
                console.warn("[ErpNetScaleService] list failed:", e);
                return [];
            }
        }

        /**
         * Read the current weight. Without an id, uses the first scale.
         * Returns { ok, weight_kg, status, error, scale_id }.
         */
        async function readWeight(scaleId) {
            let id = scaleId;
            if (!id) {
                const ids = await list();
                id = ids[0];
            }
            if (!id) {
                return { ok: false, error: "no scale configured" };
            }
            try {
                const resp = await fetch(
                    `${baseUrl}/scales/${encodeURIComponent(id)}/weight`,
                    { credentials: "omit" },
                );
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                const d = await resp.json();
                // Proxy serialises weight as `weightKg` (alias `weight_kg`).
                const kg = (d.weightKg ?? d.weight_kg ?? null);
                return {
                    ok: !!d.ok && kg != null,
                    weight_kg: kg,
                    status: d.status || [],
                    error: d.error || null,
                    scale_id: id,
                };
            } catch (e) {
                return { ok: false, error: String(e), scale_id: id };
            }
        }

        return {
            list,
            readWeight,
            get host() {
                return baseUrl;
            },
        };
    },
};

registry.category("services").add(
    "l10n_bg_erp_net_fp.scale", erpnetScaleService);
