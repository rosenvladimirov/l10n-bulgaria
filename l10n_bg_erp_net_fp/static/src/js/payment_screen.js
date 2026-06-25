/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ErpNetFPPrinter } from "@l10n_bg_erp_net_fp/js/erp_net_fp_printer";

console.log("[FiscalPayment] 🔧 Loading Fiscal Payment Extension (v18)...");

// Odoo 18: order validation все още живее в PaymentScreen.prototype.validateOrder().
// (OrderPaymentValidation.finalizeValidation е v19-only — затова hook-ваме validateOrder.)
patch(PaymentScreen.prototype, {

    async validateOrder(isForceValidate) {
        console.log("[FiscalPayment] ═══════════════════════════════════════");
        console.log("[FiscalPayment] 🎯 validateOrder() called");
        console.log("[FiscalPayment] ═══════════════════════════════════════");

        const order = this.currentOrder;

        // GUARD: ако този order вече е fiscalised в предишен failed опит, не печатай пак.
        if (order?.l10n_bg_is_fiscalized) {
            console.log("[FiscalPayment] ⏭ Order already fiscalised — skipping reprint, delegating to super");
            return await super.validateOrder(isForceValidate);
        }

        console.log("[FiscalPayment] Current order:", order);
        console.log("[FiscalPayment] Order name:", order?.name);
        console.log("[FiscalPayment] Order lines:", order?.lines?.length);

        window.__fiscalPrinterCurrentOrder = order;
        window.__fiscalPrinterPosStore = this.pos;

        const fiscalPrinterHost = this.pos.session?.l10n_bg_erp_net_fp_host;
        const fiscalPrinterId = this.pos.session?.l10n_bg_erp_net_fp_ip;

        console.log("[FiscalPayment] Fiscal printer host:", fiscalPrinterHost);
        console.log("[FiscalPayment] Fiscal printer ID:", fiscalPrinterId);

        const notification = this.env?.services?.notification || this.pos.env?.services?.notification;

        if (fiscalPrinterHost && fiscalPrinterId && order) {
            console.log("[FiscalPayment] 🚀 Fiscal printer configured, checking order type...");

            const refundInfo = this._getRefundInfo(order);
            console.log("[FiscalPayment] Is refund order:", refundInfo.isRefund);

            try {
                const fiscalPrinter = new ErpNetFPPrinter(this.env, {
                    baseUrl: fiscalPrinterHost,
                    printerId: fiscalPrinterId,
                });

                let result;

                if (refundInfo.isRefund && refundInfo.originalOrder) {
                    console.log("[FiscalPayment] 🔄 Processing REFUND order...");
                    console.log("[FiscalPayment] Original order:", refundInfo.originalOrder.name);

                    const reason = this._getRefundReason(order);
                    console.log("[FiscalPayment] Refund reason:", reason);

                    result = await fiscalPrinter.printReversalReceipt(
                        refundInfo.originalOrder,
                        order,
                        reason
                    );
                } else {
                    console.log("[FiscalPayment] 📄 Processing NORMAL order...");
                    result = await fiscalPrinter.printReceipt(order);
                }

                console.log("[FiscalPayment] Fiscal printer result:", result);

                if (result.successful) {
                    console.log("[FiscalPayment] ✅ Fiscal print SUCCESS!");
                    console.log("[FiscalPayment] Receipt #:", result.fiscalData?.receiptNumber);
                    console.log("[FiscalPayment] Fiscal Memory #:", result.fiscalData?.fiscalMemorySerialNumber);

                    order.l10n_bg_fiscal_receipt_number = result.fiscalData?.receiptNumber;
                    order.l10n_bg_fiscal_memory_number = result.fiscalData?.fiscalMemorySerialNumber;
                    order.l10n_bg_is_fiscalized = true;

                    if (refundInfo.isRefund) {
                        order.l10n_bg_is_reversal = true;
                    }

                    window.__fiscalPrinterCurrentOrder.l10n_bg_is_fiscalized = true;
                    window.__fiscalPrinterCurrentOrder.l10n_bg_fiscal_receipt_number = result.fiscalData?.receiptNumber;
                    window.__fiscalPrinterCurrentOrder.l10n_bg_fiscal_memory_number = result.fiscalData?.fiscalMemorySerialNumber;

                    if (notification) {
                        const message = refundInfo.isRefund
                            ? _t("Сторно бон отпечатан ")
                            : _t("Фискален бон отпечатан ");

                        notification.add(
                            message +
                            (result.fiscalData?.receiptNumber ? `№${result.fiscalData.receiptNumber}` : ""),
                            { type: "success" }
                        );
                    }
                } else {
                    console.error("[FiscalPayment] ❌ Fiscal print FAILED:", result);

                    // AUTO-VOID на pinpad транзакциите — ако фискалният бон се
                    // провали, клиентът НЕ трябва да остане с дебитирана карта
                    // без съответен бон. Намираме всички платежни линии, маркирани
                    // от `payment_datecs_pay.js` (l10n_bg_pinpad_rrn), и викаме
                    // /pinpads/<id>/void за всяка.
                    const paymentLines =
                        order.payment_ids || order.get_paymentlines?.() || [];
                    const toVoid = paymentLines.filter(
                        (l) => l.l10n_bg_pinpad_rrn && l.l10n_bg_pinpad_host
                    );
                    let voidedCount = 0;
                    let voidFailed = false;
                    for (const line of toVoid) {
                        const url =
                            String(line.l10n_bg_pinpad_host).replace(/\/+$/, "") +
                            `/pinpads/${encodeURIComponent(line.l10n_bg_pinpad_id)}/void`;
                        try {
                            const resp = await fetch(url, {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({
                                    amount: line.l10n_bg_pinpad_amount,
                                    rrn: line.l10n_bg_pinpad_rrn,
                                    auth_id: line.l10n_bg_pinpad_auth_id,
                                }),
                            });
                            const voidResult = resp.ok ? await resp.json() : null;
                            if (voidResult && voidResult.ok) {
                                voidedCount++;
                                console.log(
                                    "[FiscalPayment] 🔄 Auto-VOID OK · RRN",
                                    line.l10n_bg_pinpad_rrn
                                );
                            } else {
                                voidFailed = true;
                                console.error(
                                    "[FiscalPayment] ⚠ Auto-VOID failed · RRN",
                                    line.l10n_bg_pinpad_rrn, voidResult
                                );
                            }
                        } catch (e) {
                            voidFailed = true;
                            console.error(
                                "[FiscalPayment] ⚠ Auto-VOID exception · RRN",
                                line.l10n_bg_pinpad_rrn, e
                            );
                        }
                    }

                    if (notification) {
                        const errorType = refundInfo.isRefund ? _t("сторно бон") : _t("фискален бон");
                        let body =
                            _t("Грешка при печат на ") + errorType + ": " +
                            (result.message?.body || _t("Неизвестна грешка")) +
                            _t("\n\nПоръчката НЕ МОЖЕ да бъде валидирана без фискален бон!");
                        if (toVoid.length) {
                            if (voidFailed) {
                                body += _t(
                                    "\n\n⚠ ВНИМАНИЕ: автоматичното VOID на картовото плащане НЕ премина за %s от %s транзакции. Провери терминала и при нужда направи ръчно VOID/отмяна през банката, преди да опитваш отново!",
                                    toVoid.length - voidedCount, toVoid.length,
                                );
                            } else {
                                body += _t(
                                    "\n\n🔄 Автоматично прекъснах %s картово(и) плащане(я) — клиентът не е дебитиран.",
                                    voidedCount,
                                );
                            }
                        }
                        notification.add(body, { type: "danger", sticky: true });
                    }

                    console.log("[FiscalPayment] ⛔ Order validation BLOCKED due to fiscal print failure");
                    return;
                }

            } catch (error) {
                console.error("[FiscalPayment] ❌ Fiscal printer error:", error);
                console.error("[FiscalPayment] ❌ Error stack:", error.stack);

                if (notification) {
                    notification.add(
                        _t("Грешка при комуникация с фискален принтер: ") + error.message +
                        _t("\n\nПоръчката НЕ МОЖЕ да бъде валидирана без фискален бон!"),
                        {
                            type: "danger",
                            sticky: true
                        }
                    );
                }

                console.log("[FiscalPayment] ⛔ Order validation BLOCKED due to fiscal printer error");
                return;
            }
        } else {
            console.log("[FiscalPayment] ⚠️ Fiscal printer not configured or no order");
            console.log("[FiscalPayment] Proceeding with normal validation...");
        }

        console.log("[FiscalPayment] ✅ Proceeding to normal order validation...");
        const ret = await super.validateOrder(isForceValidate);

        // SKIP ReceiptScreen — фискалното устройство вече произведе хартиен бон;
        // не ни трябва Odoo preview/print/email диалог. + email-ваме клиента
        // ако партньорът има email.
        if (order?.l10n_bg_is_fiscalized) {
            try {
                const partner = order.get_partner?.() || order.partner_id;
                const email = partner?.email;
                if (email && typeof order.id === "number") {
                    console.log("[FiscalPayment] 📧 Auto-sending receipt e-mail to", email);
                    this.pos.data
                        .call("pos.order", "action_send_receipt",
                              [[order.id], email, "", null])
                        .then(() => console.log("[FiscalPayment] ✉ e-mail dispatched"))
                        .catch(err => console.warn("[FiscalPayment] e-mail send failed:", err));
                }
            } catch (e) {
                console.warn("[FiscalPayment] e-mail trigger error:", e);
            }
            try {
                console.log("[FiscalPayment] ⏭ Skipping ReceiptScreen → ProductScreen");
                order.set_screen_data?.({ name: "" });
                this.pos.selectNextOrder?.();
                // v18: pos.showScreen; (v19 преименува на pos.navigate — пазим и двата)
                if (typeof this.pos.showScreen === "function") {
                    this.pos.showScreen("ProductScreen");
                } else if (typeof this.pos.navigate === "function") {
                    this.pos.navigate("ProductScreen");
                }
            } catch (e) {
                console.warn("[FiscalPayment] ReceiptScreen skip failed:", e);
            }
        }
        return ret;
    },

    _getRefundInfo(order) {
        const orderLines = order.lines || order.get_orderlines?.() || [];

        for (const line of orderLines) {
            const qty = line.get_quantity?.() || line.qty || 0;

            if (qty < 0 && line.refunded_orderline_id) {
                const originalOrder = line.refunded_orderline_id.order_id;

                console.log("[FiscalPayment] 📋 Found refund line:");
                console.log("[FiscalPayment]    Current line qty:", qty);
                console.log("[FiscalPayment]    Refunded line:", line.refunded_orderline_id);
                console.log("[FiscalPayment]    Original order:", originalOrder?.name);
                console.log("[FiscalPayment]    Original order fiscal #:", originalOrder?.l10n_bg_fiscal_receipt_number);

                return {
                    isRefund: true,
                    originalOrder: originalOrder,
                };
            }
        }

        return {
            isRefund: false,
            originalOrder: null,
        };
    },

    _getRefundReason(order) {
        return "refund";
    }
});

console.log("[FiscalPayment] ✅ PaymentScreen patched successfully (v18)");
                                                                                                                                                                                                                                                                                           