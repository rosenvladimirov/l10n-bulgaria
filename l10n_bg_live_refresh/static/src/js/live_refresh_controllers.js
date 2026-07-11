/** @odoo-module **/
// Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
// License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import { onMounted, onWillUnmount } from "@odoo/owl";
import { FormController } from "@web/views/form/form_controller";
import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";

/**
 * Live refresh integration.
 *
 * The live_refresh service forwards bus messages as env.bus events:
 *
 *   - LIVE_REFRESH        -> generic full record/list reload
 *   - LIVE_REFRESH_FIELD  -> reload + flash the named fields (Form view)
 *   - LIVE_REFRESH_LIST   -> reload + highlight the named rows (List view)
 *
 * Each event carries { model, res_ids, mode, fields, values }.  Controllers
 * ignore events whose model does not match the view they render.
 */

function flashElement(el, cssClass = "o_live_refresh_flash") {
    if (!el) return;
    el.classList.add(cssClass);
    setTimeout(() => el.classList.remove(cssClass), 1500);
}

function flashFields(rootEl, fieldNames) {
    if (!rootEl || !fieldNames?.length) return;
    for (const name of fieldNames) {
        rootEl
            .querySelectorAll(`[name="${name}"]`)
            .forEach((el) => flashElement(el));
    }
}

function flashRow(rootEl, resId) {
    if (!rootEl || !resId) return;
    let row = rootEl.querySelector(`tr[data-id="${resId}"]`);
    if (!row) {
        for (const r of rootEl.querySelectorAll("tr.o_data_row")) {
            if (r.dataset?.id == resId) {
                row = r;
                break;
            }
        }
    }
    flashElement(row, "o_live_refresh_row_flash");
}

// ── FormController patch: field-level live refresh ──────────────────

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);

        this._onLiveRefresh = async ({ detail }) => {
            if (!detail) return;
            if (detail.model && detail.model !== this.props.resModel) return;
            const record = this.model?.root;
            if (!record) return;
            await record.load();
            this.model.notify?.();
        };

        this._onLiveRefreshField = async ({ detail }) => {
            if (!detail || !detail.model) return;
            if (detail.model !== this.props.resModel) return;
            const record = this.model?.root;
            if (!record) return;
            const currentId = record.resId;
            if (!currentId) return;
            const resIds = detail.res_ids || [];
            if (resIds.length && !resIds.includes(currentId)) return;
            // Match-by-field (proxy refresh hints): repaint only when the
            // open record's `match_field` equals `match_value` — lets the
            // hardware proxy target a record by a business key (e.g.
            // ctrl_id) without knowing its Odoo res_id. Loose == so
            // "38" (str from JSON) matches 38 (int).
            if (detail.match_field !== undefined) {
                const cur = record.data?.[detail.match_field];
                // m2o comes as [id, name]; compare on the id.
                const curVal = Array.isArray(cur) ? cur[0] : cur;
                /* eslint-disable-next-line eqeqeq */
                if (curVal != detail.match_value) return;
            }

            await record.load();
            this.model.notify?.();

            requestAnimationFrame(() => {
                const rootEl = this.rootRef?.el || document;
                const names = detail.fields?.length
                    ? detail.fields
                    : Object.keys(detail.values || {});
                flashFields(rootEl, names);
            });
        };

        onMounted(() => {
            this.env.bus.addEventListener("LIVE_REFRESH", this._onLiveRefresh);
            this.env.bus.addEventListener("LIVE_REFRESH_FIELD", this._onLiveRefreshField);
        });
        onWillUnmount(() => {
            this.env.bus.removeEventListener("LIVE_REFRESH", this._onLiveRefresh);
            this.env.bus.removeEventListener("LIVE_REFRESH_FIELD", this._onLiveRefreshField);
        });
    },
});

// ── ListController patch: new row live refresh ──────────────────────

patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);

        this._onLiveRefresh = async ({ detail }) => {
            if (!detail) return;
            if (detail.model && detail.model !== this.props.resModel) return;
            await this.model.root.load();
            this.model.notify?.();
        };

        this._onLiveRefreshList = async ({ detail }) => {
            if (!detail || !detail.model) return;
            if (detail.model !== this.props.resModel) return;

            await this.model.root.load();
            this.model.notify?.();

            requestAnimationFrame(() => {
                const rootEl = this.rootRef?.el || document;
                for (const resId of detail.res_ids || []) {
                    flashRow(rootEl, resId);
                }
            });
        };

        onMounted(() => {
            this.env.bus.addEventListener("LIVE_REFRESH", this._onLiveRefresh);
            this.env.bus.addEventListener("LIVE_REFRESH_LIST", this._onLiveRefreshList);
        });
        onWillUnmount(() => {
            this.env.bus.removeEventListener("LIVE_REFRESH", this._onLiveRefresh);
            this.env.bus.removeEventListener("LIVE_REFRESH_LIST", this._onLiveRefreshList);
        });
    },
});
