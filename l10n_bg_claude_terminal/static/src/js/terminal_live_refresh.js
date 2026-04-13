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
 * NOTE (v16): FormController stores rootRef as a local variable in setup(),
 * not on `this`. flashFields/flashRow fall back to `document` which is fine.
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

patch(FormController.prototype, "l10n_bg_claude_terminal.form_live_refresh", {
    setup() {
        this._super(...arguments);

        this._onClaudeRefreshField = async ({ detail }) => {
            if (!detail || !detail.model) return;
            const record = this.model?.root;
            if (!record) return;
            if (detail.model !== this.props.resModel) return;
            const currentId = record.resId;
            if (!currentId) return;
            const resIds = detail.res_ids || [];
            if (!resIds.includes(currentId)) return;

            await record.load();
            this.model.notify?.();

            requestAnimationFrame(() => {
                // v16: this.rootRef is not on the instance, fall back to document
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

patch(ListController.prototype, "l10n_bg_claude_terminal.list_live_refresh", {
    setup() {
        this._super(...arguments);

        this._onClaudeRefreshList = async ({ detail }) => {
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
