import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { rpc } from '@web/core/network/rpc';

// Checkout: отметката „Искам фактура“ — пази се в поръчката; ако адресът за
// фактура няма фирма, отваря формата за него
export class InvoiceRequest extends Interaction {
    static selector = '#l10n_bg_invoice_requested';
    dynamicContent = {
        _root: { 't-on-change': this.onChange },
    };

    async onChange() {
        const result = await this.waitFor(
            rpc('/shop/l10n_bg/invoice_request', { requested: this.el.checked })
        );
        if (this.el.checked && result && result.billing_url) {
            window.location = result.billing_url;
        }
    }
}

// Формата за адрес: фирмата, ДДС номерът и ЕИК се виждат само при поискана фактура
export class InvoiceRequestAddress extends Interaction {
    static selector = '#o_l10n_bg_invoice_requested';
    dynamicContent = {
        _root: { 't-on-change': this.toggle },
    };

    start() {
        this.toggle();
    }

    toggle() {
        const form = this.el.form;
        if (!form) {
            return;
        }
        for (const id of ['company_name_div', 'div_vat', 'div_l10n_bg_uic']) {
            const div = form.querySelector('#' + id);
            if (div) {
                div.classList.toggle('d-none', !this.el.checked);
            }
        }
    }
}

registry
    .category('public.interactions')
    .add('l10n_bg_website_sale_invoice_request.invoice_request', InvoiceRequest)
    .add('l10n_bg_website_sale_invoice_request.invoice_request_address', InvoiceRequestAddress);
