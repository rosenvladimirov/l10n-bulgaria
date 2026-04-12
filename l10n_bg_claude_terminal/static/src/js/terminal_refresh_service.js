/** @odoo-module **/
// Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import { registry } from "@web/core/registry";

/**
 * Listens for Claude terminal bus notifications and forwards them as
 * env.bus events so patched controllers can react.
 *
 * Supported channels:
 *   - claude_terminal/refresh         → CLAUDE_REFRESH
 *       Full record/list reload (fired by odoo_refresh MCP tool).
 *
 *   - claude_terminal/refresh_field   → CLAUDE_REFRESH_FIELD
 *       Field-level live update (fired after MCP odoo_write).
 *       Patched FormController reloads the record and flashes the
 *       changed fields when model + res_id match.
 *
 *   - claude_terminal/refresh_list    → CLAUDE_REFRESH_LIST
 *       New row live notification (fired after MCP odoo_create).
 *       Patched ListController reloads the list and highlights the
 *       new row when model matches.
 *
 */
const claudeRefreshService = {
    dependencies: ["bus_service"],

    start(env, { bus_service }) {
        bus_service.subscribe("claude_terminal/refresh", (payload) => {
            env.bus.trigger("CLAUDE_REFRESH", payload);
        });
        bus_service.subscribe("claude_terminal/refresh_field", (payload) => {
            env.bus.trigger("CLAUDE_REFRESH_FIELD", payload);
        });
        bus_service.subscribe("claude_terminal/refresh_list", (payload) => {
            env.bus.trigger("CLAUDE_REFRESH_LIST", payload);
        });
    },
};

registry.category("services").add("claude_refresh", claudeRefreshService);
