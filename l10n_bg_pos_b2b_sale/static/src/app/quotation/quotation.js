import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { L10nBgB2bHeader } from "@l10n_bg_pos_b2b/app/screens/product_screen/b2b_header/b2b_header";

/**
 * „Данни на поръчката“ + оферта: запазване като чернова SO, номерът ѝ и
 * печатите в десния екран (ADR specs/pos-b2b-wholesale/0003, фаза 1).
 */
patch(L10nBgB2bHeader.prototype, {
    setup() {
        super.setup(...arguments);
        this.notification = useService("notification");
        this.state.saving = false;
    },

    get quotation() {
        const form = this.form;
        return form.sale_order_id
            ? { id: form.sale_order_id, name: form.sale_order_name, state: form.sale_order_state_label }
            : null;
    },

    get canSaveQuotation() {
        return Boolean(this.partner && this.order?.lines.length && !this.isOffline && !this.state.saving);
    },

    _l10nBgQuotationPayload() {
        const order = this.order;
        return {
            sale_order_id: this.form.sale_order_id || false,
            partner_id: this.partner.id,
            pricelist_id: order.pricelist_id?.id || false,
            client_order_ref: order.client_order_ref || false,
            shipping_date: this.shippingDate || false,
            pos_reference: order.pos_reference || order.name || false,
            form: this.form,
            lines: order.lines
                .filter((line) => !line.combo_parent_id)
                .map((line) => ({
                    product_id: line.product_id.id,
                    qty: line.qty,
                    price_unit: line.price_unit,
                    discount: line.discount || 0,
                })),
        };
    },

    async l10nBgSaveQuotation() {
        if (!this.canSaveQuotation) {
            return;
        }
        const order = this.order;
        this.state.saving = true;
        try {
            const result = await this.pos.data.call("pos.config", "l10n_bg_b2b_save_quotation", [
                [this.pos.config.id],
                this._l10nBgQuotationPayload(),
            ]);
            order.l10nBgSetForm({
                sale_order_id: result.id,
                sale_order_name: result.name,
                sale_order_state_label: result.state_label,
                sale_order_reports: result.reports,
            });
            this.notification.add(_t("Quotation %s saved.", result.name), { type: "success" });
        } catch (error) {
            this.notification.add(error?.data?.message || error?.message || String(error), {
                type: "danger",
            });
        } finally {
            this.state.saving = false;
        }
    },

    l10nBgPrint(kind) {
        const url = this.form.sale_order_reports?.[kind];
        if (!url) {
            return;
        }
        const titles = { quotation: _t("Quotation"), pro_forma: _t("Pro-forma invoice") };
        this.pos.l10nBgReport = { url, title: `${titles[kind]} ${this.form.sale_order_name || ""}` };
    },
});
