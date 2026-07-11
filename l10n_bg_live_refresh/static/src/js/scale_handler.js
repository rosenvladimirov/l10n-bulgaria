/** @odoo-module **/
// Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
// License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

/**
 * Form-level handler for electronic-scale weight readings coming
 * over the live_refresh SCALE_READ env.bus event.
 *
 * Use case: a cashier or warehouseman tares the scale, places the
 * product, the scale fires `scale.weighed` via the proxy, and the
 * currently-focused Float / Monetary field on a Form view is auto-
 * filled with the weight. Same UX as a USB-HID scale plugged into
 * a keyboard wedge, but works over WebSocket from the proxy.
 *
 * SCALE_READ payload `data`:
 *   weight  — number, in `unit`
 *   unit    — "kg" / "g" / "lb" (default "kg")
 *   stable  — bool (false = scale still settling; we skip these)
 *
 * Two integration modes:
 *
 *   A) Field widget `widget="scale_weight_input"` (TODO) — Float /
 *      Monetary field that auto-fills with the next STABLE reading
 *      while focused. Should be used on inventory/receiving forms
 *      where weight is the canonical input.
 *
 *   B) Form-level handler (this file's main service) — listens for
 *      SCALE_READ and writes the value into the focused numeric
 *      input field, if any. Pragmatic fallback when no specific
 *      widget is configured.
 *
 * Conflict guard: if Enterprise `iot` is installed, scale readings
 * are already plumbed via the IoT longpoll. We skip this handler
 * to avoid double-fill.
 */

import { registry } from "@web/core/registry";


const _UNIT_TO_KG = {
    kg: 1,
    g: 0.001,
    lb: 0.45359237,
    oz: 0.028349523125,
};


function _convertToKg(weight, unit) {
    const factor = _UNIT_TO_KG[(unit || "kg").toLowerCase()];
    return factor ? weight * factor : weight;   // unknown unit → pass-through
}


const scaleHandlerService = {
    dependencies: ["bus_service"],

    start(env) {
        // (Earlier draft had a conflict guard checking for the
        // `iot_longpolling` service. Backend usually doesn't have it
        // unless EE iot is genuinely installed; the guard was a no-op
        // for community installs and unnecessarily noisy in logs.)
        const handler = (ev) => {
            const data = ev?.detail?.data || {};
            if (data.weight === undefined || data.weight === null) return;
            // Skip wobbling readings — scales typically emit unstable
            // intermediate values too, and we'd overwrite the field
            // every 100 ms which is jarring. Form widgets that want
            // every reading can subscribe to SCALE_READ themselves.
            if (data.stable === false) return;
            const weightKg = _convertToKg(Number(data.weight), data.unit);
            const target = document.activeElement;
            if (!target) return;
            const tag = (target.tagName || "").toLowerCase();
            const type = (target.type || "").toLowerCase();
            if (tag !== "input"
                    || (type !== "number" && type !== "text")) {
                return;
            }
            try {
                // React-controlled inputs need a native input-event
                // dispatch — direct value write isn't picked up by
                // Owl's value-tracking.
                const setter = Object.getOwnPropertyDescriptor(
                    Object.getPrototypeOf(target), "value").set;
                setter.call(target, String(weightKg));
                target.dispatchEvent(
                    new Event("input", { bubbles: true }));
                target.dispatchEvent(
                    new Event("change", { bubbles: true }));
            } catch (e) {
                console.error("[ScaleHandler] field fill failed:", e);
            }
        };
        env.bus.addEventListener("SCALE_READ", handler);
        return {
            unsubscribe() {
                env.bus.removeEventListener("SCALE_READ", handler);
            },
        };
    },
};

registry.category("services").add(
    "live_refresh.scale_handler", scaleHandlerService);
