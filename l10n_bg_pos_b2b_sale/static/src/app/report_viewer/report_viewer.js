import { Component } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

/**
 * Печатите на офертата в десния екран на касата — над продуктите, със
 * затваряне; нов прозорец не се отваря (ADR specs/pos-b2b-wholesale/0003).
 */
export class L10nBgReportViewer extends Component {
    static template = "l10n_bg_pos_b2b_sale.ReportViewer";
    static props = {};

    setup() {
        this.pos = usePos();
    }

    get report() {
        return this.pos.l10nBgReport;
    }

    /**
     * PDF-ът през визуализатора pdf.js на Odoo — както прегледа на файлове
     * в бекофиса (web/core/file_viewer/file_model.js). Вграден направо,
     * PDF-ът зависи от визуализатора на браузъра: Firefox с „свали PDF“ и
     * таблетите показват празна рамка.
     */
    get viewerUrl() {
        const url = this.report?.url;
        return url
            ? `/web/static/lib/pdfjs/web/viewer.html?file=${encodeURIComponent(url)}#pagemode=none`
            : "";
    }

    close() {
        this.pos.l10nBgReport = null;
    }
}

patch(PosStore.prototype, {
    async setup() {
        this.l10nBgReport = null;
        return await super.setup(...arguments);
    },
});

patch(ProductScreen, {
    components: { ...ProductScreen.components, L10nBgReportViewer },
});
