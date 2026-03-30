/** @odoo-module **/
// Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Chatter } from "@mail/chatter/web_portal/chatter";

// ── Terminal iframe panel ──────────────────────────────────────────

class ClaudeTerminalPanel extends Component {
    static template = "l10n_bg_claude_terminal.TerminalPanel";
    static props = {
        url: { type: String },
        model: { type: String },
        resId: { type: [Number, String] },
    };

    setup() {
        this.iframeRef = useRef("iframe");
        this.state = useState({ status: "loading", expanded: false });

        onMounted(() => {
            const iframe = this.iframeRef.el;
            if (iframe) {
                iframe.addEventListener("load", () => {
                    this.state.status = "ready";
                });
                iframe.addEventListener("error", () => {
                    this.state.status = "error";
                });
            }
        });
    }

    get iframeSrc() {
        // Pass context as URL params so the terminal can pick them up
        const base = this.props.url.replace(/\/+$/, "");
        return `${base}/?model=${encodeURIComponent(this.props.model)}&res_id=${this.props.resId}`;
    }

    toggleExpand() {
        this.state.expanded = !this.state.expanded;
    }

    openNewTab() {
        window.open(this.iframeSrc, "_blank");
    }

    reload() {
        const iframe = this.iframeRef.el;
        if (iframe) {
            this.state.status = "loading";
            iframe.src = this.iframeSrc;
        }
    }
}

// ── Chatter toggle button ──────────────────────────────────────────

class ClaudeTerminalButton extends Component {
    static template = "l10n_bg_claude_terminal.TerminalButton";
    static components = { ClaudeTerminalPanel };
    static props = {
        threadModel: { type: String },
        threadId: { type: [Number, Boolean], optional: true },
    };

    setup() {
        this.user = useService("user");
        this.orm = useService("orm");
        this.state = useState({ open: false, url: "" });

        onMounted(async () => {
            // Load user's terminal URL from preferences
            const [userData] = await this.orm.read(
                "res.users", [this.user.userId], ["claude_terminal_url"]
            );
            this.state.url = userData?.claude_terminal_url || "";
        });
    }

    get hasUrl() {
        return !!this.state.url;
    }

    toggle() {
        this.state.open = !this.state.open;
    }
}

// Register on Chatter so the inherited template can resolve it
Chatter.components = { ...Chatter.components, ClaudeTerminalButton };
