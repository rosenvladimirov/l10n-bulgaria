/** @odoo-module **/

/**
 * Shared host-resolution for Odoo.ErpNet.FP proxy consumers.
 *
 * Single source of truth for "where is the proxy?" — reused by the
 * reader (`l10n_bg_erp_net_reader`) and scale (`l10n_bg_erp_net_scale`)
 * services so neither hard-codes the model lookup.
 *
 * Resolution order:
 *   1. POS context (opportunistic) — `pos.session.l10n_bg_erp_net_fp_host`,
 *      computed on `pos.config` from its primary fiscal printer. Read only
 *      when the POS service is present; skipped gracefully in a POS-absent
 *      backend (e.g. a manufacturing-only Shop Floor install).
 *   2. Backend — the first active `fiscal.printer.device` in proxy mode
 *      with a host set (RPC via the orm service).
 *
 * Returns the trailing-slash-trimmed base URL, or "" when nothing is
 * configured (callers should degrade to an inert service).
 *
 * @param {object} env  the Owl service env
 * @param {object} orm  the "orm" service
 * @param {string} [tag="ErpNetProxy"] short prefix for console warnings
 * @returns {Promise<string>} base URL (no trailing slash) or ""
 */
export async function resolveProxyHost(env, orm, tag = "ErpNetProxy") {
    let host = "";
    // 1) POS context — opportunistic, guarded (no hard POS dependency).
    if (env.services && env.services.pos &&
            env.services.pos.session &&
            env.services.pos.session.l10n_bg_erp_net_fp_host) {
        host = env.services.pos.session.l10n_bg_erp_net_fp_host;
    }
    // 2) Backend — read straight off the transport model (defined in base).
    if (!host) {
        try {
            const recs = await orm.searchRead(
                "fiscal.printer.device",
                [["active", "=", true],
                 ["connection_mode", "=", "proxy"],
                 ["host", "!=", false]],
                ["host"],
                { limit: 1, order: "id" },
            );
            if (recs && recs.length) {
                host = recs[0].host;
            }
        } catch (e) {
            console.warn(`[${tag}] fiscal.printer.device lookup failed:`, e);
        }
    }
    if (!host) {
        return "";
    }
    return host.replace(/\/+$/, "");
}
