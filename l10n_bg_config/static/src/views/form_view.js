/** @odoo-module **/
import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";
import { onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

// Constants for shortcut configuration and event
const SHORTCUT_KEY_CONFIG = { shift: true, alt: true, key: "k", keyCode: 75 };
const KEYDOWN_EVENT = "keydown";
const FIELD_NAME = "l10n_bg_key";

export class ApiKeyPartnerFormController extends FormController {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.notification = useService("notification");

        // Shortcut listener setup
        this._handleShortcutKey = this._createShortcutHandler();
        onMounted(() => document.addEventListener(KEYDOWN_EVENT, this._handleShortcutKey));
        onWillUnmount(() => document.removeEventListener(KEYDOWN_EVENT, this._handleShortcutKey));
    }

    _createShortcutHandler() {
        return (event) => {
            if (this._matchesShortcutKey(event)) {
                event.preventDefault();
                this._executeShortcutAction();
            }
        };
    }

    _matchesShortcutKey(event) {
        return (
            event.altKey === SHORTCUT_KEY_CONFIG.alt &&
            event.shiftKey === SHORTCUT_KEY_CONFIG.shift &&
            event.keyCode === SHORTCUT_KEY_CONFIG.keyCode
        );
    }

    _executeShortcutAction() {
        const recordId = this.model?.root?.resId;
        if (recordId) {
            this._fetchAndHandleApiKey(recordId);
        }
    }

    async _fetchAndHandleApiKey(recordId) {
        // Fetch API Key from the backend
        const result = await this.orm.call(
            "res.partner",
            "get_api_key",
            [recordId],
            { context: { ...this.context } }
        );
        console.log(result);
        // Извличане на стойността от резултата
        if (result) {
            const message = _t(`The API Key is: ${result}`);
            this.notification.add(message, { type: "info" });
            // Update the model and focus the field in DOM
            if (this.model?.root) {
                this.model.root.update({ [FIELD_NAME]: result });
                this._focusField(FIELD_NAME);
            } else {
                console.warn(`Field "${FIELD_NAME}" not found!`);
            }
        } else {
            console.warn("No value returned from API call.");
        }
    }

    _focusField(fieldName) {
        // Намерете елемента за полето по неговото име
        const fieldElement = document.querySelector(`[name="${fieldName}"]`);

        if (fieldElement) {
            // Потърсете най-близкия контейнер на полето, който има атрибут name (ако съществува)
            const tabName = fieldElement.closest(".o_group")?.getAttribute("name");

            if (tabName) {
                // Намерете съответния nav-link по атрибута name
                const allTabs = document.querySelectorAll('.o_notebook_headers .nav-link');
                const allContent = document.querySelectorAll('.o_group');

                // Деактивирайте всички табове и съдържателни контейнери
                allTabs.forEach(tab => tab.classList.remove("active"));
                allContent.forEach(content => (content.style.display = "none"));

                // Намерете желания таб и неговото съдържание
                const targetTab = document.querySelector(`.nav-link[name="${tabName}"]`);
                const targetContent = document.querySelector(`.o_group[name="${tabName}"]`);

                if (targetTab && targetContent) {
                    // Активирайте желания таб
                    targetTab.classList.add("active");
                    targetContent.style.display = "block";
                } else {
                    console.warn(`Tab or content with name "${tabName}" not found.`);
                }
            }

            // Поставете фокус върху полето
            fieldElement.focus();
        } else {
            console.warn(`Field with name "${fieldName}" not found.`);
        }
    }
}

// Register the form with the custom controller
registry.category("views").add("api_key_res_partner_form", {
    ...formView,
    Controller: ApiKeyPartnerFormController,
});
