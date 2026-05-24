/** @odoo-module **/

/**
 * Backend-side bridge for ErpNet.FP barcode reader scans.
 *
 * Subscribes to `l10n_bg_erp_net_fp.reader` service in the web
 * backend and forwards each scan into Odoo's core
 * `barcode_service` (which existing form-view handlers already
 * listen to — same path as a keyboard wedge or Enterprise IoT box).
 *
 * Net effect: any backend form/list view that reacts to barcode
 * scans (stock pickings, inventory adjustments, hr.attendance, …)
 * works with the proxy reader, without `iot` from Enterprise.
 *
 * Notes:
 *   - We don't intercept browser keystrokes — only WS scans from
 *     the proxy. So plain USB-HID keyboard scanners still work
 *     through the OS keyboard layer; our bridge is for proxy-only
 *     transports (BT-HID-over-VSP, serial, custom drivers).
 *   - Core `barcode_service` exposes `.bus.trigger("barcode_scanned",
 *     {barcode, target})` — see web/static/src/core/barcode/.
 */

import { registry } from "@web/core/registry";


const backendReaderBridgeService = {
    dependencies: ["l10n_bg_erp_net_fp.reader", "barcode"],

    start(env, { "l10n_bg_erp_net_fp.reader": reader,
                  barcode: barcodeSvc }) {
        if (!barcodeSvc || !barcodeSvc.bus) {
            console.warn("[BackendBarcodeBridge] core barcode service "
                         + "has no .bus; aborting bridge");
            return {};
        }
        const sub = reader.subscribe(({ reader_id, barcode }) => {
            console.log("[BackendBarcodeBridge] reader=%s barcode=%s",
                        reader_id, barcode);
            try {
                barcodeSvc.bus.trigger("barcode_scanned", {
                    barcode,
                    target: document.activeElement,
                });
            } catch (e) {
                console.error("[BackendBarcodeBridge] dispatch failed:",
                              e);
            }
        });
        return { unsubscribe: () => sub.unsubscribe() };
    },
};

registry.category("services").add(
    "l10n_bg_erp_net_fp.backend_barcode_bridge",
    backendReaderBridgeService);
