/** @odoo-module **/
import { Component, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";

class MarkdownPopupDropdown extends Component {
    static template = "markdown_viewer_locale_dropdown.MarkdownModal";

    setup() {
        onMounted(() => {
            this.initEvents();
        });
    }

    initEvents() {
        document.querySelectorAll(".o_show_markdown_dropdown").forEach(link => {
            link.addEventListener("click", (e) => {
                e.preventDefault();
                this.populateDropdowns(link);
                this.showModal();
            });
        });

        const loadBtn = document.querySelector(".o_markdown_load_btn");
        if (loadBtn) {
            loadBtn.addEventListener("click", async () => {
                await this.loadSelectedMarkdown();
            });
        }
    }

    showModal() {
        const modalEl = document.querySelector(".o_markdown_modal");
        if (modalEl) {
            const modal = new bootstrap.Modal(modalEl);
            modal.show();
        }
    }

    async loadSelectedMarkdown() {
        try {
            const moduleName = document.querySelector(".o_markdown_module")?.value;
            const fileNameBase = document.querySelector(".o_markdown_file")?.value;
            const lang = document.querySelector(".o_markdown_lang")?.value;

            if (!moduleName || !fileNameBase || !lang) {
                throw new Error("Моля, изберете модул, файл и език");
            }

            const suffix = lang.split('_')[0];
            const localizedFile = fileNameBase.replace('.md', `.${suffix}.md`);

            let url = `/${moduleName}/static/src/md/${localizedFile}`;
            let response = await fetch(url);

            if (!response.ok) {
                // fallback към основния файл
                url = `/${moduleName}/static/src/md/${fileNameBase}`;
                response = await fetch(url);
            }

            if (!response.ok) {
                throw new Error(`Файлът не може да бъде зареден: ${url}`);
            }

            const mdText = await response.text();
            const htmlContent = marked.parse(mdText, {
                highlight: function(code, lang) {
                    if (lang && hljs.getLanguage(lang)) {
                        return hljs.highlight(code, { language: lang }).value;
                    }
                    return hljs.highlightAuto(code).value;
                }
            });

            const contentDiv = document.querySelector(".o_markdown_content");
            if (contentDiv) {
                contentDiv.innerHTML = htmlContent;
            }

            this.addSearchFeature();
        } catch (error) {
            console.error("Грешка при зареждане на Markdown:", error);
            alert(`Грешка: ${error.message}`);
        }
    }

    populateDropdowns(link) {
        const currentLang = odoo.session.user_context.lang || 'bg_BG';
        const defaultModule = link.dataset.mdModule || 'markdown_viewer_locale_dropdown';
        const defaultFile = link.dataset.mdFile || 'readme.md';

        // Populate language dropdown
        const langSelect = document.querySelector(".o_markdown_lang");
        if (langSelect) {
            langSelect.innerHTML = '';
            const languages = [
                { value: 'bg_BG', label: 'Български (bg_BG)' },
                { value: 'en_US', label: 'English (en_US)' },
                { value: 'de_DE', label: 'Deutsch (de_DE)' }
            ];
            languages.forEach(l => {
                const opt = document.createElement('option');
                opt.value = l.value;
                opt.textContent = l.label;
                if (l.value === currentLang) {
                    opt.selected = true;
                }
                langSelect.appendChild(opt);
            });
        }

        // Populate file dropdown
        const fileSelect = document.querySelector(".o_markdown_file");
        if (fileSelect) {
            fileSelect.innerHTML = '';
            const files = ['readme.md', 'guide.md', 'help.md', 'documentation.md'];
            files.forEach(f => {
                const opt = document.createElement('option');
                opt.value = f;
                opt.textContent = f;
                if (f === defaultFile) {
                    opt.selected = true;
                }
                fileSelect.appendChild(opt);
            });
        }

        // Populate module dropdown
        const moduleSelect = document.querySelector(".o_markdown_module");
        if (moduleSelect) {
            moduleSelect.innerHTML = '';
            const modules = [
                'markdown_viewer_locale_dropdown',
                'l10n_bg_tax_admin',
                'custom_module'
            ];
            modules.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m;
                opt.textContent = m;
                if (m === defaultModule) {
                    opt.selected = true;
                }
                moduleSelect.appendChild(opt);
            });
        }
    }

    addSearchFeature() {
        const searchInput = document.querySelector(".o_markdown_search");
        if (!searchInput) return;

        // Премахни стари event listeners
        const newSearchInput = searchInput.cloneNode(true);
        searchInput.replaceWith(newSearchInput);

        newSearchInput.addEventListener("input", () => {
            const query = newSearchInput.value.toLowerCase();
            const contentDiv = document.querySelector(".o_markdown_content");
            if (!contentDiv) return;

            const paragraphs = contentDiv.querySelectorAll("p, li, h1, h2, h3, h4, h5, h6, code, pre");
            paragraphs.forEach(el => {
                if (query && el.textContent.toLowerCase().includes(query)) {
                    el.style.backgroundColor = "yellow";
                } else {
                    el.style.backgroundColor = "";
                }
            });
        });
    }
}

registry.category("actions").add("markdown_popup_dropdown", MarkdownPopupDropdown);
