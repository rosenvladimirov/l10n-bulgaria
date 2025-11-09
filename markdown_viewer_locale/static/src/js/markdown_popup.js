/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { session } from "@web/session";
import { markdownRegistry } from "@markdown_viewer_locale/js/markdown_registry";

// ДЕБЪГ: Проверка дали модулът се зарежда
console.log("🔵 Markdown модул зареден!");

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        // ДЕБЪГ: Проверка дали patch-а се прилага
        console.log("🟢 FormController patch приложен!");
    },

    /**
     * Отваря Markdown документация в модал - показва индекс
     */
    async onClickMarkdownPopup(ev) {
        console.log("🟡 onClickMarkdownPopup извикан!", ev);

        ev.preventDefault();

        // Показваме индекс
        this.showMarkdownIndex();
    },

    /**
     * Показва индекс с всички документации
     */
    showMarkdownIndex() {
        console.log("📚 Показване на индекс");

        const lang = session?.user_context?.lang || 'en_US';
        const langName = lang === 'bg_BG' ? 'Български' : 'English';

        // Вземаме всички документации групирани по категория
        const docsByCategory = markdownRegistry.getAllByCategory();

        // Генерираме HTML за индекса
        let indexHTML = `
            <div class="markdown-index">
                <div class="alert alert-info mb-3">
                    <i class="fa fa-language"></i>
                    <strong>Language / Език:</strong> ${langName}
                    <small class="text-muted">(автоматично разпознат)</small>
                </div>
        `;

        // Генерираме списък по категории
        for (const [category, docs] of Object.entries(docsByCategory)) {
            indexHTML += `
                <div class="category-section mb-4">
                    <h4 class="border-bottom pb-2 mb-3">
                        <i class="fa fa-folder-open text-primary"></i> ${category}
                    </h4>
                    <div class="list-group">
            `;

            docs.forEach(doc => {
                indexHTML += `
                    <a href="#"
                       class="list-group-item list-group-item-action markdown-doc-link"
                       data-md-key="${doc.key}">
                        <div class="d-flex w-100 justify-content-between">
                            <h6 class="mb-1">
                                <i class="fa fa-file-text-o text-muted"></i>
                                ${doc.title}
                            </h6>
                        </div>
                        ${doc.description ? `<small class="text-muted">${doc.description}</small>` : ''}
                    </a>
                `;
            });

            indexHTML += `
                    </div>
                </div>
            `;
        }

        indexHTML += `</div>`;

        // Показваме модала с индекса
        this.showMarkdownModal(indexHTML, 'Documentation Index / Индекс на документацията', true);

        // Добавяме event listeners за линковете
        this.attachIndexListeners();
    },

    /**
     * Добавя event listeners за линковете в индекса
     */
    attachIndexListeners() {
        const links = document.querySelectorAll('.markdown-doc-link');

        links.forEach(link => {
            link.addEventListener('click', async (ev) => {
                ev.preventDefault();
                const mdKey = ev.currentTarget.dataset.mdKey;
                console.log("📄 Зареждане на документ:", mdKey);

                await this.loadMarkdownByKey(mdKey);
            });
        });
    },

    /**
     * Зарежда Markdown файл по ключ от регистъра
     */
    async loadMarkdownByKey(key) {
        const config = markdownRegistry.get(key);

        if (!config) {
            console.error(`❌ Не е намерена конфигурация за ключ: ${key}`);
            alert(`Markdown файлът "${key}" не е регистриран!`);
            return;
        }

        console.log("📋 Конфигурация:", config);

        await this.loadMarkdown(config.module, config.file, config.title);
    },

    /**
     * Зарежда Markdown файл според езика на потребителя
     */
    async loadMarkdown(moduleName, fileNameBase, title = 'Markdown Documentation') {
        console.log("📄 loadMarkdown стартиран:", moduleName, fileNameBase);

        try {
            // Безопасен достъп до езика
            const lang = session?.user_context?.lang || 'en_US';
            const suffix = lang.split('_')[0];
            const localizedFile = fileNameBase.replace('.md', `.${suffix}.md`);

            console.log("🌍 Език:", lang, "Суфикс:", suffix);
            console.log("📁 Локализиран файл:", localizedFile);

            // Опитваме се да заредим локализиран файл
            let url = `/${moduleName}/static/src/md/${localizedFile}`;
            console.log("🔗 Опит за зареждане:", url);
            let response = await fetch(url);

            // Fallback към основния файл
            if (!response.ok) {
                console.warn("⚠️ Локализираният файл не е намерен, опит за fallback");
                url = `/${moduleName}/static/src/md/${fileNameBase}`;
                console.log("🔗 Fallback URL:", url);
                response = await fetch(url);
            }

            if (!response.ok) {
                throw new Error(`Файлът не може да бъде зареден: ${url}`);
            }

            console.log("✅ Файлът е зареден успешно!");
            const mdText = await response.text();
            console.log("📝 Markdown текст (първите 100 символа):", mdText.substring(0, 100));

            // Проверка за marked библиотека
            if (typeof marked === 'undefined') {
                throw new Error('Библиотеката marked.js не е заредена');
            }
            console.log("✅ marked.js библиотека налична");

            // Конвертиране на Markdown в HTML
            const htmlContent = marked.parse(mdText, {
                highlight: function(code, lang) {
                    if (typeof hljs !== 'undefined' && lang && hljs.getLanguage(lang)) {
                        return hljs.highlight(code, { language: lang }).value;
                    }
                    if (typeof hljs !== 'undefined') {
                        return hljs.highlightAuto(code).value;
                    }
                    return code;
                }
            });
            console.log("🎨 HTML конвертиран (първите 100 символа):", htmlContent.substring(0, 100));

            // Добавяме бутон "Назад към индекс"
            const contentWithBackButton = `
                <div class="mb-3">
                    <button class="btn btn-sm btn-outline-secondary o_markdown_back_btn">
                        <i class="fa fa-arrow-left"></i> Back to Index / Назад към индекс
                    </button>
                </div>
                <hr/>
                ${htmlContent}
            `;

            // Показване на модала
            this.showMarkdownModal(contentWithBackButton, title, false);
            this.addSearchFeature();
            this.attachBackButton();

        } catch (error) {
            console.error("❌ Грешка при зареждане на Markdown:", error);
            alert(`Грешка: ${error.message}`);
        }
    },

    /**
     * Добавя функционалност на бутон "Назад"
     */
    attachBackButton() {
        const backBtn = document.querySelector('.o_markdown_back_btn');
        if (backBtn) {
            backBtn.addEventListener('click', () => {
                this.showMarkdownIndex();
            });
        }
    },

    /**
     * Показва или създава модал
     */
    showMarkdownModal(htmlContent, title = 'Markdown Documentation', isIndex = false) {
        console.log("🪟 showMarkdownModal извикан");

        let modalEl = document.querySelector(".o_markdown_modal");
        console.log("🔍 Съществуващ модал намерен:", !!modalEl);

        if (!modalEl) {
            console.log("🆕 Създаване на нов модал...");
            // Създаваме модала ако не съществува
            modalEl = document.createElement('div');
            modalEl.className = 'modal fade o_markdown_modal';
            modalEl.tabIndex = -1;
            modalEl.innerHTML = `
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${title}</h5>
                            <button type="button" class="btn-close"></button>
                        </div>
                        <div class="modal-body">
                            <input type="text" class="form-control o_markdown_search mb-3" placeholder="Search..." style="display: none;"/>
                            <div class="o_markdown_content"></div>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modalEl);

            // Добавяме event listener за затваряне
            const closeBtn = modalEl.querySelector('.btn-close');
            closeBtn.addEventListener('click', () => {
                this.closeModal(modalEl);
            });

            console.log("✅ Модал създаден и добавен в DOM");
        } else {
            // Обновяваме заглавието
            const titleEl = modalEl.querySelector('.modal-title');
            if (titleEl) {
                titleEl.textContent = title;
            }
        }

        // Показваме/скриваме search според дали е индекс
        const searchInput = modalEl.querySelector('.o_markdown_search');
        if (searchInput) {
            searchInput.style.display = isIndex ? 'none' : 'block';
        }

        // Добавяме съдържанието
        const contentDiv = modalEl.querySelector(".o_markdown_content");
        if (contentDiv) {
            contentDiv.innerHTML = htmlContent;
            console.log("✅ Съдържание добавено в модала");
        } else {
            console.error("❌ .o_markdown_content не е намерен!");
        }

        // Показваме модала с Bootstrap 5 API
        console.log("👁️ Показване на модала...");

        try {
            // Използваме window.bootstrap
            if (window.bootstrap && window.bootstrap.Modal) {
                const modal = new window.bootstrap.Modal(modalEl);
                modal.show();
                console.log("✅ Модал показан с Bootstrap");
            } else {
                // Ръчно показване
                console.warn("⚠️ Bootstrap Modal не е наличен, показвам ръчно");
                modalEl.classList.add('show');
                modalEl.style.display = 'block';
                document.body.classList.add('modal-open');

                // Добавяме backdrop
                let backdrop = document.querySelector('.modal-backdrop');
                if (!backdrop) {
                    backdrop = document.createElement('div');
                    backdrop.className = 'modal-backdrop fade show';
                    document.body.appendChild(backdrop);

                    // Затваряне при клик на backdrop
                    backdrop.addEventListener('click', () => {
                        this.closeModal(modalEl);
                    });
                }
                console.log("✅ Модал показан ръчно");
            }
        } catch (error) {
            console.error("❌ Грешка при показване на модал:", error);
            alert("Грешка при отваряне на модала");
        }
    },

    /**
     * Затваря модала
     */
    closeModal(modalEl) {
        console.log("🔒 Затваряне на модал");

        if (window.bootstrap && window.bootstrap.Modal) {
            const modal = window.bootstrap.Modal.getInstance(modalEl);
            if (modal) {
                modal.hide();
            }
        } else {
            // Ръчно затваряне
            modalEl.classList.remove('show');
            modalEl.style.display = 'none';
            document.body.classList.remove('modal-open');

            const backdrop = document.querySelector('.modal-backdrop');
            if (backdrop) {
                backdrop.remove();
            }
        }

        console.log("✅ Модал затворен");
    },

    /**
     * Добавя функция за търсене в съдържанието
     */
    addSearchFeature() {
        console.log("🔎 addSearchFeature извикан");

        const searchInput = document.querySelector(".o_markdown_search");
        if (!searchInput) {
            console.warn("⚠️ Search input не е намерен!");
            return;
        }

        console.log("✅ Search input намерен");

        // Премахваме стари listeners
        const newSearchInput = searchInput.cloneNode(true);
        searchInput.replaceWith(newSearchInput);

        newSearchInput.addEventListener("input", () => {
            const query = newSearchInput.value.toLowerCase();
            console.log("🔍 Търсене за:", query);

            const contentDiv = document.querySelector(".o_markdown_content");
            if (!contentDiv) return;

            const paragraphs = contentDiv.querySelectorAll("p, li, h1, h2, h3, h4, h5, h6");
            console.log("📊 Намерени елементи за търсене:", paragraphs.length);

            paragraphs.forEach(el => {
                if (query && el.textContent.toLowerCase().includes(query)) {
                    el.style.backgroundColor = "yellow";
                } else {
                    el.style.backgroundColor = "";
                }
            });
        });

        console.log("✅ Search feature добавен");
    }
});

console.log("🏁 Markdown модул напълно зареден и конфигуриран!");
