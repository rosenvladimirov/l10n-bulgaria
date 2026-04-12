/** @odoo-module **/
// Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import { onMounted, onWillUnmount } from "@odoo/owl";
import { FormController } from "@web/views/form/form_controller";
import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";

/**
 * Live refresh integration for Claude MCP write/create events.
 *
 * When the MCP server executes odoo_write / odoo_create, it calls
 * notify_claude_refresh_field / notify_claude_refresh_list on
 * res.users.  Those methods send bus notifications that the refresh
 * service forwards as env.bus events:
 *
 *   - CLAUDE_REFRESH_FIELD → handled here by FormController patch.
 *     If the current record matches (model + res_id), reload the
 *     record and flash the changed fields.
 *
 *   - CLAUDE_REFRESH_LIST → handled here by ListController patch.
 *     If the current model matches, reload the list and highlight
 *     the new row(s).
 */

// ── Flash helper: highlight a DOM element briefly ───────────────────

function flashElement(el, cssClass = "o_claude_flash") {
    if (!el) return;
    el.classList.add(cssClass);
    setTimeout(() => el.classList.remove(cssClass), 1500);
}

function flashFields(rootEl, fieldNames) {
    if (!rootEl || !fieldNames?.length) return;
    for (const name of fieldNames) {
        const els = rootEl.querySelectorAll(`[name="${name}"]`);
        els.forEach((el) => flashElement(el));
    }
}

function flashRow(rootEl, resId) {
    if (!rootEl || !resId) return;
    // Odoo list rows have data-id or are keyed by resId in different ways.
    // Try a few selectors.
    let row = rootEl.querySelector(`tr[data-id="${resId}"]`);
    if (!row) {
        const rows = rootEl.querySelectorAll("tr.o_data_row");
        for (const r of rows) {
            if (r.dataset?.id == resId) {
                row = r;
                break;
            }
        }
    }
    flashElement(row, "o_claude_row_flash");
}

// ── FormController patch: field-level live refresh ─────────────────

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);

        this._onClaudeRefreshField = async ({ detail }) => {
            console.log("🔄 FormController: CLAUDE_REFRESH_FIELD event", detail);
            if (!detail || !detail.model) return;
            const record = this.model?.root;
            if (!record) return;
            if (detail.model !== this.props.resModel) return;
            // Match if any of the changed res_ids is the currently open record
            const currentId = record.resId;
            if (!currentId) return;
            const resIds = detail.res_ids || [];
            if (!resIds.includes(currentId)) return;

            // Reload the record so new field values are fetched from DB
            await record.load();
            this.model.notify?.();

            // Flash the updated fields on next animation frame
            requestAnimationFrame(() => {
                const rootEl = this.rootRef?.el || document;
                flashFields(rootEl, Object.keys(detail.values || {}));
            });
        };

        onMounted(() => {
            this.env.bus.addEventListener(
                "CLAUDE_REFRESH_FIELD",
                this._onClaudeRefreshField,
            );
        });
        onWillUnmount(() => {
            this.env.bus.removeEventListener(
                "CLAUDE_REFRESH_FIELD",
                this._onClaudeRefreshField,
            );
        });
    },
});

// ── ListController patch: new row live refresh ──────────────────────

patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);

        this._onClaudeRefreshList = async ({ detail }) => {
            console.log("🔄 ListController: CLAUDE_REFRESH_LIST event", detail);
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
            this.env.bus.addEventListener(
                "CLAUDE_REFRESH_LIST",
                this._onClaudeRefreshList,
            );
        });
        onWillUnmount(() => {
            this.env.bus.removeEventListener(
                "CLAUDE_REFRESH_LIST",
                this._onClaudeRefreshList,
            );
        });
    },
});
