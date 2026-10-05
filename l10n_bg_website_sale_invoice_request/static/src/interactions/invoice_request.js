import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { rpc } from '@web/core/network/rpc';

// Checkout: „Искам фактура“ — клиентът става фирмата; ако тя липсва, отделната
// форма „Фирма за фактура“; без отметка поръчката се връща към лицето
export class InvoiceRequest extends Interaction {
    static selector = '#l10n_bg_invoice_requested';
    dynamicContent = {
        _root: { 't-on-change': this.onChange },
    };

    async onChange() {
        const result = await this.waitFor(
            rpc('/shop/l10n_bg/invoice_request', { requested: this.el.checked })
        );
        window.location = (result && result.form_url) || '/shop/checkout';
    }
}

registry
    .category('public.interactions')
    .add('l10n_bg_website_sale_invoice_request.invoice_request', InvoiceRequest);
