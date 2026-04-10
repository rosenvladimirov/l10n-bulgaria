/** @odoo-module **/

import { registry } from "@web/core/registry";
import { SignSubmitDialog } from "./sign_submit_dialog";

/**
 * Client action handler for "l10n_bg_api_nra.kep_sign_submit".
 *
 * Triggered from the header button on the nra.declaration form. Opens
 * the custom SignSubmitDialog OWL component which runs the full
 * StampIT → sign → submit flow with a friendly progress timeline.
 */
async function kepSignSubmitAction(env, action) {
    const params = action.params || {};
    const declarationId = params.declaration_id;
    const declarationName = params.declaration_name || "declaration";

    if (!declarationId) {
        env.services.notification.add("No declaration ID provided", {
            type: "danger",
        });
        return false;
    }

    env.services.dialog.add(SignSubmitDialog, {
        declarationId,
        declarationName,
    });
    return false;
}

registry.category("actions").add(
    "l10n_bg_api_nra.kep_sign_submit",
    kepSignSubmitAction,
);
