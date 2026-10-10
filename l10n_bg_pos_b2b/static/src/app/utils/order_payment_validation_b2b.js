import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { ask } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { l10nBgB2bBlockers, l10nBgB2bWarnings, l10nBgCreditState } from "./b2b_checks";

patch(OrderPaymentValidation.prototype, {
    /**
     * Режим `warn`: касиерът потвърждава липсите в данните и превишения
     * кредит. Потвърждението се записва върху поръчката ПРЕДИ push-а и
     * стига до chatter-а при синхронизацията (котвата §21).
     */
    async askBeforeValidation() {
        const result = await super.askBeforeValidation(...arguments);
        if (result === false) {
            return false;
        }
        const order = this.order;
        if (!order.l10nBgIsB2b || l10nBgB2bBlockers(this.pos, order).length) {
            // Твърдото спиране е в isOrderValid — без излишно потвърждение
            return result;
        }
        const warnings = l10nBgB2bWarnings(this.pos, order);
        if (!warnings.length) {
            return result;
        }
        const confirmed = await ask(this.pos.dialog, {
            title: _t("Wholesale check"),
            body: warnings.map((w) => w.text).join("\n"),
            confirmLabel: _t("Continue"),
            cancelLabel: _t("Back"),
        });
        if (!confirmed) {
            return false;
        }
        const dataWarnings = warnings.filter((w) => w.kind === "data");
        if (dataWarnings.length) {
            order.l10n_bg_guard_ack = dataWarnings.map((w) => w.text).join(" ");
        }
        if (warnings.some((w) => w.kind === "credit")) {
            const credit = l10nBgCreditState(this.pos, order);
            order.l10n_bg_credit_override_by = this.pos.user;
            order.l10n_bg_credit_override_reason = _t(
                "Confirmed at the cash register: limit %(limit)s, used %(used)s, order %(amount)s",
                {
                    limit: this.pos.env.utils.formatCurrency(credit.limit),
                    used: this.pos.env.utils.formatCurrency(credit.used),
                    amount: this.pos.env.utils.formatCurrency(credit.onAccount),
                }
            );
        }
        return result;
    },

    /** Твърдите гардове на едро — преди плащането, не при sync (§10.1). */
    async isOrderValid(isForceValidate) {
        const order = this.order;
        const blockers = l10nBgB2bBlockers(this.pos, order);
        if (blockers.length) {
            this.pos.dialog.add(AlertDialog, {
                title: blockers[0].title,
                body: blockers.map((b) => b.body).join("\n\n"),
            });
            return false;
        }
        if (order.l10nBgIsB2b) {
            // Признакът е върху модела преди push (котвата §8.2)
            order.l10n_bg_is_b2b = true;
        }
        return super.isOrderValid(...arguments);
    },
});
