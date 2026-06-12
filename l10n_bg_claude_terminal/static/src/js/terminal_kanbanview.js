/** @odoo-module **/
// Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import { onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { ClaudeTerminalDialog } from "./terminal_listview";
import { buildExternalTerminalUrl } from "./terminal_utils";
import { showClaudeDispatch } from "./claude_dispatch";

// ── Patch KanbanController: add AI button logic ─────────────────

patch(KanbanController.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialogService = useService("dialog");
        this.claudeTerminalUrl = "";
        this.claudeOdooConfig = null;
        this.claudeUseExternal = false;
        this.claudeApiKey = "";

        // ── Bus listener: reload kanban when Claude sends refresh ──
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
        // Генеричен dispatch грид на всеки модел (kanban няма row-selection → ids=[]).
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
