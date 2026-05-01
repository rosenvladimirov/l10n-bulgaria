/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";

/**
 * Datecs PM Fiscal Printer — frontend facade.
 *
 * Browser ──fetch()──▶ Odoo.ErpNet.FP service (shop machine)
 *                     │
 *                     └──serial/TCP──▶ Datecs FP-700 MX
 *
 * The proxy speaks 100% ErpNet.FP-compatible HTTP, so this class is
 * essentially a clone of `ErpNetFPPrinter` from the sibling
 * `l10n_bg_erp_net_fp` module — just defaulted to our PM driver.
 */
export class DatecsPMPrinter {
    /**
     * @param {Object} env - Odoo environment
     * @param {Object} params - { proxyUrl, printerId, posConfigId, sessionId }
     */
    constructor(env, params) {
        this.env = env || {};
        this.baseUrl = (params?.proxyUrl || "").replace(/\/+$/, "");
        this.printerId = params?.printerId || "";
        this.posConfigId = params?.posConfigId;
        this.sessionId = params?.sessionId;

        if (!this.baseUrl || !this.printerId) {
            console.error(
                "[DatecsPM] Missing proxyUrl/printerId — printer will not work"
            );
        }
    }

    // ─── status ──────────────────────────────────────────────────

    async getStatus() {
        if (!this._configured()) return { successful: false, online: false };
        try {
            const url = `${this.baseUrl}/printers/${encodeURIComponent(this.printerId)}/status`;
            const response = await this._fetch(url, { method: "GET" }, 5000);
            const result = await response.json();
            return {
                successful: true,
                online: !!result.ok,
                deviceDateTime: result.deviceDateTime,
                messages: result.messages,
            };
        } catch (error) {
            console.error("[DatecsPM] status error:", error);
            return { successful: false, online: false };
        }
    }

    // ─── fiscal receipt ──────────────────────────────────────────

    async printReceipt(order) {
        if (!this._configured()) return this._configError();
        if (!order) return this._fail(_t("Missing order"), _t("No order to fiscalize."));

        const payload = this._buildReceiptPayload(order);
        if (!payload.items.length) {
            return this._fail(
                _t("Empty receipt"),
                _t("Order has no fiscalizable items."),
            );
        }

        try {
            const url = `${this.baseUrl}/printers/${encodeURIComponent(this.printerId)}/receipt`;
            const response = await this._fetch(url, {
                method: "POST",
                headers: { "Content-Type": "application/json", Accept: "application/json" },
                body: JSON.stringify(payload),
            });
            const result = await response.json();
            return this._handleReceiptResult(result, order);
        } catch (error) {
            console.error("[DatecsPM] printReceipt error:", error);
            return this._fail(
                _t("Communication error"),
                error.message,
                "DATECS_PM_HTTP_ERROR",
            );
        }
    }

    _handleReceiptResult(result, order) {
        if (!result || !result.ok) {
            return this._fail(
                _t("Datecs PM error"),
                this._extractErrorMessages(result) || _t("Unknown error"),
                result?.messages?.[0]?.code,
            );
        }
        order.l10n_bg_fp_datecs_receipt_number = String(result.receiptNumber || "");
        order.l10n_bg_fp_datecs_receipt_datetime = (result.receiptDateTime || "")
            .replace("T", " ")
            .replace("Z", "")
            .split(".")[0];
        order.l10n_bg_fp_datecs_fm_number = result.fiscalMemorySerialNumber || "";
        order.l10n_bg_fp_datecs_uns = payload?.uniqueSaleNumber || order.l10n_bg_fp_datecs_uns;
        order.l10n_bg_fp_datecs_is_fiscalized = true;

        return {
            successful: true,
            fiscalData: {
                receiptNumber: result.receiptNumber,
                receiptDateTime: result.receiptDateTime,
                fiscalMemorySerialNumber: result.fiscalMemorySerialNumber,
            },
        };
    }

    _buildReceiptPayload(order) {
        const items = [];
        const orderLines = order.lines || order.get_orderlines?.() || [];
        for (const line of orderLines) {
            const qty = line.get_quantity?.() ?? line.qty ?? 0;
            if (qty === 0) continue;
            const unitPrice = line.get_unit_display_price?.() ?? line.price ?? 0;
            const discount = line.get_discount?.() ?? line.discount ?? 0;
            const item = {
                type: "sale",
                text:
                    line.get_full_product_name?.() ||
                    line.full_product_name ||
                    line.product?.display_name ||
                    line.product_id?.display_name ||
                    _t("Product"),
                quantity: Math.abs(qty),
                unitPrice: Math.abs(unitPrice),
                taxGroup: this._getTaxGroup(line, order),
            };
            if (discount > 0) {
                item.priceModifierType = "discount-percent";
                item.priceModifierValue = discount;
            }
            items.push(item);
        }

        const payments = [];
        const paymentLines = order.payment_ids || order.get_paymentlines?.() || [];
        for (const pay of paymentLines) {
            const amount = pay.get_amount?.() ?? pay.amount ?? 0;
            if (amount <= 0) continue;
            payments.push({
                amount: Math.abs(amount),
                paymentType: this._getPaymentType(pay),
            });
        }

        return {
            uniqueSaleNumber: this._formatUns(order),
            items,
            payments,
        };
    }

    /**
     * Resolve taxGroup integer (1..8) per ErpNet.FP convention.
     * Falls back to 1 (А = 20% in default mapping).
     */
    _getTaxGroup(line, order) {
        const taxes = line.tax_ids || line.get_taxes?.() || [];
        if (!taxes.length) return 1;
        const tax = taxes[0];
        const pos = order.pos || order;

        let group = null;
        if (typeof tax.tax_group_id === "object") {
            group = tax.tax_group_id;
        } else if (typeof tax.tax_group_id === "number") {
            group = pos?.models?.["account.tax.group"]?.find?.(
                (g) => g.id === tax.tax_group_id,
            );
        }
        if (group?.l10n_bg_fp_datecs_tax_group) {
            const map = { А: 1, Б: 2, В: 3, Г: 4, Д: 5, Е: 6, Ж: 7, З: 8 };
            return map[group.l10n_bg_fp_datecs_tax_group] || 1;
        }
        // Heuristic by tax % rate
        const rate = tax.amount ?? 0;
        if (Math.abs(rate - 20) < 0.001) return 1;
        if (Math.abs(rate - 9) < 0.001) return 2;
        if (Math.abs(rate - 0) < 0.001) return 3;
        return 1;
    }

    _getPaymentType(pay) {
        const name = (
            pay.payment_method?.name ||
            pay.payment_method_id?.name ||
            pay.name ||
            ""
        ).toLowerCase();
        if (name.includes("card") || name.includes("карта")) return "card";
        if (name.includes("bank")) return "bank";
        return "cash";
    }

    _formatUns(order) {
        const prefix = "DT";
        const session = String(this.sessionId || 0).padStart(4, "0").slice(-4);
        const orderNum = String(order.id || order.sequence_number || 1);
        const orderSeq = orderNum.padStart(7, "0").slice(-7);
        return `${prefix}000000-${session}-${orderSeq}`;
    }

    // ─── cash ops ────────────────────────────────────────────────

    async cashIn(amount, reason = "") {
        return this._post("/deposit", { amount, text: reason });
    }
    async cashOut(amount, reason = "") {
        return this._post("/withdraw", { amount, text: reason });
    }

    // ─── reports ─────────────────────────────────────────────────

    async printXReport() {
        return this._post("/xreport");
    }
    async printZReport() {
        return this._post("/zreport");
    }
    async printDuplicate() {
        return this._post("/duplicate");
    }

    // ─── helpers ─────────────────────────────────────────────────

    _configured() {
        return !!this.baseUrl && !!this.printerId;
    }

    _configError() {
        return {
            successful: false,
            message: {
                title: _t("Configuration error"),
                body: _t("Datecs PM proxy is not configured."),
            },
            errorCode: "DATECS_PM_CONFIG_ERROR",
        };
    }

    _fail(title, body, errorCode) {
        return {
            successful: false,
            message: { title, body: body || _t("Unknown error") },
            errorCode: errorCode || "DATECS_PM_ERROR",
        };
    }

    async _post(path, body = null) {
        if (!this._configured()) return this._configError();
        try {
            const url = `${this.baseUrl}/printers/${encodeURIComponent(this.printerId)}${path}`;
            const response = await this._fetch(url, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Accept: "application/json",
                },
                body: body ? JSON.stringify(body) : null,
            });
            return await response.json();
        } catch (error) {
            return this._fail(_t("Proxy error"), error.message);
        }
    }

    async _fetch(url, options = {}, timeout = 15000) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);
        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal,
            });
            clearTimeout(timeoutId);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response;
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === "AbortError") {
                throw new Error(_t("Timeout connecting to fiscal proxy"));
            }
            throw error;
        }
    }

    _extractErrorMessages(result) {
        if (Array.isArray(result?.messages)) {
            return result.messages
                .filter((m) => m.type === "error")
                .map((m) => m.text || m.code || "")
                .join("; ");
        }
        return "";
    }
}
