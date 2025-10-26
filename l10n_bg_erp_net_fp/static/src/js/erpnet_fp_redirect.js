/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { useService } from "@web/core/utils/hooks";

/**
 * Хибриден подход за ErpNet.FP интеграция:
 * - Касови бонове (receipts) -> Директно от браузъра към ErpNet.FP
 * - X/Z отчети, служебни операции -> През Odoo backend (erp_net_fp.py)
 */
patch(ReceiptScreen.prototype, {
    setup() {
        super.setup();
        this.notification = useService("notification");
    },

    async doFullPrint() {
        const pos = this.pos || this.env.pos;

        // Намираме конфигурирания фискален принтер
        const printers = pos.orderPrinters || pos.printers || pos.config?.printers || [];
        const fiscalPrinter = printers.find((p) =>
            p.printer_type === 'erp_net_fp' && p.l10n_bg_proxy_ip && p.l10n_bg_printer_id
        );

        // Ако няма конфигуриран фискален принтер -> стандартен печат
        if (!fiscalPrinter) {
            console.log("There is no ErpNet.FP printer configured, standard printing is used");
            return await super.doFullPrint();
        }

        const baseUrl = fiscalPrinter.l10n_bg_proxy_ip;
        const printerId = fiscalPrinter.l10n_bg_printer_id;

        if (!baseUrl || !printerId) {
            console.error("Invalid fiscal printer configuration");
            this.notification.add(
                this.env._t("Fiscal printer configuration error"),
                { type: "danger" }
            );
            return await super.doFullPrint();
        }

        const order = pos.get_order();
        if (!order) {
            return await super.doFullPrint();
        }

        // ДИРЕКТЕН ПЕЧАТ НА КАСОВ БОН ОТ БРАУЗЪРА
        try {
            const receiptData = this._prepareFiscalReceiptData(order, pos);
            const result = await this._sendToFiscalPrinter(baseUrl, printerId, receiptData);

            if (result && result.ok) {
                // Успешен фискален печат
                this.notification.add(
                    this.env._t("Fiscal receipt printed successfully") +
                    (result.receiptNumber ? ` №${result.receiptNumber}` : ""),
                    { type: "success", timeout: 3000 }
                );

                // Запазване на фискалните данни в поръчката
                if (result.receiptNumber || result.fiscalMemorySerialNumber) {
                    order.l10n_bg_fiscal_receipt_number = result.receiptNumber;
                    order.l10n_bg_fiscal_memory_number = result.fiscalMemorySerialNumber;
                }

                return; // НЕ печатаме локално
            } else {
                throw new Error(result?.error || "The printer returned an error");
            }
        } catch (error) {
            console.error("Fiscal stamp error:", error);
            this.notification.add(
                this.env._t("Fiscal stamp error: ") + error.message + ". " +
                this.env._t("A standard seal is used."),
                { type: "warning" }
            );
            return await super.doFullPrint();
        }
    },

    /**
     * Подготовка на данните за ErpNet.FP API
     */
    _prepareFiscalReceiptData(order, pos) {
        const items = [];
        const orderLines = order.get_orderlines();

        for (const line of orderLines) {
            const item = {
                text: line.get_full_product_name?.() || line.product?.display_name || "Продукт",
                quantity: line.get_quantity(),
                unitPrice: line.get_unit_display_price(),
                taxGroup: this._getTaxGroup(line, pos)
            };

            // Добавяне на отстъпка ако има
            const discount = line.get_discount();
            if (discount && discount > 0) {
                item.priceModifierType = "discount-percent";
                item.priceModifierValue = discount;
            }

            items.push(item);
        }

        // Подготовка на плащанията
        const payments = [];
        const paymentLines = order.get_paymentlines();

        for (const payment of paymentLines) {
            payments.push({
                amount: Math.max(0, payment.get_amount()),
                paymentType: this._getPaymentType(payment)
            });
        }

        // Уникален номер на продажбата
        const uniqueSaleNumber = `${pos.config.name || "POS"}-${order.name || order.uid}`;

        return {
            uniqueSaleNumber: uniqueSaleNumber,
            items: items,
            payments: payments
        };
    },

    /**
     * Определяне на данъчната група
     */
    _getTaxGroup(line, pos) {
        const taxes = line.get_taxes?.() || [];

        if (!taxes.length) {
            return 0; // Без ДДС
        }

        const tax = taxes[0];

        // Опит за вземане на група от account.tax.group
        if (tax.tax_group_id) {
            let taxGroup = null;

            if (typeof tax.tax_group_id === 'object') {
                taxGroup = tax.tax_group_id;
            } else if (typeof tax.tax_group_id === 'number') {
                // Търсене в loaded data
                taxGroup = pos.models['account.tax.group']?.find(
                    g => g.id === tax.tax_group_id
                );
            }

            if (taxGroup && taxGroup.l10n_bg_fiscal_tax_group !== undefined) {
                // Маппинг на българските букви към числа за ErpNet.FP
                const groupMap = {
                    'А': 0,  // VAT 0%
                    'Б': 2,  // VAT 20%
                    'В': 2,  // VAT 20%
                    'Г': 3   // VAT 9%
                };
                return groupMap[taxGroup.l10n_bg_fiscal_tax_group] || 0;
            }
        }

        // Fallback по ставка
        const rate = tax.amount || 0;
        if (Math.abs(rate - 20) < 0.001) return 2; // 20%
        if (Math.abs(rate - 9) < 0.001) return 3;  // 9%
        if (Math.abs(rate - 0) < 0.001) return 1;  // 0%

        return 0; // По подразбиране
    },

    /**
     * Определяне на типа плащане
     */
    _getPaymentType(payment) {
        const methodName = (payment.payment_method?.name || "").toLowerCase();

        if (methodName.includes("cash") || methodName.includes("каса") || methodName.includes("кеш")) {
            return "cash";
        }
        if (methodName.includes("card") || methodName.includes("карта")) {
            return "card";
        }

        return "cash"; // По подразбиране
    },

    /**
     * ДИРЕКТНО изпращане към ErpNet.FP сървър от браузъра
     * Използва се само за печат на касови бонове
     */
    async _sendToFiscalPrinter(baseUrl, printerId, data) {
        const url = `${baseUrl.replace(/\/+$/, "")}/printers/${encodeURIComponent(printerId)}/receipt`;
        const timeout = 15000; // 15 секунди за касов бон

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);

        try {
            console.log("Директно изпращане към ErpNet.FP:", url, data);

            const response = await fetch(url, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                body: JSON.stringify(data),
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                const errorText = await response.text();
                console.error("HTTP грешка от ErpNet.FP:", response.status, errorText);
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }

            const result = await response.json();
            console.log("Отговор от ErpNet.FP:", result);

            if (!result.ok) {
                const errorMessages = Array.isArray(result.messages)
                    ? result.messages
                        .filter(m => m.type === "error")
                        .map(m => m.text || m.code)
                        .join("; ")
                    : "Принтерът върна грешка";

                throw new Error(errorMessages || "Неизвестна грешка от принтера");
            }

            return result;

        } catch (error) {
            clearTimeout(timeoutId);

            if (error.name === 'AbortError') {
                console.error("Timeout при комуникация с ErpNet.FP");
                throw new Error("Времето за изчакване изтече");
            }

            console.error("Грешка при изпращане към ErpNet.FP:", error);
            throw error;
        }
    }
});
