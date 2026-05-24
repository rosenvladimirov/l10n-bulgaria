/** @odoo-module **/

/**
 * Adds a "DatecsPay" card to the standard POS payment-provider cards
 * (Adyen/Stripe/Ingenico…). The core widget's provider list is a
 * hard-coded const, so we patch the component to push our provider into
 * `state.providers` after the core load. Module `l10n_bg_erp_net_fp` is
 * already installed → the card shows "Setup" (sets use_payment_terminal=
 * 'datecs_pay'), not "Activate"/install.
 */

import { patch } from "@web/core/utils/patch";
import { PosPaymentProviderCards } from "@point_of_sale/backend/pos_payment_provider_cards/pos_payment_provider_cards";
import { onWillStart } from "@odoo/owl";

patch(PosPaymentProviderCards.prototype, {
    setup() {
        super.setup();
        onWillStart(async () => {
            if (this.state.providers.some((p) => p.selection === "datecs_pay")) {
                return;
            }
            const mods = await this.orm.searchRead(
                "ir.module.module",
                [["name", "=", "l10n_bg_erp_net_fp"]],
                ["id", "state"],
            );
            if (mods.length) {
                this.state.providers.push({
                    selection: "datecs_pay",
                    provider: "DatecsPay",
                    name: "l10n_bg_erp_net_fp",
                    id: mods[0].id,
                    state: mods[0].state, // "installed" → renders "Setup"
                });
            }
        });
    },
});
