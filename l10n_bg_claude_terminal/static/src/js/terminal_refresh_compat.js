/** @odoo-module **/
// Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import { registry } from "@web/core/registry";

/**
 * Backward-compat bridge.
 *
 * The generic l10n_bg_live_refresh service emits LIVE_REFRESH /
 * LIVE_REFRESH_FIELD / LIVE_REFRESH_LIST env.bus events.  Several
 * claude-terminal-specific consumers (terminal_chatter.js,
 * terminal_kanbanview.js, terminal_listview.js) still listen for the
 * historical CLAUDE_REFRESH* event names.  This thin relay keeps them
 * working without change after the refresh primitive was extracted into
 * l10n_bg_live_refresh.
 *
 * Form/List field-flash + row-highlight is now handled generically by
 * l10n_bg_live_refresh; this module no longer ships its own copy.
 */
const claudeRefreshCompat = {
    dependencies: ["live_refresh"],

    start(env) {
        const relay = (src, dst) =>
            env.bus.addEventListener(src, (ev) => env.bus.trigger(dst, ev.detail));
        relay("LIVE_REFRESH", "CLAUDE_REFRESH");
        relay("LIVE_REFRESH_FIELD", "CLAUDE_REFRESH_FIELD");
        relay("LIVE_REFRESH_LIST", "CLAUDE_REFRESH_LIST");
    },
};

registry.category("services").add("claude_refresh_compat", claudeRefreshCompat);
