/** @odoo-module **/

/**
 * Shift state service — wraps ORM calls to l10n.bg.fiscal.shift +
 * orchestrates the open / close flows.
 *
 * The browser is the actor; this service:
 *   1. Creates the shift DB record (or reuses an active one)
 *   2. Calls the device proxy to push PLU / VAT / operators
 *   3. Updates the shift state via ORM action_mark_*
 *   4. On close — pulls Z + journal from device, persists to ORM
 */

import { registry } from "@web/core/registry";


export const shiftStateService = {
    dependencies: ["orm", "l10n_bg_external_shift.device_proxy"],

    start(env, { orm }) {
        const proxy = env.services["l10n_bg_external_shift.device_proxy"];

        return {
            // ─── reads ────────────────────────────────────────────
            async listDevices() {
                return orm.searchRead(
                    "fiscal.printer.device",
                    [["active", "=", true]],
                    ["id", "name", "host", "printer_id",
                     "connection_mode", "driver_type"],
                    { order: "name" },
                );
            },

            async findActiveShift(deviceId) {
                if (!deviceId) return null;
                const id = await orm.call(
                    "l10n.bg.fiscal.shift",
                    "find_active_shift", [deviceId],
                );
                if (!id) return null;
                const recs = await orm.read(
                    "l10n.bg.fiscal.shift",
                    [Array.isArray(id) ? id[0] : id],
                    ["id", "name", "state", "device_id",
                     "operator_user_id", "opened_at",
                     "receipt_count", "sales_total",
                     "z_number", "z_total", "push_summary"],
                );
                return recs[0] || null;
            },

            async loadShift(shiftId) {
                if (!shiftId) return null;
                const recs = await orm.read(
                    "l10n.bg.fiscal.shift",
                    [shiftId],
                    ["id", "name", "state", "device_id",
                     "operator_user_id", "opened_at", "closed_at",
                     "receipt_count", "sales_total",
                     "z_number", "z_total", "push_summary"],
                );
                return recs[0] || null;
            },

            async loadProductsAndPlu() {
                const products = await orm.searchRead(
                    "product.product",
                    [["available_in_pos", "=", true]],
                    ["id", "display_name", "default_code",
                     "lst_price", "barcode"],
                    { limit: 200, order: "display_name" },
                );
                const plus = await orm.searchRead(
                    "l10n.bg.fiscal.plu",
                    [["active", "=", true]],
                    ["id", "plu_number", "name", "price",
                     "push_state", "product_ids"],
                );
                const byProduct = {};
                for (const p of plus) {
                    for (const pid of (p.product_ids || [])) {
                        byProduct[pid] = p;
                    }
                }
                for (const prod of products) {
                    const plu = byProduct[prod.id];
                    if (!plu) {
                        prod.plu_status = "missing";
                        prod.plu_label = "";
                    } else if (plu.push_state === "pushed") {
                        prod.plu_status = "ok";
                        prod.plu_label = `PLU#${plu.plu_number}`;
                    } else if (
                        ["stale", "name_drift", "pending"]
                            .includes(plu.push_state)
                    ) {
                        prod.plu_status = "stale";
                        prod.plu_label =
                            `PLU#${plu.plu_number} (${plu.push_state})`;
                    } else {
                        prod.plu_status = "error";
                        prod.plu_label =
                            `PLU#${plu.plu_number} (${plu.push_state})`;
                    }
                }
                return { products, plusByProduct: byProduct };
            },

            // ─── orchestrators ────────────────────────────────────
            /**
             * Open a new shift on the given device.
             * @returns shift record or throws.
             */
            async openShift(device) {
                if (!device) {
                    throw new Error("Select a device first.");
                }
                const summaryLines = [];

                // 1. Create draft shift
                const ids = await orm.create(
                    "l10n.bg.fiscal.shift",
                    [{ device_id: device.id }],
                );
                const shiftId = ids[0];

                try {
                    // 2. Mark opening
                    await orm.call(
                        "l10n.bg.fiscal.shift",
                        "action_mark_opening", [shiftId],
                    );

                    // 3. Pre-flight
                    try {
                        const st = await proxy.status(device);
                        if (st && st.ok === false) {
                            throw new Error(
                                "Device not ready: "
                                + JSON.stringify(st.messages || []));
                        }
                        summaryLines.push("[status] ✓ device ready");
                    } catch (err) {
                        summaryLines.push(`[status] ✗ ${err.message}`);
                        throw err;
                    }

                    // 4. PLU bulk push (only registry items, deduped)
                    const plus = await orm.searchRead(
                        "l10n.bg.fiscal.plu",
                        [["active", "=", true]],
                        ["plu_number", "name", "price"],
                    );
                    if (plus.length) {
                        try {
                            await proxy.pushPluBulk(
                                device,
                                plus.map(p => ({
                                    plu: p.plu_number,
                                    name: p.name,
                                    price: p.price,
                                })),
                            );
                            summaryLines.push(
                                `[plu] ✓ ${plus.length} pushed`);
                        } catch (err) {
                            summaryLines.push(
                                `[plu] ✗ ${err.message}`);
                            // continue — non-fatal
                        }
                    } else {
                        summaryLines.push("[plu] — registry empty");
                    }

                    // 5. Mark open
                    await orm.call(
                        "l10n.bg.fiscal.shift",
                        "action_mark_open", [shiftId],
                        { push_summary: summaryLines.join("\n") },
                    );
                    return await this.loadShift(shiftId);
                } catch (err) {
                    await orm.call(
                        "l10n.bg.fiscal.shift",
                        "action_mark_error", [shiftId],
                        { message: String(err.message || err) },
                    ).catch(() => {});
                    throw err;
                }
            },

            async closeShift(shiftId, device) {
                if (!shiftId || !device) {
                    throw new Error("Missing shift or device.");
                }
                await orm.call(
                    "l10n.bg.fiscal.shift",
                    "action_mark_closing", [shiftId],
                );
                const summaryLines = [];
                let zData = {};
                try {
                    zData = await proxy.zReportTotals(device) || {};
                    summaryLines.push(
                        `[z] ✓ Z#${zData.z_number || "?"} `
                        + `total=${(zData.total || 0).toFixed(2)}`);
                } catch (err) {
                    summaryLines.push(`[z] ✗ ${err.message}`);
                    throw err;
                }
                // Phase 0: journal pull stub — empty list. Phase 1
                // will fetch + parse + persist receipts.
                summaryLines.push("[journal] — Phase 1 TODO");
                await orm.call(
                    "l10n.bg.fiscal.shift",
                    "action_mark_closed", [shiftId],
                    {
                        z_data: zData,
                        receipts_data: [],
                        push_summary: summaryLines.join("\n"),
                    },
                );
                return await this.loadShift(shiftId);
            },

            // ─── ad-hoc reports (without shift state change) ──────
            async fireXReport(device) {
                return await proxy.xReport(device);
            },
            async fireZReport(device) {
                return await proxy.zReport(device);
            },
        };
    },
};

registry.category("services").add(
    "l10n_bg_external_shift.shift_state", shiftStateService);
