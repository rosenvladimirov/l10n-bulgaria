/** @odoo-module **/

import paymentForm from "@payment/js/payment_form";

paymentForm.include({
    async _initiatePaymentFlow(providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== "mypos") {
            return this._super(...arguments);
        }
        return this._super(...arguments);
    },
});
