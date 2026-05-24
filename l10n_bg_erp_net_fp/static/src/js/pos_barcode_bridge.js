/** @odoo-module **/

/**
 * POS-side bridge for ErpNet.FP barcode reader scans.
 *
 * Subscribes to `l10n_bg_erp_net_fp.reader` service and forwards each
 * scan into the POS core `barcode_reader` service, which already
 * knows how to:
 *   - parse the barcode (Nomenclature / EAN-13 / GTIN)
 *   - dispatch to the correct screen handler (product, customer,
 *     discount, etc.)
 *   - emit hooks for cashier search-bar focus
 *
 * Net effect: hardware barcode reader works in POS without Odoo
 * Enterprise `pos_iot` — same UX as if the scanner were a keyboard
 * wedge, but over WebSocket from the proxy (works on iPads too).
 */

import { registry } from "@web/core/registry";


const posReaderBridgeService = {
    dependencies: [
        "l10n_bg_erp_net_fp.reader",
        "barcode_reader",
        "pos",
    ],

    start(env, { "l10n_bg_erp_net_fp.reader": reader,
                  barcode_reader: posBarcode }) {
        if (!posBarcode || typeof posBarcode.scan !== "function") {
            console.warn("[PosBarcodeBridge] POS barcode_reader service "
                         + "is missing scan(); aborting bridge");
            return {};
        }
        const sub = reader.subscribe(({ reader_id, barcode }) => {
            console.log("[PosBarcodeBridge] reader=%s barcode=%s",
                        reader_id, barcode);
            try {
                posBarcode.scan(barcode);
            } catch (e) {
                console.error("[PosBarcodeBridge] scan dispatch failed:",
                              e);
            }
        });
        return { unsubscribe: () => sub.unsubscribe() };
    },
};

registry.category("services").add(
    "l10n_bg_erp_net_fp.pos_barcode_bridge", posReaderBridgeService);
