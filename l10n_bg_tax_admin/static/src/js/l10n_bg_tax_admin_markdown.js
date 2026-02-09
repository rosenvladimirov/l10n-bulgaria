/** @odoo-module **/

import { markdownRegistry } from "@markdown_viewer_locale/js/markdown_registry";

// Регистрираме документацията за ДДС администрация
markdownRegistry.register(
    'l10n_bg_tax_admin',
    'l10n_bg_tax_admin',
    'l10n_bg_tax_admin_documentation.md',
    'Guide to VAT Administration (Bulgaria)',
    'Accounting',
    'Complete guide to using the module for VAT administration according to VAT - includes GOP, customs, protocols under Art. 117, personal use',
    [
        'account.move',
        'account.move.line',
        'account.move.bg.protocol',
        'account.move.bg.private',
        'account.move.bg.customs',
        'account.fiscal.position',
        'account.fiscal.position.tax.action'
    ]
);

console.log("✅ ДДС администрация документация регистрирана успешно!");
