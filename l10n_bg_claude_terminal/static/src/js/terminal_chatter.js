/** @odoo-module **/
// Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { Chatter } from "@mail/chatter/web_portal/chatter";
import { patch } from "@web/core/utils/patch";
import { buildExternalTerminalUrl } from "./terminal_utils";

// ── Terminal iframe panel ──────────────────────────────────────────

export class ClaudeTerminalPanel extends Component {
    static template = "l10n_bg_claude_terminal.TerminalPanel";
    static props = {
        url: { type: String },
        model: { type: String },
        resId: { type: [Number, Boolean], optional: true },
        odooConfig: { type: Object, optional: true },
        useExternal: { type: Boolean, optional: true },
        apiKey: { type: String, optional: true },
        theme: { type: String, optional: true },
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
        if (this.props.useExternal) {
            // External Docker terminal — with API_KEY auth
            return buildExternalTerminalUrl(
                this.props.url, this.props.odooConfig,
                this.props.apiKey || "", this.props.model, this.props.resId,
                this.props.theme || "",
            );
        }
        // Local host terminal — old format, no API_KEY
        const base = this.props.url.replace(/\/+$/, "");
        const odoo = this.props.odooConfig || {};
        const params = new URLSearchParams();
        params.append("arg", `ODOO_ORIGIN=${odoo.url || window.location.origin}`);
        params.append("arg", `ODOO_DB=${odoo.db || ""}`);
        params.append("arg", `ODOO_USER=${odoo.username || ""}`);
        params.append("arg", `ODOO_PROTOCOL=${odoo.protocol || "xmlrpc"}`);
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
        this.claudeTerminal = useState({
            open: false, url: "", odooConfig: null,
            useExternal: false, apiKey: "", theme: "",
        });

        // ── Bus listener: reload form record when Claude sends refresh ──
        this._onClaudeRefresh = ({ detail }) => {
            const model = this.props.threadModel;
            if (!detail.model || detail.model === model) {
                if (this.props.webRecord) {
                    this.props.webRecord.load();
                }
            }
        };
        onMounted(() => {
            this.env.bus.addEventListener("CLAUDE_REFRESH", this._onClaudeRefresh);
        });
        onWillUnmount(() => {
            this.env.bus.removeEventListener("CLAUDE_REFRESH", this._onClaudeRefresh);
        });

        // Load current user's MCP config via RPC
        fetch("/web/dataset/call_kw", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                jsonrpc: "2.0", method: "call", id: 1,
                params: {
                    model: "res.users",
                    method: "get_claude_mcp_config",
                    args: [],
                    kwargs: {},
                },
            }),
        })
            .then(r => r.json())
            .then(d => {
                if (d.result) {
                    this.claudeTerminal.url = d.result.terminal_url || "";
                    this.claudeTerminal.odooConfig = d.result.odoo || null;
                    this.claudeTerminal.useExternal = d.result.use_external || false;
                    this.claudeTerminal.apiKey = d.result.api_key || "";
                    this.claudeTerminal.theme = d.result.theme || "";
                }
            })
            .catch(() => {});
    },

    toggleClaudeTerminal() {
        this.claudeTerminal.open = !this.claudeTerminal.open;
    },
});
