/** @odoo-module **/
// Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import { Component, useState, useRef, onMounted } from "@odoo/owl";
import { Chatter } from "@mail/chatter/web_portal/chatter";
import { patch } from "@web/core/utils/patch";

// ── Terminal iframe panel ──────────────────────────────────────────

class ClaudeTerminalPanel extends Component {
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
        return `${base}/?model=${encodeURIComponent(this.props.model)}&res_id=${this.props.resId || 0}`;
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

        // Load user's terminal URL (no service dependency — use fetch)
        fetch("/web/dataset/call_kw", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                jsonrpc: "2.0", method: "call", id: 1,
                params: {
                    model: "res.users",
                    method: "read",
                    args: [odoo.session_info?.uid ? [odoo.session_info.uid] : [], ["claude_terminal_url"]],
                    kwargs: {},
                },
            }),
        })
            .then(r => r.json())
            .then(d => {
                const url = d.result?.[0]?.claude_terminal_url;
                if (url) this.claudeTerminal.url = url;
            })
            .catch(() => {});
    },

    toggleClaudeTerminal() {
        this.claudeTerminal.open = !this.claudeTerminal.open;
    },
});
