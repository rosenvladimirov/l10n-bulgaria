/** @odoo-module **/
// Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { Chatter } from "@mail/chatter/web_portal/chatter";

// ── Terminal iframe panel ──────────────────────────────────────────

class ClaudeTerminalPanel extends Component {
    static template = "l10n_bg_claude_terminal.TerminalPanel";
    static props = {
        url: { type: String },
        model: { type: String },
        resId: { type: [Number, String] },
    };

    setup() {
        this.iframeRef = useRef("iframe");
        this.state = useState({ status: "loading", expanded: false });

        onMounted(() => {
            const iframe = this.iframeRef.el;
            if (iframe) {
                iframe.addEventListener("load", () => {
                    this.state.status = "ready";
                });
                iframe.addEventListener("error", () => {
                    this.state.status = "error";
                });
            }
        });
    }

    get iframeSrc() {
        // Pass context as URL params so the terminal can pick them up
        const base = this.props.url.replace(/\/+$/, "");
        return `${base}/?model=${encodeURIComponent(this.props.model)}&res_id=${this.props.resId}`;
    }

    toggleExpand() {
        this.state.expanded = !this.state.expanded;
    }

    openNewTab() {
        window.open(this.iframeSrc, "_blank");
    }

    reload() {
        const iframe = this.iframeRef.el;
        if (iframe) {
            this.state.status = "loading";
            iframe.src = this.iframeSrc;
        }
    }
}

// ── Chatter toggle button ──────────────────────────────────────────

class ClaudeTerminalButton extends Component {
    static template = "l10n_bg_claude_terminal.TerminalButton";
    static components = { ClaudeTerminalPanel };
    static props = {
        threadModel: { type: String },
        threadId: { type: [Number, Boolean], optional: true },
    };

    setup() {
        this.state = useState({ open: false, url: "" });

        onMounted(() => {
            // Fetch user's terminal URL via JSON-RPC (no service dependency)
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
                    if (url) this.state.url = url;
                })
                .catch(() => {});
        });
    }

    toggle() {
        this.state.open = !this.state.open;
    }
}

// Register on Chatter (use Object.assign — same pattern as chatter_patch.js)
Object.assign(Chatter.components, { ClaudeTerminalButton });
