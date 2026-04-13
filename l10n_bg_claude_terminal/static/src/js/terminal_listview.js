/** @odoo-module **/
// Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import { Component, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { buildExternalTerminalUrl } from "./terminal_utils";

// ── Dialog with terminal iframe ─────────────────────────────────

export class ClaudeTerminalDialog extends Component {
    static template = "l10n_bg_claude_terminal.TerminalDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        url: { type: String, optional: true },
        model: { type: String, optional: true },
        odooConfig: { type: Object, optional: true },
        useExternal: { type: Boolean, optional: true },
        apiKey: { type: String, optional: true },
        anthropicApiKey: { type: String, optional: true },
    };

    get iframeSrc() {
        if (this.props.useExternal) {
            return buildExternalTerminalUrl(
                this.props.url, this.props.odooConfig,
                this.props.apiKey || "", this.props.model, 0,
                "", this.props.anthropicApiKey || "",
            );
        }
        const base = (this.props.url || "").replace(/\/+$/, "");
        const odoo = this.props.odooConfig || {};
        const params = new URLSearchParams();
        params.append("arg", `ODOO_ORIGIN=${odoo.url || window.location.origin}`);
        params.append("arg", `ODOO_DB=${odoo.db || ""}`);
        params.append("arg", `ODOO_USER=${odoo.username || ""}`);
        params.append("arg", `ODOO_PROTOCOL=${odoo.protocol || "xmlrpc"}`);
        params.append("arg", `ODOO_MODEL=${this.props.model || ""}`);
        params.append("arg", "ODOO_RES_ID=0");
        if (this.props.anthropicApiKey) {
            params.append("arg", `ANTHROPIC_API_KEY=${this.props.anthropicApiKey}`);
        }
        return `${base}/?${params.toString()}`;
    }
}

// ── Patch ListController: add AI button logic ────────────────────
// NOTE (v16): use this.rpc = useService("rpc") — no module-level rpc import

patch(ListController.prototype, "l10n_bg_claude_terminal.list", {
    setup() {
        this._super(...arguments);
        // v16: ListController already sets this.rpc = useService("rpc") in its
        // own setup, so it's available after this._super().
        this.dialogService = useService("dialog");
        this.claudeTerminalUrl = "";
        this.claudeOdooConfig = null;
        this.claudeUseExternal = false;
        this.claudeApiKey = "";
        this.claudeAnthropicApiKey = "";

        // ── Bus listener: reload list when Claude sends refresh ──
        this._onClaudeRefresh = ({ detail }) => {
            if (!detail.model || detail.model === this.props.resModel) {
                this.model.root.load();
            }
        };
        onMounted(() => {
            this.env.bus.addEventListener("CLAUDE_REFRESH", this._onClaudeRefresh);
        });
        onWillUnmount(() => {
            this.env.bus.removeEventListener("CLAUDE_REFRESH", this._onClaudeRefresh);
        });

        onWillStart(async () => {
            try {
                const result = await this.rpc("/web/dataset/call_kw", {
                    model: "res.users",
                    method: "get_claude_mcp_config",
                    args: [],
                    kwargs: {},
                });
                if (result) {
                    this.claudeTerminalUrl = result.terminal_url || "";
                    this.claudeOdooConfig = result.odoo || null;
                    this.claudeUseExternal = result.use_external || false;
                    this.claudeApiKey = result.api_key || "";
                    this.claudeAnthropicApiKey = result.anthropic_api_key || "";
                }
            } catch {
                // MCP config not available
            }
        });
    },

    openClaudeTerminal() {
        this.dialogService.add(ClaudeTerminalDialog, {
            url: this.claudeTerminalUrl,
            model: this.props.resModel,
            odooConfig: this.claudeOdooConfig,
            useExternal: this.claudeUseExternal,
            apiKey: this.claudeApiKey,
            anthropicApiKey: this.claudeAnthropicApiKey,
        });
    },
});
