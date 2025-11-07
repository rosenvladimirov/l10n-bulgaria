/** @odoo-module **/
import { Component, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";

class MarkdownPopupSimple extends Component {
    static template = "markdown_viewer.MarkdownModal";

    setup() {
        onMounted(() => {
            this.initEvents();
        });
    }

    initEvents() {
        document.querySelectorAll(".o_show_markdown").forEach(link => {
            link.addEventListener("click", async (e) => {
                e.preventDefault();
                await this.loadMarkdown(link);
            });
        });
    }

    async loadMarkdown(link) {
        try {
            const moduleName = link.dataset.mdModule || 'markdown_viewer_locale';
            const fileNameBase = link.dataset.mdFile;
            const lang = odoo.session.user_context.lang || 'en_US';
            const suffix = lang.split('_')[0]; // bg, en, etc.
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

            const modalEl = document.querySelector(".o_markdown_modal");
            if (modalEl) {
                const modal = new bootstrap.Modal(modalEl);
                modal.show();
            }
        } catch (error) {
            console.error("Грешка при зареждане на Markdown:", error);
            alert(`Грешка: ${error.message}`);
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

            const paragraphs = contentDiv.querySelectorAll("p, li, h1, h2, h3, h4, h5, h6");
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

registry.category("actions").add("markdown_popup_simple", MarkdownPopupSimple);
