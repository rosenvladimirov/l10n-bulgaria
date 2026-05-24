/** @odoo-module **/
// Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

/**
 * Form-level handler for barcode scans coming over the live_refresh
 * BARCODE_SCANNED env.bus event.
 *
 * Two integration modes:
 *
 *   A) Field widget `widget="barcode_scan_input"` — Char field that
 *      auto-fills with the next scan while the field is focused
 *      (or, in `auto-focus` mode, always). Useful on custom forms
 *      where one specific field collects barcodes.
 *
 *   B) Form-level handler (this file's main service) — listens for
 *      BARCODE_SCANNED and dispatches to the core
 *      `barcode_service.bus` so existing form handlers
 *      (stock.picking, product, hr.attendance...) get it as if it
 *      were a keyboard-wedge scan. Single subscription, fans out
 *      to every form view that knows what to do with a barcode.
 *
 * Conflict guard: if Enterprise `iot` is installed, that module
 * already hooks `barcode_service` via its own IoT longpoll path.
 * Doubling up would dispatch each scan twice. We detect EE-iot by
 * looking for the `iot_longpolling` service in the registry and
 * skip the handler if present.
 */

import { registry } from "@web/core/registry";


const barcodeHandlerService = {
    dependencies: ["bus_service", "barcode"],

    start(env, { bus_service: _bus, barcode: barcodeSvc }) {
        // Conflict guard — EE iot already feeds barcode_service.
        const services = registry.category("services");
        if (services.contains("iot_longpolling")) {
            console.info("[BarcodeHandler] EE iot detected — "
                         + "skipping live_refresh barcode handler "
                         + "to avoid double-dispatch");
            return {};
        }
        if (!barcodeSvc || !barcodeSvc.bus) {
            console.warn("[BarcodeHandler] core barcode service has "
                         + "no .bus; nothing to forward to");
            return {};
        }
        const handler = (ev) => {
            const code = ev?.detail?.data?.barcode;
            if (!code) return;
            try {
                barcodeSvc.bus.trigger("barcode_scanned", {
                    barcode: String(code),
                    target: document.activeElement,
                });
            } catch (e) {
                console.error("[BarcodeHandler] dispatch failed:", e);
            }
        };
        env.bus.addEventListener("BARCODE_SCANNED", handler);
        return {
            unsubscribe() {
                env.bus.removeEventListener("BARCODE_SCANNED", handler);
            },
        };
    },
};

registry.category("services").add(
    "live_refresh.barcode_handler", barcodeHandlerService);
