/** @odoo-module **/

/**
 * Native POS payment terminal driver for DatecsPay (Odoo.ErpNet.FP proxy).
 *
 * Registered as `datecs_pay` — appears in the standard POS "Integration"
 * section. When the cashier sends the card payment, `sendPaymentRequest`
 * fetches the LOCAL ErpNet.FP proxy `/pinpads/<id>/purchase` directly from
 * the browser (browser-proxy topology). The proxy drives the physical
 * pinpad (BluePad-55 etc.) via libdatecs_pinpad.so.
 *
 * Cancellation: if the cashier closes the payment screen or removes the
 * waiting line, `sendPaymentCancel`/`close` ABORT the in-flight fetch so
 * the POS stops waiting immediately (the proxy/pinpad request is dropped).
 */

import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { register_payment_method } from "@point_of_sale/app/services/pos_store";

// Колко чакаме клиента да пъхне картата + PIN (хостов round-trip + EMV).
const PINPAD_TIMEOUT_MS = 90000;

export class PaymentDatecsPay extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        // uuid → { controller, cancelled }
        this._pending = {};
    }

    sendPaymentRequest(uuid) {
        super.sendPaymentRequest(uuid);
        return this._datecsPay(uuid);
    }

    sendPaymentCancel(order, uuid) {
        super.sendPaymentCancel(order, uuid);
        // 1) прекъсваме чакащата browser заявка → POS-ът спира да чака;
        // 2) казваме на проксито/терминала да прекъсне и да освободи pinpad-а.
        this._abort(uuid);
        this._postCancel();
        return Promise.resolve(true);
    }

    close() {
        super.close();
        const hadPending = Object.keys(this._pending).length > 0;
        for (const uuid of Object.keys(this._pending)) {
            this._abort(uuid);
        }
        if (hadPending) {
            this._postCancel();
        }
    }

    _postCancel() {
        const host = this.pos.session?.l10n_bg_erp_net_fp_host;
        const pm = this.payment_method_id || this.payment_method;
        const pinpadId = (pm && pm.l10n_bg_pinpad_id) || "default";
        if (!host) {
            return;
        }
        const url =
            String(host).replace(/\/+$/, "") +
            `/pinpads/${encodeURIComponent(pinpadId)}/cancel`;
        // fire-and-forget — освобождава устройството на проксито + опит за
        // abort на физическия терминал (TRANSACTION END).
        fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: "{}",
        }).catch(() => {});
    }

    _abort(uuid) {
        const p = this._pending[uuid];
        if (p) {
            p.cancelled = true;
            try {
                p.controller.abort();
            } catch (e) {
                // ignore
            }
        }
    }

    async _datecsPay(uuid) {
        const order = this.pos.getOrder();
        const line =
            (order.getSelectedPaymentline && order.getSelectedPaymentline()) ||
            order.get_paymentlines().find((l) => l.uuid === uuid);
        if (!line) {
            return false;
        }
        const pm = line.payment_method_id || line.payment_method;
        const host = this.pos.session?.l10n_bg_erp_net_fp_host;
        const pinpadId = (pm && pm.l10n_bg_pinpad_id) || "default";
        if (!host) {
            this.env.services.notification.add(
                _t("No ErpNet.FP proxy host configured for this POS — pinpad disabled."),
                { type: "danger" },
            );
            return false;
        }

        const url =
            String(host).replace(/\/+$/, "") +
            `/pinpads/${encodeURIComponent(pinpadId)}/purchase`;
        const ctrl = new AbortController();
        const pending = { controller: ctrl, cancelled: false };
        this._pending[uuid] = pending;
        const timer = setTimeout(() => ctrl.abort(), PINPAD_TIMEOUT_MS);
        let result;
        try {
            const resp = await fetch(url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    amount: line.amount,
                    currency: this.pos.currency?.name || "BGN",
                    reference: order.name || order.uid || "",
                }),
                signal: ctrl.signal,
            });
            if (!resp.ok) {
                throw new Error(`HTTP ${resp.status}`);
            }
            result = await resp.json();
            console.log("[DatecsPay] proxy response:", JSON.stringify(result));
        } catch (e) {
            // Прекъснато от касиера (Cancel/Close) — тихо, без грешка.
            if (pending.cancelled || e.name === "AbortError") {
                if (!pending.cancelled) {
                    this.env.services.notification.add(
                        _t("Pinpad timed out — no response from the terminal."),
                        { type: "danger" },
                    );
                }
                return false;
            }
            this.env.services.notification.add(
                _t("Pinpad request failed: %s", e.message || e),
                { type: "danger" },
            );
            return false;
        } finally {
            clearTimeout(timer);
            delete this._pending[uuid];
        }

        // Проксито връща HTTP 200 дори при отказ — решаваме по `ok`.
        if (!result || !result.ok) {
            this.env.services.notification.add(
                _t("Pinpad declined: %s", (result && result.error) || _t("unknown error")),
                { type: "danger" },
            );
            return false;
        }

        const txid = result.rrn || result.authId || result.hostRrn || "";
        if (line.setReceiptInfo) {
            line.setReceiptInfo(
                `RRN: ${result.rrn || "—"}  AUTH: ${result.authId || "—"}`,
            );
        }
        line.transaction_id = txid;
        line.card_type = "card";
        // Запазваме отделните полета на line-а, за да може finalizeValidation
        // да направи AUTO-VOID при провал на фискалния бон (клиентът да не
        // остане платен без бон). Стандартните transaction_id/card_type са
        // за UI; тези `l10n_bg_pinpad_*` са за machine-to-machine void.
        line.l10n_bg_pinpad_host = host;
        line.l10n_bg_pinpad_id = pinpadId;
        line.l10n_bg_pinpad_rrn = result.rrn || "";
        line.l10n_bg_pinpad_auth_id = result.authId || "";
        line.l10n_bg_pinpad_amount = line.amount;
        this.env.services.notification.add(
            _t("Pinpad approved · ref %s", txid || "—"),
            { type: "success" },
        );
        return true;
    }
}

register_payment_method("datecs_pay", PaymentDatecsPay);
