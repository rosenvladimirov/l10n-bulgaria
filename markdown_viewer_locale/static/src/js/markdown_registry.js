
/** @odoo-module **/

/**
 * Централен регистър за Markdown документация
 */
class MarkdownRegistry {
    constructor() {
        this.registry = new Map();
    }

    /**
     * Регистрира Markdown файл
     * @param {string} key - Уникален идентификатор
     * @param {string} moduleName - Име на модула
     * @param {string} fileName - Име на файла
     * @param {string} title - Заглавие за показване
     * @param {string} category - Категория (General, Sales, Accounting, etc.)
     * @param {string} description - Кратко описание
     * @param {Array|string|null} models - Odoo модели за които е документацията (null = всички)
     */
    register(key, moduleName, fileName, title = 'Documentation', category = 'General', description = '', models = null) {
        // Нормализираме models към Array
        let modelsList = null;
        if (models) {
            if (typeof models === 'string') {
                modelsList = [models];
            } else if (Array.isArray(models)) {
                modelsList = models;
            }
        }

        this.registry.set(key, {
            key: key,
            module: moduleName,
            file: fileName,
            title: title,
            category: category,
            description: description,
            models: modelsList  // null = показва се за всички модели
        });

        const modelsInfo = modelsList ? modelsList.join(', ') : 'all models';
        console.log(`📝 Регистриран Markdown: ${key} -> ${moduleName}/${fileName} (${modelsInfo})`);
    }

    /**
     * Взема конфигурация за Markdown файл
     */
    get(key) {
        return this.registry.get(key);
    }

    /**
     * Връща всички регистрирани файлове
     */
    getAll() {
        return Array.from(this.registry.values());
    }

    /**
     * Връща документации за конкретен модел или общи
     * @param {string|null} resModel - Име на модела (напр. 'res.partner')
     */
    getForModel(resModel = null) {
        const allDocs = this.getAll();

        if (!resModel) {
            // Ако няма модел, връщаме само общите документации
            return allDocs.filter(doc => doc.models === null);
        }

        // Филтрираме документации които са или за този модел, или общи
        return allDocs.filter(doc => {
            // Общи документации (models === null)
            if (doc.models === null) {
                return true;
            }
            // Специфични за този модел
            if (doc.models.includes(resModel)) {
                return true;
            }
            return false;
        });
    }

    /**
     * Връща документации групирани по категория за конкретен модел
     * @param {string|null} resModel - Име на модела
     */
    getAllByCategory(resModel = null) {
        const items = this.getForModel(resModel);
        const grouped = {};

        items.forEach(item => {
            if (!grouped[item.category]) {
                grouped[item.category] = [];
            }
            grouped[item.category].push(item);
        });

        return grouped;
    }

    /**
     * Проверява дали key съществува
     */
    has(key) {
        return this.registry.has(key);
    }
}

// Експортираме singleton инстанция
export const markdownRegistry = new MarkdownRegistry();

// ========================================
// РЕГИСТРАЦИЯ НА ДОКУМЕНТАЦИИ
// ========================================

// ОБЩИ ДОКУМЕНТАЦИИ (за всички модели)
markdownRegistry.register(
    'welcome',
    'markdown_viewer_locale',
    'readme.md',
    'Welcome Guide',
    'General',
    'Getting started with the system',
    null  // null = показва се навсякъде
);

markdownRegistry.register(
    'system_overview',
    'markdown_viewer_locale',
    'system_overview.md',
    'System Overview',
    'General',
    'Overview of system capabilities',
    null
);

// ДОКУМЕНТАЦИИ ЗА КОНКРЕТНИ МОДЕЛИ

// CRM - Contacts/Partners
markdownRegistry.register(
    'partner_help',
    'markdown_viewer_locale',
    'partner_help.md',
    'Contacts & Partners Guide',
    'CRM',
    'How to manage contacts and partners',
    ['res.partner', 'res.company']  // Показва се само в тези модели
);

// Sales
markdownRegistry.register(
    'sale_order_help',
    'markdown_viewer_locale',
    'sale_order_help.md',
    'Sales Orders Guide',
    'Sales',
    'Create and manage sales orders',
    ['sale.order', 'sale.order.line']
);

markdownRegistry.register(
    'quotation_help',
    'markdown_viewer_locale',
    'quotation_help.md',
    'Quotations Guide',
    'Sales',
    'How to create quotations',
    'sale.order'  // Може да е и string
);

// Accounting
markdownRegistry.register(
    'invoice_help',
    'markdown_viewer_locale',
    'invoice_help.md',
    'Invoices Guide',
    'Accounting',
    'Invoice management and workflows',
    ['account.move', 'account.move.line']
);

markdownRegistry.register(
    'payment_help',
    'markdown_viewer_locale',
    'payment_help.md',
    'Payments Guide',
    'Accounting',
    'How to register payments',
    ['account.payment']
);

// Inventory
markdownRegistry.register(
    'product_help',
    'markdown_viewer_locale',
    'product_help.md',
    'Products Guide',
    'Inventory',
    'Product catalog and variants',
    ['product.product', 'product.template']
);

markdownRegistry.register(
    'stock_help',
    'markdown_viewer_locale',
    'stock_help.md',
    'Stock Operations',
    'Inventory',
    'Manage inventory and stock moves',
    ['stock.picking', 'stock.move']
);

// HR
markdownRegistry.register(
    'employee_help',
    'markdown_viewer_locale',
    'employee_help.md',
    'Employee Management',
    'Human Resources',
    'How to manage employee records',
    ['hr.employee']
);

console.log("✅ Markdown Registry инициализиран с", markdownRegistry.getAll().length, "документации");
