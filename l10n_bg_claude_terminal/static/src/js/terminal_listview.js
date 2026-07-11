/** @odoo-module **/
// Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
// License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import { Component, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { buildExternalTerminalUrl } from "./terminal_utils";
import { showClaudeDispatch } from "./claude_dispatch";

// ── Dialog with terminal iframe ─────────────────────────────────

export class ClaudeTerminalDialog extends Component {
    static template = "l10n_bg_claude_terminal.TerminalDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        url: { type: String, optional: true },
        model: { type: String, optional: true },
        resId: { type: [Number, Boolean], optional: true },
        focus: { type: String, optional: true },
        odooConfig: { type: Object, optional: true },
        useExternal: { type: Boolean, optional: true },
        apiKey: { type: String, optional: true },
    };

    get iframeSrc() {
        if (this.props.useExternal) {
            return buildExternalTerminalUrl(
                this.props.url, this.props.odooConfig,
                this.props.apiKey || "", this.props.model,
                this.props.resId || 0, "", this.props.focus || "",
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
        params.append("arg", `ODOO_RES_ID=${this.props.resId || 0}`);
        if (this.props.focus) {
            params.append("arg", `ODOO_FOCUS=${this.props.focus}`);
        }
        return `${base}/?${params.toString()}`;
    }
}

// ── Patch ListController: add AI button logic ────────────────────

patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialogService = useService("dialog");
        this.claudeTerminalUrl = "";
        this.claudeOdooConfig = null;
        this.claudeUseExternal = false;
        this.claudeApiKey = "";

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
                const result = await rpc("/web/dataset/call_kw", {
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
                }
            } catch {
                // MCP config not available
            }
        });
    },

    async openClaudeTerminal() {
        // Показва генеричния dispatch грид (Terminal + Ask me + skills за модела),
        // вместо да отваря терминала директно. Гридът работи на ВСЕКИ модел.
        const selected = (this.model?.root?.selection || [])
            .map((r) => r.resId).filter(Boolean);
        const openTerminal = (focus) => {
            this.dialogService.add(ClaudeTerminalDialog, {
                url: this.claudeTerminalUrl,
                model: this.props.resModel,
                resId: selected[0] || 0,
                focus: focus || "",
                odooConfig: this.claudeOdooConfig,
                useExternal: this.claudeUseExternal,
                apiKey: this.claudeApiKey,
            });
        };
        await showClaudeDispatch(this.dialogService, {
            resModel: this.props.resModel,
            ids: selected,
            env: this.env,
            openTerminal,
        });
    },
});
