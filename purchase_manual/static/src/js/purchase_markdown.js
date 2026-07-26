/** @odoo-module **/

import { markdownRegistry } from "@markdown_viewer_locale/js/markdown_registry";

const PURCHASE_MODELS = ['purchase.order', 'purchase.order.line'];

markdownRegistry.register(
    'purchase_process_overview',
    'purchase_manual',
    'purchase_process_overview.md',
    'Purchase Process Overview',
    'Purchase',
    'End-to-end purchase flow: RFQ, order confirmation, receipt, vendor bill.',
    PURCHASE_MODELS
);

markdownRegistry.register(
    'purchase_to_bill_fiscal_bridge',
    'purchase_manual',
    'purchase_to_bill_fiscal_bridge.md',
    'From Purchase Order to Vendor Bill — Fiscal Bridge',
    'Purchase',
    'Why purchase.order itself has no Bulgarian VAT logic, and what happens once the vendor bill is created (fiscal position, Art. 117 protocols).',
    PURCHASE_MODELS
);

markdownRegistry.register(
    'purchase_eori_supplier',
    'purchase_manual',
    'purchase_eori_supplier.md',
    'Supplier EORI Number',
    'Purchase',
    'Why the supplier EORI number matters for EU and import purchases and where to set it.',
    PURCHASE_MODELS
);

markdownRegistry.register(
    'purchase_eu_supplier',
    'purchase_manual',
    'purchase_eu_supplier.md',
    'Buying from an EU Supplier',
    'Purchase',
    'What to check on the purchase order for an intra-community acquisition before the vendor bill is created.',
    PURCHASE_MODELS
);

markdownRegistry.register(
    'purchase_import_customs',
    'purchase_manual',
    'purchase_import_customs.md',
    'Importing from Outside the EU',
    'Purchase',
    'Purchase-order-side considerations for imports: customs value, landed costs, and the link to the customs declaration on the bill.',
    PURCHASE_MODELS
);

console.log("purchase_manual: documentation registered.");
