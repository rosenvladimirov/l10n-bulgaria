/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { loadJS } from "@web/core/assets";
import { session } from "@web/session";
import { markdownRegistry } from "@markdown_viewer_locale/js/markdown_registry";

// Lazy-load на marked.js + highlight.js само при първо отваряне на popup-а.
// Преди бяха в `web.assets_backend` → товареха се при ВСЯКО backend зареждане
// и замърсяваха window.marked / window.hljs дори когато никой не ползва модула.
const MARKDOWN_LIB_URLS = [
    "/markdown_viewer_locale/static/src/lib/marked.min.js",
    "/markdown_viewer_locale/static/src/lib/highlight.min.js",
];
let _markdownLibsPromise = null;

function ensureMarkdownLibsLoaded() {
    if (!_markdownLibsPromise) {
        _markdownLibsPromise = Promise.all(MARKDOWN_LIB_URLS.map(loadJS));
    }
    return _markdownLibsPromise;
}

patch(FormController.prototype, {
    /**
     * Отваря Markdown документация в модал - показва индекс
     */
    async onClickMarkdownPopup(ev) {
        ev.preventDefault();
        const resModel = this.props.resModel || this.model?.config?.resModel;
        this.showMarkdownIndex(resModel);
    },

    /**
     * Взема езика на потребителя
     */
    getUserLanguage() {
        if (session?.bundle_params?.lang) {
            return session.bundle_params.lang;
        }
        if (session?.user_context?.lang) {
            return session.user_context.lang;
        }
        if (session?.user_settings?.lang) {
            return session.user_settings.lang;
        }
        try {
            const userService = this.env?.services?.user;
            if (userService?.context?.lang) {
                return userService.context.lang;
            }
            if (userService?.lang) {
                return userService.lang;
            }
        } catch (e) {
            // ignore - fallback below
        }
        if (typeof odoo !== "undefined" && odoo?.session_info?.user_context?.lang) {
            return odoo.session_info.user_context.lang;
        }
        return "en_US";
    },

    /**
     * Показва индекс с всички документации филтрирани по модел
     */
    showMarkdownIndex(resModel = null) {
        const lang = this.getUserLanguage();
        const langName = lang === "bg_BG" ? "Български" : "English";

        const docsByCategory = markdownRegistry.getAllByCategory(resModel);
        const totalDocs = Object.values(docsByCategory).reduce((sum, docs) => sum + docs.length, 0);

        if (totalDocs === 0) {
            const noDocsHTML = `
                <div class="markdown-index">
                    <div class="alert alert-warning">
                        <i class="fa fa-exclamation-triangle"></i>
                        <strong>No documentation available / Няма налична документация</strong>
                        <p class="mb-0 mt-2">
                            No documentation has been registered for model: <code>${resModel || "unknown"}</code>
                        </p>
                    </div>
                </div>
            `;
            this.showMarkdownModal(noDocsHTML, "Documentation Index / Индекс на документацията", true);
            return;
        }

        let indexHTML = `
            <div class="markdown-index">
                <div class="alert alert-info mb-3">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <i class="fa fa-language"></i>
                            <strong>Language / Език:</strong> ${langName}
                        </div>
                        ${resModel ? `
                        <div>
                            <i class="fa fa-database"></i><span/><strong>Model:</strong><span/><code>${resModel}</code>
                        </div>
                        ` : ""}
                    </div>
                    <small class="text-muted d-block mt-2">
                        Found ${totalDocs} documentation(s) / Намерени ${totalDocs} документации
                    </small>
                </div>
        `;

        for (const [category, docs] of Object.entries(docsByCategory)) {
            indexHTML += `
                <div class="category-section mb-4">
                    <h4 class="border-bottom pb-2 mb-3">
                        <i class="fa fa-folder-open text-primary"></i> ${category}
                        <span class="badge bg-secondary ms-2">${docs.length}</span>
                    </h4>
                    <div class="list-group">
            `;

            docs.forEach(doc => {
                let modelsInfo = "";
                if (doc.models && doc.models.length > 0) {
                    const modelsList = doc.models.join(", ");
                    modelsInfo = `
                        <div class="mt-1">
                            <small class="text-info">
                                <i class="fa fa-tag"></i> ${modelsList}
                            </small>
                        </div>
                    `;
                }

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
                        ${doc.description ? `<small class="text-muted d-block">${doc.description}</small>` : ""}
                        ${modelsInfo}
                    </a>
                `;
            });

            indexHTML += `
                    </div>
                </div>
            `;
        }

        indexHTML += `</div>`;

        this.showMarkdownModal(indexHTML, "Documentation Index / Индекс на документацията", true);
        this.attachIndexListeners();
    },

    /**
     * Добавя event listeners за линковете в индекса
     */
    attachIndexListeners() {
        const links = document.querySelectorAll(".markdown-doc-link");
        links.forEach(link => {
            link.addEventListener("click", async (ev) => {
                ev.preventDefault();
                const mdKey = ev.currentTarget.dataset.mdKey;
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
            console.error(`Markdown key not registered: ${key}`);
            alert(`Markdown файлът "${key}" не е регистриран!`);
            return;
        }
        await this.loadMarkdown(config.module, config.file, config.title);
    },

    /**
     * Зарежда Markdown файл според езика на потребителя
     */
    async loadMarkdown(moduleName, fileNameBase, title = "Markdown Documentation") {
        try {
            // Зарежда marked.js + highlight.js при първа нужда
            await ensureMarkdownLibsLoaded();

            const lang = this.getUserLanguage();
            const suffix = lang.split("_")[0];
            const localizedFile = fileNameBase.replace(".md", `.${suffix}.md`);

            let url = `/${moduleName}/static/src/md/${localizedFile}`;
            let response = await fetch(url);

            // Fallback към основния файл
            if (!response.ok) {
                url = `/${moduleName}/static/src/md/${fileNameBase}`;
                response = await fetch(url);
            }

            if (!response.ok) {
                throw new Error(`Файлът не може да бъде зареден: ${url}`);
            }

            const mdText = await response.text();

            if (typeof marked === "undefined") {
                throw new Error("Библиотеката marked.js не е заредена");
            }

            const htmlContent = marked.parse(mdText, {
                highlight: function (code, lang) {
                    if (typeof hljs !== "undefined" && lang && hljs.getLanguage(lang)) {
                        return hljs.highlight(code, { language: lang }).value;
                    }
                    if (typeof hljs !== "undefined") {
                        return hljs.highlightAuto(code).value;
                    }
                    return code;
                },
            });

            const resModel = this.props.resModel || this.model?.config?.resModel;
            const contentWithBackButton = `
                <div class="mb-3">
                    <button class="btn btn-sm btn-outline-secondary o_markdown_back_btn" data-res-model="${resModel || ""}">
                        <i class="fa fa-arrow-left"></i> Back to Index / Назад към индекс
                    </button>
                </div>
                <hr/>
                ${htmlContent}
            `;

            this.showMarkdownModal(contentWithBackButton, title, false);
            this.addSearchFeature();
            this.attachBackButton();
        } catch (error) {
            console.error("Markdown load failed:", error);
            alert(`Грешка: ${error.message}`);
        }
    },

    /**
     * Добавя функционалност на бутон "Назад"
     */
    attachBackButton() {
        const backBtn = document.querySelector(".o_markdown_back_btn");
        if (backBtn) {
            backBtn.addEventListener("click", () => {
                const resModel = backBtn.dataset.resModel || null;
                this.showMarkdownIndex(resModel);
            });
        }
    },

    /**
     * Показва или създава модал
     */
    showMarkdownModal(htmlContent, title = "Markdown Documentation", isIndex = false) {
        let modalEl = document.querySelector(".o_markdown_modal");

        if (!modalEl) {
            modalEl = document.createElement("div");
            modalEl.className = "modal fade o_markdown_modal";
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

            const closeBtn = modalEl.querySelector(".btn-close");
            closeBtn.addEventListener("click", () => {
                this.closeModal(modalEl);
            });
        } else {
            const titleEl = modalEl.querySelector(".modal-title");
            if (titleEl) {
                titleEl.textContent = title;
            }
        }

        const searchInput = modalEl.querySelector(".o_markdown_search");
        if (searchInput) {
            searchInput.style.display = isIndex ? "none" : "block";
        }

        const contentDiv = modalEl.querySelector(".o_markdown_content");
        if (contentDiv) {
            contentDiv.innerHTML = htmlContent;
        }

        try {
            if (window.bootstrap && window.bootstrap.Modal) {
                const modal = new window.bootstrap.Modal(modalEl);
                modal.show();
            } else {
                modalEl.classList.add("show");
                modalEl.style.display = "block";
                document.body.classList.add("modal-open");

                let backdrop = document.querySelector(".modal-backdrop");
                if (!backdrop) {
                    backdrop = document.createElement("div");
                    backdrop.className = "modal-backdrop fade show";
                    document.body.appendChild(backdrop);
                    backdrop.addEventListener("click", () => {
                        this.closeModal(modalEl);
                    });
                }
            }
        } catch (error) {
            console.error("Markdown modal show failed:", error);
            alert("Грешка при отваряне на модала");
        }
    },

    /**
     * Затваря модала
     */
    closeModal(modalEl) {
        if (window.bootstrap && window.bootstrap.Modal) {
            const modal = window.bootstrap.Modal.getInstance(modalEl);
            if (modal) {
                modal.hide();
            }
        } else {
            modalEl.classList.remove("show");
            modalEl.style.display = "none";
            document.body.classList.remove("modal-open");
            const backdrop = document.querySelector(".modal-backdrop");
            if (backdrop) {
                backdrop.remove();
            }
        }
    },

    /**
     * Добавя функция за търсене в съдържанието
     */
    addSearchFeature() {
        const searchInput = document.querySelector(".o_markdown_search");
        if (!searchInput) {
            return;
        }

        // Re-clone за да се махнат стари listener-и от предишно отваряне
        const newSearchInput = searchInput.cloneNode(true);
        searchInput.replaceWith(newSearchInput);

        newSearchInput.addEventListener("input", () => {
            const query = newSearchInput.value.toLowerCase();
            const contentDiv = document.querySelector(".o_markdown_content");
            if (!contentDiv) {
                return;
            }
            const paragraphs = contentDiv.querySelectorAll("p, li, h1, h2, h3, h4, h5, h6");
            paragraphs.forEach(el => {
                if (query && el.textContent.toLowerCase().includes(query)) {
                    el.style.backgroundColor = "yellow";
                } else {
                    el.style.backgroundColor = "";
                }
            });
        });
    },
});
