/** @odoo-module **/
// Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
// License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const STATE_META = {
    indexed: { label: "Indexed", cls: "text-bg-success" },
    stale: { label: "Stale", cls: "text-bg-warning" },
    missing: { label: "Not indexed", cls: "text-bg-secondary" },
    draft: { label: "Pending", cls: "text-bg-info" },
    tokenized: { label: "Tokenized", cls: "text-bg-info" },
    error: { label: "Error", cls: "text-bg-danger" },
};

export class AiTokenizerStatusWidget extends Component {
    static template = "l10n_bg_claude_terminal.AiTokenizerStatus";
    static props = { ...Component.props, record: { type: Object, optional: true } };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            loaded: false,
            enabled: false,
            status: "missing",
            tokenCount: 0,
            busy: false,
            error: null,
        });
        onWillStart(() => this.reload());
    }

    get recordInfo() {
        const rec = this.props.record;
        if (!rec || !rec.resModel || !rec.resId) {
            return null;
        }
        return { model: rec.resModel, resId: rec.resId };
    }

    get badge() {
        return STATE_META[this.state.status] || STATE_META.missing;
    }

    async reload() {
        const info = this.recordInfo;
        if (!info) {
            this.state.loaded = true;
            return;
        }
        try {
            const res = await this.orm.call(
                "ai.composite.document", "get_status_for_record",
                [info.model, info.resId, "form"],
            );
            this.state.enabled = !!res.enabled;
            this.state.status = res.state || "missing";
            this.state.tokenCount = res.token_count || 0;
            this.state.error = res.error || null;
        } catch (err) {
            this.state.error = String(err && err.message ? err.message : err);
        } finally {
            this.state.loaded = true;
        }
    }

    async onTokenizeNow() {
        const info = this.recordInfo;
        if (!info || this.state.busy) return;
        this.state.busy = true;
        try {
            const res = await this.orm.call(
                "ai.view.registry", "tokenize_record",
                [info.model, info.resId, "form"],
            );
            if (res && res.ok) {
                this.state.status = res.state || "indexed";
                this.state.tokenCount = res.token_count || 0;
                this.state.error = null;
                this.notification.add(`Tokenized (${res.token_count || 0} tokens)`, {
                    type: "success",
                });
            } else {
                this.state.error = (res && res.error) || "Unknown error";
                this.state.status = "error";
                this.notification.add(this.state.error, { type: "danger" });
            }
        } catch (err) {
            this.state.error = String(err && err.message ? err.message : err);
            this.state.status = "error";
            this.notification.add(this.state.error, { type: "danger" });
        } finally {
            this.state.busy = false;
        }
    }
}

registry.category("view_widgets").add("ai_tokenizer_status", {
    component: AiTokenizerStatusWidget,
});
