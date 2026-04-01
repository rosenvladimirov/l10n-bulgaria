/** @odoo-module **/
// Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import { Component, useState, useRef, onMounted } from "@odoo/owl";
import { Chatter } from "@mail/chatter/web_portal/chatter";
import { patch } from "@web/core/utils/patch";

// ── Terminal iframe panel ──────────────────────────────────────────

export class ClaudeTerminalPanel extends Component {
    static template = "l10n_bg_claude_terminal.TerminalPanel";
    static props = {
        url: { type: String },
        model: { type: String },
        resId: { type: [Number, Boolean], optional: true },
    };

    setup() {
        this.iframeRef = useRef("iframe");
        this.state = useState({ status: "loading", expanded: false });

        onMounted(() => {
            const iframe = this.iframeRef.el;
            if (iframe) {
                iframe.addEventListener("load", () => { this.state.status = "ready"; });
                iframe.addEventListener("error", () => { this.state.status = "error"; });
            }
        });
    }

    get iframeSrc() {
        const base = this.props.url.replace(/\/+$/, "");
        const params = new URLSearchParams();
        params.append("arg", `ODOO_ORIGIN=${window.location.origin}`);
        params.append("arg", `ODOO_MODEL=${this.props.model}`);
        params.append("arg", `ODOO_RES_ID=${this.props.resId || 0}`);
        return `${base}/?${params.toString()}`;
    }

    toggleExpand() { this.state.expanded = !this.state.expanded; }
    openNewTab() { window.open(this.iframeSrc, "_blank"); }

    reload() {
        const iframe = this.iframeRef.el;
        if (iframe) { this.state.status = "loading"; iframe.src = this.iframeSrc; }
    }
}

// Register panel on Chatter.components
Object.assign(Chatter.components, { ClaudeTerminalPanel });

// ── Patch Chatter: add terminal state + toggle method ──────────────

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        this.claudeTerminal = useState({ open: false, url: "" });

        // Load current user's terminal URL via RPC (no uid needed)
        fetch("/web/dataset/call_kw", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                jsonrpc: "2.0", method: "call", id: 1,
                params: {
                    model: "res.users",
                    method: "get_claude_terminal_url",
                    args: [],
                    kwargs: {},
                },
            }),
        })
            .then(r => r.json())
            .then(d => {
                if (d.result) this.claudeTerminal.url = d.result;
            })
            .catch(() => {});
    },

    toggleClaudeTerminal() {
        this.claudeTerminal.open = !this.claudeTerminal.open;
    },
});
