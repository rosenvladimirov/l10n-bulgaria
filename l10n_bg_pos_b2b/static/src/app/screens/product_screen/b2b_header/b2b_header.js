import { Component, useEffect, useState } from "@odoo/owl";
import { deserializeDate, serializeDate } from "@web/core/l10n/dates";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { l10nBgCreditState, l10nBgMissingLabels } from "../../../utils/b2b_checks";

const { DateTime } = luxon;

/**
 * B2B блокът над редовете на ProductScreen — горната част на продажбата
 * (SO): адреси, ценова листа, срок на плащане, срок на офертата, дата на
 * доставка, търговец, склад, референция, обща отстъпка, бележка
 * (ADR specs/pos-b2b-wholesale/0002). Изборът се пази в
 * `l10n_bg_b2b_form` на поръчката; редовете, цените и данъците остават
 * на ядрото.
 */
export class L10nBgB2bHeader extends Component {
    static template = "l10n_bg_pos_b2b.B2bHeader";
    static props = {};

    setup() {
        this.pos = usePos();
        this.state = useState({ options: null });
        useEffect(
            (partnerId) => {
                this.loadOptions(partnerId);
            },
            () => [this.partner?.id]
        );
    }

    get order() {
        return this.pos.getOrder();
    }

    get partner() {
        return this.order?.getPartner();
    }

    get form() {
        return this.order?.l10nBgForm || {};
    }

    get options() {
        return this.state.options || {};
    }

    get pricelists() {
        return this.pos.config.availablePricelists || [];
    }

    /** Адресите: от сървъра, а офлайн — само самият клиент. */
    addresses(kind) {
        const list = this.options[kind];
        if (list?.length) {
            return list;
        }
        return this.partner ? [{ id: this.partner.id, name: this.partner.name, address: "" }] : [];
    }

    async loadOptions(partnerId) {
        this.state.options = null;
        if (!partnerId || this.isOffline) {
            return;
        }
        const order = this.order;
        let options;
        try {
            options = await this.pos.data.call("pos.config", "l10n_bg_b2b_form_options", [
                [this.pos.config.id],
                partnerId,
            ]);
        } catch {
            // Без връзка: остават подразбиращите се стойности на клиента.
            return;
        }
        if (!order || order !== this.order || this.partner?.id !== partnerId) {
            return;
        }
        this.state.options = options;
        // Подразбиращите се стойности — само за още непопълнените полета.
        const defaults = options.defaults || {};
        const form = order.l10nBgForm;
        const values = {};
        for (const key of [
            "invoice_partner_id",
            "shipping_partner_id",
            "payment_term_id",
            "salesperson_id",
            "warehouse_id",
        ]) {
            if (!form[key] && defaults[key]) {
                values[key] = defaults[key];
            }
        }
        if (!form.validity_date && defaults.validity_days > 0) {
            values.validity_date = serializeDate(
                DateTime.now().plus({ days: defaults.validity_days })
            );
        }
        if (Object.keys(values).length) {
            order.l10nBgSetForm(values);
        }
    }

    /** Свитият блок: ценова листа · срок · дата на доставка · референция. */
    get summary() {
        const order = this.order;
        const form = this.form;
        const term = (this.options.payment_terms || []).find((t) => t.id === form.payment_term_id);
        return [
            order.pricelist_id?.display_name || order.pricelist_id?.name,
            term?.name || this.partner?.l10n_bg_pos_payment_term,
            this.shippingDate,
            order.client_order_ref,
        ]
            .filter(Boolean)
            .join(" · ");
    }

    get missing() {
        return l10nBgMissingLabels(this.partner);
    }

    get credit() {
        return this.order ? l10nBgCreditState(this.pos, this.order) : null;
    }

    get creditClass() {
        const credit = this.credit;
        if (!credit || !credit.limit) {
            return "";
        }
        if (credit.used + credit.onAccount > credit.limit) {
            return "text-danger";
        }
        return credit.used > credit.limit * 0.8 ? "text-warning" : "text-success";
    }

    get isOffline() {
        return Boolean(this.pos.data?.network?.offline);
    }

    get shippingDate() {
        const date = this.order?.shipping_date;
        if (!date) {
            return "";
        }
        return typeof date === "string" ? date.slice(0, 10) : serializeDate(date);
    }

    formatCurrency(amount) {
        return this.env.utils.formatCurrency(amount || 0);
    }

    /** Акордеон: отворени са или данните на поръчката, или редовете. */
    get expanded() {
        return this.order?.l10nBgPanel === "header";
    }

    toggleExpanded() {
        this.order.l10nBgPanel = this.expanded ? "lines" : "header";
    }

    onChangeForm(key, ev, numeric = true) {
        const raw = ev.target.value;
        this.order.l10nBgSetForm({ [key]: numeric ? parseInt(raw) || false : raw || false });
    }

    onChangePricelist(ev) {
        const id = parseInt(ev.target.value);
        const pricelist = this.pricelists.find((p) => p.id === id) || false;
        this.pos.selectPricelist(pricelist);
    }

    onChangeShippingDate(ev) {
        const value = ev.target.value;
        this.order.setShippingDate(value ? deserializeDate(value) : false);
    }

    onChangeReference(ev) {
        this.order.client_order_ref = ev.target.value || false;
    }
}
