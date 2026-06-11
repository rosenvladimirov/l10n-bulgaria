/** @odoo-module **/

import { markdownRegistry } from "@markdown_viewer_locale/js/markdown_registry";

// Регистрираме документацията за автоматичното складово счетоводство
markdownRegistry.register(
    'l10n_bg_stock_account',
    'l10n_bg_stock_account_manual',
    'l10n_bg_stock_account_documentation.md',
    'Guide to Stock Auto Accounting (Bulgaria)',
    'Inventory',
    'How to configure and use automatic stock accounting at picking validation for manual/periodic costing — accounts per product category, generated journal entries, scrap and inventory adjustments, price differences.',
    [
        'stock.picking',
        'stock.move',
        'product.category',
        'account.move',
    ]
);

console.log("l10n_bg_stock_account_manual: documentation registered.");
