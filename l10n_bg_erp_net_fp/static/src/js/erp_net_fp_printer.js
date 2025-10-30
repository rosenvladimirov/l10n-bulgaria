/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { BasePrinter } from "@point_of_sale/app/printer/base_printer";

/**
 * ErpNet.FP Fiscal Printer - Директна комуникация от браузъра
 * Използва се за печат на фискални касови бонове
 */
export class ErpNetFPPrinter extends BasePrinter {
    /**
     * @param {Object} params
     * @param {string} params.baseUrl - ErpNet.FP сървър адрес
     * @param {string} params.printerId - ID на принтера
     * @param {Object} params.pos - POS инстанция
     */
    setup(params) {
        super.setup(...arguments);
        this.baseUrl = params.baseUrl?.replace(/\/+$/, "");
        this.printerId = params.printerId;
        this.pos = params.pos;
    }

    /**
     * @override
     * Печат на фискален касов бон директно през ErpNet.FP API
     */
    async printReceipt(receipt) {
        if (!this.baseUrl || !this.printerId) {
            return this.getConfigError();
        }

        const order = this.pos.get_order();
        if (!order) {
            return {
                successful: false,
                message: {
                    title: _t("No order"),
                    body: _t("There is no active order to print."),
                },
            };
        }

        const receiptData = this._prepareFiscalReceiptData(order);

        try {
            const result = await this._sendToFiscalPrinter(receiptData);

            if (result && result.ok) {
                if (result.receiptNumber || result.fiscalMemorySerialNumber) {
                    order.l10n_bg_fiscal_receipt_number = result.receiptNumber;
                    order.l10n_bg_fiscal_memory_number = result.fiscalMemorySerialNumber;
                }

                return {
                    successful: true,
                    fiscalData: {
                        receiptNumber: result.receiptNumber,
                        fiscalMemorySerialNumber: result.fiscalMemorySerialNumber,
                    },
                };
            } else {
                throw new Error(result?.error || _t("The printer returned an error"));
            }
        } catch (error) {
            console.error("ErpNet.FP printing error:", error);
            return {
                successful: false,
                message: {
                    title: _t("Fiscal printing error"),
                    body: error.message || _t("Unknown error occurred"),
                },
                errorCode: "ERPNET_FP_ERROR",
            };
        }
    }

    async sendPrintingJob(_image) {
        throw new Error("Use printReceipt() directly for fiscal printing");
    }

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
            console.error("Error opening cashbox:", error);
            return false;
        }
    }

    _prepareFiscalReceiptData(order) {
        const items = [];
        const orderLines = order.get_orderlines();

        for (const line of orderLines) {
            const item = {
                text: line.get_full_product_name?.() || line.product?.display_name || _t("Product"),
                quantity: line.get_quantity(),
                unitPrice: line.get_unit_display_price(),
                taxGroup: this._getTaxGroup(line),
            };

            const discount = line.get_discount();
            if (discount && discount > 0) {
                item.priceModifierType = "discount-percent";
                item.priceModifierValue = discount;
            }

            items.push(item);
        }

        const payments = [];
        const paymentLines = order.get_paymentlines();

        for (const payment of paymentLines) {
            payments.push({
                amount: Math.max(0, payment.get_amount()),
                paymentType: this._getPaymentType(payment),
            });
        }

        const uniqueSaleNumber = `${this.pos.config.name || "POS"}-${order.name || order.uid}`;

        return {
            uniqueSaleNumber: uniqueSaleNumber,
            items: items,
            payments: payments,
        };
    }

    _getTaxGroup(line) {
        const taxes = line.get_taxes?.() || [];

        if (!taxes.length) {
            return 0;
        }

        const tax = taxes[0];

        if (tax.tax_group_id) {
            let taxGroup = null;

            if (typeof tax.tax_group_id === "object") {
                taxGroup = tax.tax_group_id;
            } else if (typeof tax.tax_group_id === "number") {
                taxGroup = this.pos.models["account.tax.group"]?.find(
                    (g) => g.id === tax.tax_group_id
                );
            }

            if (taxGroup && taxGroup.l10n_bg_fiscal_tax_group !== undefined) {
                const groupMap = {
                    А: 0,
                    Б: 2,
                    В: 2,
                    Г: 3,
                };
                return groupMap[taxGroup.l10n_bg_fiscal_tax_group] || 0;
            }
        }

        const rate = tax.amount || 0;
        if (Math.abs(rate - 20) < 0.001) return 2;
        if (Math.abs(rate - 9) < 0.001) return 3;
        if (Math.abs(rate - 0) < 0.001) return 1;

        return 0;
    }

    _getPaymentType(payment) {
        const methodName = (payment.payment_method?.name || "").toLowerCase();

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

    async _sendToFiscalPrinter(data) {
        const url = `${this.baseUrl}/printers/${encodeURIComponent(this.printerId)}/receipt`;

        console.log("ErpNet.FP Request:", url, data);

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
            console.error("ErpNet.FP HTTP error:", response.status, errorText);
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        const result = await response.json();
        console.log("ErpNet.FP Response:", result);

        if (!result.ok) {
            const errorMessages = Array.isArray(result.messages)
                ? result.messages
                      .filter((m) => m.type === "error")
                      .map((m) => m.text || m.code)
                      .join("; ")
                : _t("Printer returned an error");

            throw new Error(errorMessages || _t("Unknown printer error"));
        }

        return result;
    }

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
                throw new Error(_t("Connection timeout"));
            }
            throw error;
        }
    }

    getConfigError() {
        return {
            successful: false,
            message: {
                title: _t("Configuration error"),
                body: _t("ErpNet.FP printer is not properly configured."),
            },
            errorCode: "ERPNET_FP_CONFIG_ERROR",
        };
    }

    getActionError() {
        return {
            successful: false,
            message: {
                title: _t("Connection to ErpNet.FP failed"),
                body: _t("Please check if the ErpNet.FP service is running."),
            },
            errorCode: "ERPNET_FP_CONNECTION_ERROR",
        };
    }

    getResultsError(printResult) {
        return {
            successful: false,
            message: {
                title: _t("Fiscal printer error"),
                body: _t("The fiscal printer returned an error. Please check the printer status."),
            },
            errorCode: "ERPNET_FP_PRINTER_ERROR",
        };
    }
}
