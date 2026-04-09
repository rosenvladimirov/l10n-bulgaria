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
 *   - claude_terminal/refresh_field   → CLAUDE_REFRESH_FIELD
 *   - claude_terminal/refresh_list    → CLAUDE_REFRESH_LIST
 *
 * NOTE (v16): bus_service in v16 does not have subscribe(). We use
 * addEventListener('notification', handler) and filter by type.
 *
 *   - claude_terminal/notification    → toast notification
 *       Fired by action_test_connections after running connection tests.
 *       Payload: { title, message, type, sticky }
 */
const claudeRefreshService = {
    dependencies: ["bus_service", "notification"],

    start(env, { bus_service, notification }) {
        const CHANNELS = {
            "claude_terminal/refresh": "CLAUDE_REFRESH",
            "claude_terminal/refresh_field": "CLAUDE_REFRESH_FIELD",
            "claude_terminal/refresh_list": "CLAUDE_REFRESH_LIST",
        };

        bus_service.addEventListener("notification", ({ detail: notifications }) => {
            for (const notif of notifications) {
                const busEvent = CHANNELS[notif.type];
                if (busEvent) {
                    env.bus.trigger(busEvent, notif.payload);
                } else if (notif.type === "claude_terminal/notification") {
                    notification.add(notif.payload.message || "", {
                        title: notif.payload.title || "",
                        type: notif.payload.type || "info",
                        sticky: notif.payload.sticky !== false,
                    });
                }
            }
        });
    },
};

registry.category("services").add("claude_refresh", claudeRefreshService);
