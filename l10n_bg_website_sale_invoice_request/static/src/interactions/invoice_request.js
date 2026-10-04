import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { rpc } from '@web/core/network/rpc';

// Отметката „Искам фактура“ в checkout — пази се в поръчката
export class InvoiceRequest extends Interaction {
    static selector = '#l10n_bg_invoice_requested';
    dynamicContent = {
        _root: { 't-on-change': this.onChange },
    };

    async onChange() {
        const result = await this.waitFor(
            rpc('/shop/l10n_bg/invoice_request', { requested: this.el.checked })
        );
        // поискана фактура ⇒ веднага формата за адреса за фактура (фирма, ДДС, ЕИК)
        if (this.el.checked && result && result.billing_url) {
            window.location = result.billing_url;
        }
    }
}

registry
    .category('public.interactions')
    .add('l10n_bg_website_sale_invoice_request.invoice_request', InvoiceRequest);
