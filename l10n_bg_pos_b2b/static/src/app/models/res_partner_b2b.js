import { ResPartner } from "@point_of_sale/app/models/res_partner";
import { patch } from "@web/core/utils/patch";

patch(ResPartner.prototype, {
    /** Търсене на клиент и по ЕИК (котвата §9). */
    get searchString() {
        const base = super.searchString;
        if (this.l10n_bg_uic && !base.includes(this.l10n_bg_uic)) {
            this._searchString = `${base} ${this.l10n_bg_uic}`;
            return this._searchString;
        }
        return base;
    },
});
