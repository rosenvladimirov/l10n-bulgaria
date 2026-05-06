
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
// Временно изключено за изолация на Knowledge Share VList breakage (2026-04-30).
// Хипотеза: registration с models=null + 11-те LogiKal docs триггерира Owl грешка.
// Ако Share работи без този блок → потвърден root cause; иначе се връща обратно.
// markdownRegistry.register(
//     'welcome',
//     'markdown_viewer_locale',
//     'readme.md',
//     'Welcome Guide',
//     'General',
//     'Getting started with the system',
//     null  // null = показва се навсякъде
// );
