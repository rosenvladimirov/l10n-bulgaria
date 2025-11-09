
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
     */
    register(key, moduleName, fileName, title = 'Documentation', category = 'General', description = '') {
        this.registry.set(key, {
            key: key,
            module: moduleName,
            file: fileName,
            title: title,
            category: category,
            description: description
        });
        console.log(`📝 Регистриран Markdown: ${key} -> ${moduleName}/${fileName}`);
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
     * Връща всички файлове групирани по категория
     */
    getAllByCategory() {
        const items = this.getAll();
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

// Регистрираме документация
markdownRegistry.register(
    'welcome',
    'markdown_viewer_locale',
    'readme.md',
    'Welcome Guide',
    'General',
    'Getting started with the system'
);

markdownRegistry.register(
    'partner_help',
    'markdown_viewer_locale',
    'partner_help.md',
    'Contacts & Partners',
    'CRM',
    'How to manage contacts and partners'
);
