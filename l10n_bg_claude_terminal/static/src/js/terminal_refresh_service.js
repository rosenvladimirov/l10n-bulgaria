/** @odoo-module **/
// Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import { registry } from "@web/core/registry";

/**
 * Listens for "claude_terminal/refresh" bus notifications and reloads
 * the current view. Works with list, form, kanban — any view backed
 * by RelationalModel.
 *
 * Flow:
 *   Claude (MCP) → odoo_refresh tool → bus.bus._sendone() →
 *   WebSocket → this service → env.bus "CLAUDE_REFRESH" →
 *   patched controllers call model.root.load()
 */
const claudeRefreshService = {
    dependencies: ["bus_service"],

    start(env, { bus_service }) {
        bus_service.subscribe("claude_terminal/refresh", (payload) => {
            env.bus.trigger("CLAUDE_REFRESH", payload);
        });
    },
};

registry.category("services").add("claude_refresh", claudeRefreshService);
