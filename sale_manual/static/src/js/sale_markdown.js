/** @odoo-module **/

import { markdownRegistry } from "@markdown_viewer_locale/js/markdown_registry";

const SALE_MODELS = ['sale.order', 'sale.order.line'];

markdownRegistry.register(
    'sale_process_overview',
    'sale_manual',
    'sale_process_overview.md',
    'Sales Process Overview',
    'Sales',
    'End-to-end sales flow: quotation, confirmation, delivery, invoicing.',
    SALE_MODELS
);

markdownRegistry.register(
    'sale_delivery_note',
    'sale_manual',
    'sale_delivery_note.md',
    'Handover Protocol / Delivery Note',
    'Sales',
    'Printing the accepted-delivery / handover protocol directly from the sale order (l10n_bg_sale_order_delivery_note).',
    SALE_MODELS
);

markdownRegistry.register(
    'sale_line_description_delivery',
    'sale_manual',
    'sale_line_description_delivery.md',
    'Order Line Wording on the Delivery Slip',
    'Sales',
    'Why the delivery slip shows the sale order line text instead of the bare product name (l10n_bg_stock_sale_line_description).',
    SALE_MODELS
);

markdownRegistry.register(
    'sale_eu_export_customers',
    'sale_manual',
    'sale_eu_export_customers.md',
    'Selling to EU and Non-EU Customers',
    'Sales',
    'What a salesperson needs to check (customer VAT, country, delivery address) so the correct VAT treatment applies later on the invoice.',
    SALE_MODELS
);

markdownRegistry.register(
    'sale_eshop_alt_regime',
    'sale_manual',
    'sale_eshop_alt_regime.md',
    'Online Store — NRA Alternative Regime',
    'Sales',
    'When confirmed sale orders feed the NRA "alternative e-shop regime" audit report (l10n_bg_eshop_alt).',
    SALE_MODELS
);

console.log("sale_manual: documentation registered.");
