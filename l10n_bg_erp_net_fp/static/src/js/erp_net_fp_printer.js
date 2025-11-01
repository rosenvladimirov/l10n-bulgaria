/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";

/**
 * ErpNet.FP Fiscal Printer - Самостоятелен клас
 *
 * ВАЖНО: НЕ наследява BasePrinter!
 * BasePrinter е за физически принтери (canvas -> image -> IoT Box)
 * ErpNetFPPrinter е за fiscal принтери (order data -> JSON API -> Fiscal Device)
 *
 * Това са два РАЗЛИЧНИ типа принтери с различна логика!
 */
export class ErpNetFPPrinter {
    /**
     * @param {Object} env - Odoo environment
     * @param {Object} params - Setup parameters
     */
    constructor(env, params) {
        this.env = env || {};

        if (params) {
            this._setupFiscalPrinter(params);
        }
    }

    _setupFiscalPrinter(params) {
        if (!params) {
            console.error("[ErpNetFPPrinter] setup called without params!");
            return;
        }

        console.log("[ErpNetFPPrinter] Setting up fiscal printer...");
        console.log("[ErpNetFPPrinter]    Base URL:", params.baseUrl);
        console.log("[ErpNetFPPrinter]    Printer ID:", params.printerId);

        this.baseUrl = params.baseUrl?.replace(/\/+$/, "") || "";
        this.printerId = params.printerId || "";

        if (!this.baseUrl || !this.printerId) {
            console.error("[ErpNetFPPrinter] Missing required parameters!");
        }
    }

    /**
     * Печат на фискален касов бон
     *
     * ВАЖНО: Това НЕ Е override на BasePrinter.printReceipt()
     * Това е самостоятелен метод който работи с order objects
     *
     * @param {Object} order - POS Order обект от Odoo
     * @returns {Promise<Object>} Result with successful flag and optional fiscalData
     */
    async printReceipt(order) {
        console.log("[ErpNetFPPrinter] ═══════════════════════════════════════");
        console.log("[ErpNetFPPrinter] 🎯 printReceipt() called");
        console.log("[ErpNetFPPrinter] ═══════════════════════════════════════");
        console.log("[ErpNetFPPrinter]    Order:", order?.name);
        console.log("[ErpNetFPPrinter]    Lines:", order?.lines?.length);

        if (!this.baseUrl || !this.printerId) {
            console.error("[ErpNetFPPrinter] ❌ Printer not configured!");
            return this.getConfigError();
        }

        if (!order) {
            console.error("[ErpNetFPPrinter] ❌ No order provided!");
            return {
                successful: false,
                message: {
                    title: _t("Липсва поръчка"),
                    body: _t("Няма поръчка за печат."),
                },
            };
        }

        // Валидация на order
        if (!order.lines && !order.get_orderlines) {
            console.error("[ErpNetFPPrinter] ❌ Order missing lines!");
            return {
                successful: false,
                message: {
                    title: _t("Невалидна поръчка"),
                    body: _t("Поръчката няма продуктови линии."),
                },
            };
        }

        console.log("[ErpNetFPPrinter] ✅ Valid order received");

        // Взимаме pos config от order ако е налично
        const posConfig = order.pos?.config || order.config || { name: "POS" };

        // Подготвяме данните за фискален бон
        const receiptData = this._prepareFiscalReceiptData(order, posConfig);

        console.log("[ErpNetFPPrinter] 📋 Receipt data prepared:");
        console.log("[ErpNetFPPrinter]    Unique sale number:", receiptData.uniqueSaleNumber);
        console.log("[ErpNetFPPrinter]    Items count:", receiptData.items.length);
        console.log("[ErpNetFPPrinter]    Payments count:", receiptData.payments.length);

        try {
            // Изпращаме към fiscal printer
            const result = await this._sendToFiscalPrinter(receiptData);

            if (result && result.ok) {
                console.log("[ErpNetFPPrinter] ✅ Fiscal print SUCCESS!");
                console.log("[ErpNetFPPrinter]    Receipt #:", result.receiptNumber);
                console.log("[ErpNetFPPrinter]    Fiscal Memory #:", result.fiscalMemorySerialNumber);

                return {
                    successful: true,
                    fiscalData: {
                        receiptNumber: result.receiptNumber,
                        fiscalMemorySerialNumber: result.fiscalMemorySerialNumber,
                    },
                };
            } else {
                throw new Error(result?.error || _t("Принтерът върна грешка"));
            }
        } catch (error) {
            console.error("[ErpNetFPPrinter] ❌ Printing error:", error);
            return {
                successful: false,
                message: {
                    title: _t("Грешка при фискален печат"),
                    body: error.message || _t("Неизвестна грешка"),
                },
                errorCode: "ERPNET_FP_ERROR",
            };
        }
    }

    /**
     * Отваряне на касов чекмедже
     */
    async openCashbox() {
        if (!this.baseUrl || !this.printerId) {
            return false;
        }

        try {
            const url = `${this.baseUrl}/printers/${encodeURIComponent(this.printerId)}/cashbox`;
            const response = await this._fetchWithTimeout(url, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const result = await response.json();
            return result.ok;
        } catch (error) {
            console.error("[ErpNetFPPrinter] Error opening cashbox:", error);
            return false;
        }
    }

    /**
     * Подготвя данните за фискален бон
     *
     * @param {Object} order - POS Order обект
     * @param {Object} posConfig - POS Configuration
     * @returns {Object} Fiscal receipt data
     */
    _prepareFiscalReceiptData(order, posConfig) {
        const items = [];

        // В Odoo 18 е order.lines
        const orderLines = order.lines || order.get_orderlines?.() || [];

        for (const line of orderLines) {
            const item = {
                text: line.get_full_product_name?.() ||
                      line.full_product_name ||
                      line.product?.display_name ||
                      _t("Продукт"),
                quantity: line.get_quantity?.() || line.qty || 0,
                unitPrice: line.get_unit_display_price?.() || line.price || 0,
                taxGroup: this._getTaxGroup(line, order),
            };

            const discount = line.get_discount?.() || line.discount || 0;
            if (discount && discount > 0) {
                item.priceModifierType = "discount-percent";
                item.priceModifierValue = discount;
            }

            items.push(item);
        }

        const payments = [];

        // В Odoo 18 е order.payment_ids
        const paymentLines = order.payment_ids || order.get_paymentlines?.() || [];

        for (const payment of paymentLines) {
            const paymentAmount = Math.max(0, payment.get_amount?.() || payment.amount || 0);
            const paymentType = this._getPaymentType(payment);

            payments.push({
                amount: paymentAmount,
                paymentType: paymentType,
            });
        }

        // Уникален номер на продажбата
        const uniqueSaleNumber = `${posConfig?.name || "POS"}-${order.name || order.uid}`;

        return {
            uniqueSaleNumber: uniqueSaleNumber,
            items: items,
            payments: payments,
        };
    }

    /**
     * Определя фискалната данъчна група
     */
    _getTaxGroup(line, order) {
        const taxes = line.tax_ids || line.get_taxes?.() || [];

        if (!taxes.length) {
            return 0;
        }

        const tax = taxes[0];

        if (tax.tax_group_id) {
            let taxGroup = null;

            if (typeof tax.tax_group_id === "object") {
                taxGroup = tax.tax_group_id;
            } else if (typeof tax.tax_group_id === "number") {
                const pos = order.pos || order;

                taxGroup = pos.models?.["account.tax.group"]?.find?.(
                    (g) => g.id === tax.tax_group_id
                );

                if (!taxGroup) {
                    taxGroup = pos.db?.tax_group_by_id?.[tax.tax_group_id];
                }
            }

            if (taxGroup && taxGroup.l10n_bg_fiscal_tax_group !== undefined) {
                const groupMap = { А: 0, Б: 2, В: 2, Г: 3 };
                return groupMap[taxGroup.l10n_bg_fiscal_tax_group] || 0;
            }
        }

        // Fallback към ръчно определяне по процент
        const rate = tax.amount || 0;
        if (Math.abs(rate - 20) < 0.001) return 2;  // 20% ДДС
        if (Math.abs(rate - 9) < 0.001) return 3;   // 9% ДДС
        if (Math.abs(rate - 0) < 0.001) return 1;   // 0% ДДС

        return 0;
    }

    /**
     * Определя типа на плащането
     */
    _getPaymentType(payment) {
        const methodName = (payment.payment_method?.name || payment.name || "").toLowerCase();

        if (
            methodName.includes("cash") ||
            methodName.includes("каса") ||
            methodName.includes("кеш")
        ) {
            return "cash";
        }
        if (methodName.includes("card") || methodName.includes("карта")) {
            return "card";
        }

        return "cash";
    }

    /**
     * Изпраща заявка към fiscal printer
     */
    async _sendToFiscalPrinter(data) {
        const url = `${this.baseUrl}/printers/${encodeURIComponent(this.printerId)}/receipt`;

        console.log("[ErpNetFPPrinter] 🌐 POST to:", url);
        console.log("[ErpNetFPPrinter] 📤 Data:", data);

        const response = await this._fetchWithTimeout(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            body: JSON.stringify(data),
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error("[ErpNetFPPrinter] ❌ HTTP error:", response.status, errorText);
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        const result = await response.json();
        console.log("[ErpNetFPPrinter] 📥 Response:", result);

        if (!result.ok) {
            const errorMessages = Array.isArray(result.messages)
                ? result.messages
                      .filter((m) => m.type === "error")
                      .map((m) => m.text || m.code)
                      .join("; ")
                : _t("Принтерът върна грешка");

            throw new Error(errorMessages || _t("Неизвестна грешка от принтера"));
        }

        return result;
    }

    /**
     * Fetch с timeout
     */
    async _fetchWithTimeout(url, options = {}, timeout = 15000) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);

        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal,
            });
            clearTimeout(timeoutId);
            return response;
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === "AbortError") {
                throw new Error(_t("Timeout при връзка с принтера"));
            }
            throw error;
        }
    }

    /**
     * Error методи
     */
    getConfigError() {
        return {
            successful: false,
            message: {
                title: _t("Грешка в конфигурацията"),
                body: _t("ErpNet.FP принтерът не е правилно конфигуриран."),
            },
            errorCode: "ERPNET_FP_CONFIG_ERROR",
        };
    }
}
