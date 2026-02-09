/** @odoo-module **/

import { Component, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { FormController } from "@web/views/form/form_controller";
import { registry } from "@web/core/registry";

export class CustomsDeclarationFormController extends FormController {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.dialog = useService("dialog");

        onWillStart(async () => {
            if (this.model.root.resId) {
                await this.loadCustomsDocuments();
            }
        });
    }

    async loadCustomsDocuments() {
        try {
            const nomenclatureData = await this.orm.searchRead(
                "l10n.bg.customs.nomenclature",
                [['type', '=', 'document']],
                ['name', 'code', 'description']
            );
            this.customsDocuments = nomenclatureData;
        } catch (error) {
            console.error("Error loading customs documents:", error);
        }
    }

    async validateCustomsDeclaration() {
        const record = this.model.root;
        const errors = [];

        // Валидация на задължителни полета
        if (!record.data.declaration_number) {
            errors.push("MRN номерът е задължителен");
        }

        if (!record.data.partner_id) {
            errors.push("Партньорът е задължителен");
        }

        if (!record.data.declaration_date) {
            errors.push("Датата на декларацията е задължителна");
        }

        // Валидация на стоковите редове
        const goodsLines = record.data.invoice_line_ids.records.filter(
            line => !line.data.display_type
        );

        if (goodsLines.length === 0) {
            errors.push("Трябва да добавите поне една стока");
        }

        for (const line of goodsLines) {
            if (!line.data.name) {
                errors.push(`Описанието на стока е задължително`);
            }
            if (!line.data.product_id && !line.data.name.includes("КН:")) {
                errors.push(`КН кодът трябва да бъде указан в описанието или чрез продукт`);
            }
            if (!line.data.l10n_bg_customs_value || line.data.l10n_bg_customs_value <= 0) {
                errors.push(`Митническата стойност на стока "${line.data.name || 'Неназована'}" трябва да бъде положителна`);
            }
        }

        return errors;
    }

    async onSave() {
        const errors = await this.validateCustomsDeclaration();

        if (errors.length > 0) {
            this.notification.add(
                errors.join('\n'),
                { type: 'danger', title: 'Грешки при валидация:' }
            );
            return false;
        }

        return super.onSave();
    }

    async onSubmitDeclaration() {
        const errors = await this.validateCustomsDeclaration();

        if (errors.length > 0) {
            this.notification.add(
                errors.join('\n'),
                { type: 'danger', title: 'Декларацията не може да бъде подадена:' }
            );
            return;
        }

        try {
            await this.orm.call(
                this.model.root.resModel,
                'action_submit_declaration',
                [this.model.root.resId]
            );

            this.notification.add(
                'Декларацията беше успешно подадена.',
                { type: 'success', title: 'Успех!' }
            );

            this.model.root.load();
        } catch (error) {
            this.notification.add(
                'Възникна грешка при подаване на декларацията.',
                { type: 'danger', title: 'Грешка!' }
            );
        }
    }

    async generateMRN() {
        try {
            const result = await this.orm.call(
                this.model.root.resModel,
                'generate_mrn_number',
                [this.model.root.resId]
            );

            if (result.mrn) {
                await this.model.root.update({ declaration_number: result.mrn });
                this.notification.add(
                    `Генериран MRN номер: ${result.mrn}`,
                    { type: 'success' }
                );
            }
        } catch (error) {
            this.notification.add(
                'Възникна грешка при генериране на MRN номер.',
                { type: 'danger', title: 'Грешка!' }
            );
        }
    }
}

// Customs goods widget за по-добро визуализиране
export class CustomsGoodsWidget extends Component {
    static template = "CustomsGoodsWidget";
    static props = {
        record: Object,
        readonly: { type: Boolean, optional: true },
    };

    setup() {
        this.orm = useService("orm");
    }

    get totalCustomsValue() {
        return this.props.record.data.invoice_line_ids.records
            .filter(line => !line.data.display_type && !line.data.l10n_bg_is_customs_expense)
            .reduce((total, line) => total + (line.data.l10n_bg_customs_value || 0), 0);
    }

    get totalExpenses() {
        return this.props.record.data.invoice_line_ids.records
            .filter(line => line.data.l10n_bg_is_customs_expense)
            .reduce((total, line) => total + (line.data.price_total || 0), 0);
    }

    get totalWeight() {
        return this.props.record.data.invoice_line_ids.records
            .filter(line => !line.data.display_type)
            .reduce((total, line) => total + (line.data.l10n_bg_weight_gross || 0), 0);
    }

    formatCurrency(value) {
        return new Intl.NumberFormat('bg-BG', {
            style: 'currency',
            currency: this.props.record.data.currency_id ? this.props.record.data.currency_id[1] : 'EUR'
        }).format(value || 0);
    }
}

// Регистрираме компонентите
registry.category("views").add("account_move_bg_customs_form", {
    type: "form",
    display_name: "BG Customs Declaration Form",
    Controller: CustomsDeclarationFormController,
});

registry.category("fields").add("customs_goods_widget", CustomsGoodsWidget);
