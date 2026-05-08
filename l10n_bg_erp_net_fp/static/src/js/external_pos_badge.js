/** @odoo-module **/

/*
 * External POS mode badge — Phase 5 UX.
 *
 * Adds a small status pill to the POS Navbar when the current
 * pos.config has `l10n_bg_external_pos_mode = true`. The pill
 * tells cashiers that sales are entered on the fiscal device,
 * not in the Odoo POS UI.
 *
 * Click → opens a notification with the last open-time push
 * status + summary so the cashier can see if PLUs were pushed
 * successfully.
 */

import { Component } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { Navbar } from "@point_of_sale/app/navbar/navbar";

patch(Navbar.prototype, {
    get l10nBgExternalMode() {
        const sess = this.pos.session;
        // The flag is shadowed onto pos.session as a related field
        // because pos.config can't safely expose fields to the POS
        // frontend (see feedback_pos_config_load_pos_data_fields.md).
        return Boolean(sess && sess.l10n_bg_external_pos_mode);
    },

    get l10nBgPushStatus() {
        const sess = this.pos.session;
        return (sess && sess.l10n_bg_external_push_status) || "none";
    },

    get l10nBgBadgeClass() {
        const status = this.l10nBgPushStatus;
        if (status === "ok") return "bg-success";
        if (status === "partial") return "bg-warning";
        if (status === "error") return "bg-danger";
        return "bg-secondary";
    },

    get l10nBgBadgeLabel() {
        const status = this.l10nBgPushStatus;
        if (status === "ok") return _t("Device ready");
        if (status === "partial") return _t("Device: partial");
        if (status === "error") return _t("Device: error");
        return _t("Device: pending");
    },

    onL10nBgBadgeClick() {
        const sess = this.pos.session;
        const summary =
            (sess && sess.l10n_bg_external_push_summary) ||
            _t("No push has been performed yet for this session.");
        const status = this.l10nBgPushStatus;
        this.env.services.notification.add(summary, {
            title: _t("External POS mode — push status: %s", status),
            type: status === "ok" ? "success" : status === "error" ? "danger" : "warning",
            sticky: status !== "ok",
        });
    },
});
