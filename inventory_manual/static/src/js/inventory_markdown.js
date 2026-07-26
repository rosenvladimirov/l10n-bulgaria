/** @odoo-module **/

import { markdownRegistry } from "@markdown_viewer_locale/js/markdown_registry";

const STOCK_MODELS = ['stock.picking', 'stock.move', 'stock.move.line'];

markdownRegistry.register(
    'stock_process_overview',
    'inventory_manual',
    'stock_process_overview.md',
    'Warehouse Process Overview',
    'Inventory',
    'End-to-end warehouse flow: receipts, deliveries, internal transfers.',
    STOCK_MODELS
);

// NOTE: 'stock_handover_protocol' is intentionally NOT registered here.
// l10n_bg_report_stock on 19.0 does not (yet) implement the Handover Protocol
// report that exists on 18.0 — only the Accepted-Delivery Slip is ported.

markdownRegistry.register(
    'stock_accepted_delivery_slip',
    'inventory_manual',
    'stock_accepted_delivery_slip.md',
    'Accepted-Delivery Slip',
    'Inventory',
    'Printing the accepted-delivery slip from a stock picking (l10n_bg_report_stock).',
    STOCK_MODELS
);

markdownRegistry.register(
    'stock_line_description_delivery',
    'inventory_manual',
    'stock_line_description_delivery.md',
    'Order Line Wording on the Delivery Slip',
    'Inventory',
    'How the delivery slip picks up the sale order line text instead of the bare product name (l10n_bg_stock_sale_line_description).',
    STOCK_MODELS
);

markdownRegistry.register(
    'stock_multi_warehouse',
    'inventory_manual',
    'stock_multi_warehouse.md',
    'Multiple Warehouses and Locations',
    'Inventory',
    'Practical guidance for setting up and working with more than one warehouse.',
    STOCK_MODELS
);

console.log("inventory_manual: documentation registered.");
