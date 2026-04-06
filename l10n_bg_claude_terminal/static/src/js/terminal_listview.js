/** @odoo-module **/
// Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import { Component, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

// ── Dialog with terminal iframe ─────────────────────────────────

export class ClaudeTerminalDialog extends Component {
    static template = "l10n_bg_claude_terminal.TerminalDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        url: { type: String, optional: true },
        model: { type: String, optional: true },
        odooConfig: { type: Object, optional: true },
    };

    get iframeSrc() {
        const base = (this.props.url || "").replace(/\/+$/, "");
        const odoo = this.props.odooConfig || {};
        const params = new URLSearchParams();
        params.append("arg", `ODOO_ORIGIN=${odoo.url || window.location.origin}`);
        params.append("arg", `ODOO_DB=${odoo.db || ""}`);
        params.append("arg", `ODOO_USER=${odoo.username || ""}`);
        params.append("arg", `ODOO_PROTOCOL=${odoo.protocol || "xmlrpc"}`);
        params.append("arg", `ODOO_MODEL=${this.props.model || ""}`);
        params.append("arg", "ODOO_RES_ID=0");
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
        });
    },
});
