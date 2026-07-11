/** @odoo-module **/
// Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
// License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

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


/** Find an <input> belonging to a Form view of `model`, optionally
 * scoped to the form rendered from view xml_id `formXmlid`, whose
 * field name is `field`. Returns null if no such input is in the
 * DOM right now. */
function _findTargetInput(model, field, formXmlid) {
    if (!model || !field) return null;
    let scope = document;
    if (formXmlid) {
        // Odoo Form renders set `data-view-xmlid` on the root view
        // wrapper when the controller was opened by xml_id. Forms
        // opened by ir.actions.act_window won't have it — that's
        // fine, we just don't narrow.
        const root = document.querySelector(
            `[data-view-xmlid="${formXmlid}"]`);
        if (root) scope = root;
    }
    // Odoo Form widgets render `<input name="field_name">` inside
    // a wrapper carrying the model on the controller's view root.
    // Fallback: any input whose surrounding .o_form_view's model
    // matches.
    const forms = scope.querySelectorAll(".o_form_view");
    for (const form of forms) {
        const viewModel = form.dataset.model
            || form.querySelector("[data-model]")?.dataset.model;
        if (model && viewModel && viewModel !== model) continue;
        const input = form.querySelector(`[name="${field}"] input,
                                           [name="${field}"] textarea`);
        if (input) return input;
    }
    return null;
}


/** Drive a parsed value into a native input the React/Owl way:
 * use the prototype setter so React's value tracker sees the
 * mutation, then dispatch input + change events for Owl. */
function _setInputValue(input, value) {
    const proto = Object.getPrototypeOf(input);
    const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
    if (setter) {
        setter.call(input, String(value));
    } else {
        input.value = String(value);
    }
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
}


const barcodeHandlerService = {
    dependencies: ["bus_service", "barcode", "orm"],

    start(env, { bus_service: _bus, barcode: barcodeSvc, orm }) {
        // (Earlier draft had a conflict guard checking for the
        // `iot_longpolling` service in the registry. Backend doesn't
        // always have it though — only when EE iot is genuinely
        // installed — so the guard was a no-op there. Kept commented
        // for future reference if double-dispatch ever becomes an
        // issue.)
        if (!barcodeSvc || !barcodeSvc.bus) {
            console.warn("[BarcodeHandler] core barcode service has "
                         + "no .bus; nothing to forward to");
            return {};
        }
        // Cache the nomenclature id once — most installs have one.
        let nomenclatureId = null;
        async function _getNomenclatureId() {
            if (nomenclatureId !== null) return nomenclatureId;
            try {
                const recs = await orm.searchRead(
                    "barcode.nomenclature", [], ["id"],
                    { limit: 1, order: "id" });
                nomenclatureId = recs[0]?.id || false;
            } catch (e) {
                console.warn("[BarcodeHandler] no nomenclature:", e);
                nomenclatureId = false;
            }
            return nomenclatureId;
        }

        const handler = async (ev) => {
            const code = ev?.detail?.data?.barcode;
            if (!code) return;
            // Two delivery paths:
            //   (a) the proxy already parsed and put routing hints in
            //       data.target  →  go straight to field fill
            //   (b) plain scan   →  ask Odoo's nomenclature to parse +
            //       resolve routing via `parse_for_target`
            let target = ev?.detail?.data?.target || null;
            let value = ev?.detail?.data?.parsed_value;
            if (!target) {
                const nid = await _getNomenclatureId();
                if (nid) {
                    try {
                        const r = await orm.call(
                            "barcode.nomenclature",
                            "parse_for_target",
                            [[nid], String(code)],
                        );
                        if (r) {
                            target = r.target || {};
                            value = r.parsed_value
                                ?? r.base_code ?? code;
                        }
                    } catch (e) {
                        console.warn("[BarcodeHandler] parse failed:", e);
                    }
                }
            }
            // target may be:
            //   - undefined        → no routing configured, fallback
            //   - array            → multi-target, fill EVERY match
            //   - object (legacy)  → single target, treat as 1-item
            //                        array for backwards-compat
            const targets = Array.isArray(target)
                ? target
                : (target && target.model ? [target] : []);
            if (targets.length) {
                const filled = [];
                for (const t of targets) {
                    if (!t || !t.model || !t.field) continue;
                    const input = _findTargetInput(
                        t.model, t.field, t.form_xmlid);
                    if (!input) continue;
                    try {
                        _setInputValue(input,
                            value !== undefined ? value : code);
                        filled.push(`${t.model}.${t.field}`);
                    } catch (e) {
                        console.error("[BarcodeHandler] fill failed "
                                      + `for ${t.model}.${t.field}:`,
                                      e);
                    }
                }
                if (filled.length) {
                    console.log("[BarcodeHandler] routed scan to:",
                                filled.join(", "), "value=", value);
                    return;
                }
            }
            // Fallback — fire the global barcode_service event, same
            // path EE keyboard wedge + IoT box use.
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
