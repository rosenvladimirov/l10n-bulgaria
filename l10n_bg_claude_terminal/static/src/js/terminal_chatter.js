/** @odoo-module **/
// Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { ChatterTopbar } from "@mail/components/chatter_topbar/chatter_topbar";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
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
        anthropicApiKey: { type: String, optional: true },
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
            return buildExternalTerminalUrl(
                this.props.url, this.props.odooConfig,
                this.props.apiKey || "", this.props.model, this.props.resId,
                this.props.theme || "", this.props.anthropicApiKey || "",
            );
        }
        const base = this.props.url.replace(/\/+$/, "");
        const odoo = this.props.odooConfig || {};
        const params = new URLSearchParams();
        params.append("arg", `ODOO_ORIGIN=${odoo.url || window.location.origin}`);
        params.append("arg", `ODOO_DB=${odoo.db || ""}`);
        params.append("arg", `ODOO_USER=${odoo.username || ""}`);
        params.append("arg", `ODOO_PROTOCOL=${odoo.protocol || "xmlrpc"}`);
        params.append("arg", `ODOO_MODEL=${this.props.model}`);
        params.append("arg", `ODOO_RES_ID=${this.props.resId || 0}`);
        if (this.props.anthropicApiKey) {
            params.append("arg", `ANTHROPIC_API_KEY=${this.props.anthropicApiKey}`);
        }
        return `${base}/?${params.toString()}`;
    }

    toggleExpand() { this.state.expanded = !this.state.expanded; }
    openNewTab() { window.open(this.iframeSrc, "_blank"); }

    reload() {
        const iframe = this.iframeRef.el;
        if (iframe) { this.state.status = "loading"; iframe.src = this.iframeSrc; }
    }
}

// Register panel on ChatterTopbar.components
ChatterTopbar.components = Object.assign(ChatterTopbar.components || {}, {
    ClaudeTerminalPanel,
});

// ── Patch ChatterTopbar: add terminal state + toggle method ────────
// NOTE (v16):
//   - patch() requires 3 args: (obj, patchName, patchValue)
//   - model/resId accessed via this.props.record.chatter.thread
//   - reload parent view via this.props.record.chatter.reloadParentView()
//   - RPC via useService("rpc")

patch(ChatterTopbar.prototype, "l10n_bg_claude_terminal.chatter", {
    setup() {
        this._super(...arguments);
        this.rpc = useService("rpc");
        this.claudeTerminal = useState({
            open: false, url: "", odooConfig: null,
            useExternal: false, apiKey: "", anthropicApiKey: "", theme: "",
        });

        // ── Bus listener: reload form record when Claude sends refresh ──
        this._onClaudeRefresh = ({ detail }) => {
            const model = this.props.record?.chatter?.thread?.model;
            if (!detail.model || detail.model === model) {
                this.props.record?.chatter?.reloadParentView?.();
            }
        };
        onMounted(() => {
            this.env.bus.addEventListener("CLAUDE_REFRESH", this._onClaudeRefresh);
        });
        onWillUnmount(() => {
            this.env.bus.removeEventListener("CLAUDE_REFRESH", this._onClaudeRefresh);
        });

        // Load current user's MCP config via RPC
        this.rpc("/web/dataset/call_kw", {
            model: "res.users",
            method: "get_claude_mcp_config",
            args: [],
            kwargs: {},
        })
            .then(d => {
                if (d) {
                    this.claudeTerminal.url = d.terminal_url || "";
                    this.claudeTerminal.odooConfig = d.odoo || null;
                    this.claudeTerminal.useExternal = d.use_external || false;
                    this.claudeTerminal.apiKey = d.api_key || "";
                    this.claudeTerminal.anthropicApiKey = d.anthropic_api_key || "";
                    this.claudeTerminal.theme = d.theme || "";
                }
            })
            .catch(() => {});
    },

    toggleClaudeTerminal() {
        this.claudeTerminal.open = !this.claudeTerminal.open;
    },

    // Getters for model/resId from the messaging model
    get claudeModel() {
        return this.props.record?.chatter?.thread?.model || "";
    },

    get claudeResId() {
        return this.props.record?.chatter?.thread?.id || 0;
    },
});
