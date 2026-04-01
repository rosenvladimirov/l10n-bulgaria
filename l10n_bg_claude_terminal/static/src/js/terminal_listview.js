/** @odoo-module **/
// Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import { Component, onWillStart } from "@odoo/owl";
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
    };

    get iframeSrc() {
        const base = (this.props.url || "").replace(/\/+$/, "");
        const params = new URLSearchParams();
        params.append("arg", `ODOO_ORIGIN=${window.location.origin}`);
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

        onWillStart(async () => {
            try {
                const result = await rpc("/web/dataset/call_kw", {
                    model: "res.users",
                    method: "get_claude_terminal_url",
                    args: [],
                    kwargs: {},
                });
                if (result) {
                    this.claudeTerminalUrl = result;
                }
            } catch {
                // Terminal URL not configured — button will show config hint
            }
        });
    },

    openClaudeTerminal() {
        this.dialogService.add(ClaudeTerminalDialog, {
            url: this.claudeTerminalUrl,
            model: this.props.resModel,
        });
    },
});
