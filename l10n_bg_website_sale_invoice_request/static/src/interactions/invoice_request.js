import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { rpc } from '@web/core/network/rpc';

// Checkout: „Искам фактура“ отваря на място фирмата и адреса за фактуриране;
// стандартният списък с адреси за фактура се скрива, докато е поискана фактура
export class InvoiceRequest extends Interaction {
    static selector = '#shop_checkout';
    dynamicContent = {
        '#l10n_bg_invoice_requested': { 't-on-change': this.onToggle },
        '#l10n_bg_ic_save': { 't-on-click': this.onSave },
    };

    setup() {
        this.toggle = this.el.querySelector('#l10n_bg_invoice_requested');
        this.block = this.el.querySelector('#l10n_bg_invoice_company_block');
        this.billingList = this.el.querySelector('#billing_address_list');
    }

    start() {
        this.showBlock(this.toggle && this.toggle.checked);
    }

    showBlock(on) {
        this.block?.classList.toggle('d-none', !on);
        this.billingList?.classList.toggle('d-none', !!on);
    }

    async onToggle() {
        const result = await this.waitFor(
            rpc('/shop/l10n_bg/invoice_request', { requested: this.toggle.checked })
        );
        if (result && result.reload) {
            window.location.reload();
            return;
        }
        this.showBlock(this.toggle.checked);
    }

    async onSave() {
        const data = {};
        for (const input of this.block.querySelectorAll('[data-field]')) {
            data[input.dataset.field] = input.value;
            input.classList.remove('is-invalid');
        }
        const result = await this.waitFor(rpc('/shop/l10n_bg/invoice_company/save', data));
        const errorBox = this.block.querySelector('#l10n_bg_ic_error');
        if (result && result.errors) {
            for (const field of Object.keys(result.errors)) {
                this.block.querySelector(`[data-field="${field}"]`)?.classList.add('is-invalid');
            }
            errorBox.textContent = Object.values(result.errors).join(' ');
            errorBox.classList.remove('d-none');
            return;
        }
        window.location.reload();
    }
}

registry
    .category('public.interactions')
    .add('l10n_bg_website_sale_invoice_request.invoice_request', InvoiceRequest);
