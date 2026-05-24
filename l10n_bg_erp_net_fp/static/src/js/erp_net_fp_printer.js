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

        // Per-cashier fiscal-printer credentials — set on res.users
        // and exposed through pos.session._load_pos_data_fields.
        // When empty, the ErpNet.FP server falls back to its own
        // config.yaml defaults (operator=1, password=0000).
        const session = order.pos?.session || order.session;
        const operatorOpts = {};
        if (session?.l10n_bg_fp_operator) {
            operatorOpts.operator = session.l10n_bg_fp_operator;
        }
        if (session?.l10n_bg_fp_operator_password) {
            operatorOpts.operatorPassword = session.l10n_bg_fp_operator_password;
        }

        // Подготвяме данните за фискален бон (async — взима УНП от ORM allocator)
        const receiptData = await this._prepareFiscalReceiptData(order, posConfig, operatorOpts);

        // Detect invoice mode — Odoo POS sets `to_invoice` flag from
        // the standard "Фактура" checkbox in the payment screen. When
        // active, we hit the proxy's /invoice endpoint with extra
        // partner data (EIK, address, МОЛ, ИН по ЗДДС) so the device
        // prints a true fiscal invoice on supporting firmware (or a
        // free-text-headed regular receipt as a fallback — proxy
        // chooses automatically based on detected capability).
        const isInvoice = !!(order.to_invoice || (order.is_to_invoice && order.is_to_invoice()));
        let endpoint = "receipt";
        let payload = receiptData;
        if (isInvoice) {
            const partner = order.get_partner ? order.get_partner() : order.partner_id;
            if (!partner) {
                console.warn("[ErpNetFPPrinter] Invoice flag set but no partner — falling back to receipt");
            } else {
                endpoint = "invoice";
                payload = this._prepareFiscalInvoiceData(receiptData, partner);
            }
        }

        console.log("[ErpNetFPPrinter] 📋 Receipt data prepared:");
        console.log("[ErpNetFPPrinter]    Endpoint:", endpoint);
        console.log("[ErpNetFPPrinter]    Unique sale number:", payload.uniqueSaleNumber);
        console.log("[ErpNetFPPrinter]    Items count:", payload.items.length);
        console.log("[ErpNetFPPrinter]    Payments count:", payload.payments.length);

        try {
            // Изпращаме към fiscal printer
            const result = await this._sendToFiscalPrinter(payload, endpoint);

            if (result && result.ok) {
                console.log("[ErpNetFPPrinter] ✅ Fiscal print SUCCESS!");
                console.log("[ErpNetFPPrinter]    Receipt #:", result.receiptNumber);
                console.log("[ErpNetFPPrinter]    Receipt DateTime:", result.receiptDateTime);
                console.log("[ErpNetFPPrinter]    Fiscal Memory #:", result.fiscalMemorySerialNumber);

                // Актуализираме order с фискалните данни
                if (order) {
                    order.l10n_bg_fiscal_receipt_number = result.receiptNumber;
                    // Конвертираме към Odoo datetime формат: 'YYYY-MM-DD HH:MM:SS'
                    // ErpNet.FP връща: "2019-05-17T13:55:18"
                    // Odoo очаква: "2019-05-17 13:55:18"
                    if (result.receiptDateTime) {
                        // Заменяме 'T' с интервал и премахваме всичко след секундите
                        const dateTimeStr = result.receiptDateTime
                            .replace('T', ' ')     // 2019-05-17T13:55:18 -> 2019-05-17 13:55:18
                            .replace('Z', '')      // Премахваме Z ако има
                            .split('.')[0];        // Премахваме милисекунди ако има

                        order.l10n_bg_fiscal_receipt_datetime = dateTimeStr;
                    } else {
                        // Fallback към текущо време в Odoo формат
                        const now = new Date();
                        const year = now.getFullYear();
                        const month = String(now.getMonth() + 1).padStart(2, '0');
                        const day = String(now.getDate()).padStart(2, '0');
                        const hours = String(now.getHours()).padStart(2, '0');
                        const minutes = String(now.getMinutes()).padStart(2, '0');
                        const seconds = String(now.getSeconds()).padStart(2, '0');

                        order.l10n_bg_fiscal_receipt_datetime = `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
                    }
                    order.l10n_bg_fiscal_memory_number = result.fiscalMemorySerialNumber;
                    order.l10n_bg_is_fiscalized = true;

                    console.log("[ErpNetFPPrinter] ✅ Order updated with fiscal data");
                    console.log("[ErpNetFPPrinter]    order.l10n_bg_fiscal_receipt_number:", order.l10n_bg_fiscal_receipt_number);
                    console.log("[ErpNetFPPrinter]    order.l10n_bg_fiscal_receipt_datetime:", order.l10n_bg_fiscal_receipt_datetime);
                    console.log("[ErpNetFPPrinter]    order.l10n_bg_fiscal_memory_number:", order.l10n_bg_fiscal_memory_number);
                }

                return {
                    successful: true,
                    fiscalData: {
                        receiptNumber: result.receiptNumber,
                        receiptDateTime: result.receiptDateTime,
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
     * @param {Object} options - Допълнителни опции (operator, operatorPassword, info, etc.)
     * @returns {Object} Fiscal receipt data
     */
    async _prepareFiscalReceiptData(order, posConfig, options = {}) {
        const items = [];
        let amount_return = 0;
        let all_payments = 0;
        const isReversal = options.isReversal || false;

        // В Odoo 18 е order.lines
        const orderLines = order.lines || order.get_orderlines?.() || [];

        for (const line of orderLines) {
            // qty + единична цена С ДДС (GROSS) — НЕ NET. Фискалните устройства
            // от Datecs (DP-150) очакват цени per VAT group ВКЛЮЧИТЕЛНО ДДС
            // (Б1.98), за да съвпадне със сумата на плащането (картовите
            // плащания изискват ТОЧНА сума иначе E404 "Command not allowed").
            // В v19 POS: `line.priceIncl` = line total С ДДС, `line.price_unit`
            // = NET unit. Изчисляваме gross unit = priceIncl/qty с fallback-и.
            let quantity = line.qty ?? line.get_quantity?.() ?? 1;
            const grossTotal =
                line.priceIncl
                ?? line.price_subtotal_incl
                ?? line.getPriceWithTax?.()
                ?? line.get_price_with_tax?.();
            let unitPrice;
            if (grossTotal !== undefined && grossTotal !== null && quantity) {
                unitPrice = grossTotal / quantity;
            } else {
                // Fallback ако gross липсва: ползваме каквото има (NET е приемлив
                // за устройства, които сами добавят ДДС, но Datecs DP-150 НЕ
                // прави това → бонът пада).
                unitPrice =
                    line.getUnitDisplayPrice?.()
                    ?? line.get_unit_display_price?.()
                    ?? line.price_unit
                    ?? line.price
                    ?? 0;
            }
            console.log("[ErpNetFPPrinter]    line price (gross):", unitPrice,
                        "qty:", quantity,
                        "(priceIncl:", line.priceIncl,
                        ", price_subtotal_incl:", line.price_subtotal_incl,
                        ", price_unit NET:", line.price_unit, ")");

            // ════════════════════════════════════════════════════════════
            // ВАЖНО: За сторно бонове ErpNet.FP изисква ПОЛОЖИТЕЛНИ стойности
            // ════════════════════════════════════════════════════════════
            if (isReversal) {
                quantity = Math.abs(quantity);
                unitPrice = Math.abs(unitPrice);
            }

            const item = {
                text: line.get_full_product_name?.() ||
                      line.full_product_name ||
                      line.product?.display_name ||
                      _t("Product"),
                quantity: quantity,
                unitPrice: unitPrice,
                taxGroup: this._getTaxGroup(line, order),
            };
            amount_return += parseFloat((item.quantity * item.unitPrice).toFixed(2));

            const discount = line.get_discount?.() || line.discount || 0;
            if (discount && discount > 0) {
                item.priceModifierType = "discount-percent";
                item.priceModifierValue = discount;
                item.unitPrice = line.getUnitDisplayPriceBeforeDiscount?.() || (item.unitPrice / (1 - discount / 100));
            }
            items.push(item);
        }

        const payments = [];

        // В Odoo 18 е order.payment_ids
        const paymentLines = order.payment_ids || order.get_paymentlines?.() || [];

        for (const payment of paymentLines) {
            let paymentAmount = payment.get_amount?.() || payment.amount || 0;

            // ════════════════════════════════════════════════════════════
            // ВАЖНО: За сторно бонове ErpNet.FP изисква ПОЛОЖИТЕЛНИ стойности
            // ════════════════════════════════════════════════════════════
            if (isReversal) {
                paymentAmount = Math.abs(paymentAmount);
            } else {
                paymentAmount = Math.max(0, paymentAmount);
            }

            const paymentType = this._getPaymentType(payment);
            console.log("[ErpNetFPPrinter] Payment:", payment, "Amount:", paymentAmount);

            if (paymentAmount === 0) continue;
            all_payments += paymentAmount;

            payments.push({
                amount: paymentAmount,
                paymentType: paymentType,
            });
        }

        // НЕ пращаме отделен "change" payment ред — ErpNet.FP проксито/ФУ
        // не приема такъв enum (валидни са cash/card/check/bank/coupons/...).
        // Устройството САМО изчислява рестото от tendered amount (ако
        // сумата на плащанията > сумата на артикулите, разликата е автоматично
        // ресто и се принтира на бона).

        // Уникален номер на продажбата (НАП-compliant per-device counter).
        // Изпробваме server-side allocator (atomic +1 per device, ползва
        // реалния ИН на ФУ); fallback е локалната евристика.
        const uniqueSaleNumber = await this._formatUniqueSaleNumber(order, posConfig);

        const receiptData = {
            uniqueSaleNumber: uniqueSaleNumber,
            items: items,
            payments: payments,
        };

        // Operator credentials (ако са предоставени)
        if (options.operator) {
            receiptData.operator = options.operator;
        }
        if (options.operatorPassword) {
            receiptData.operatorPassword = options.operatorPassword;
        }

        // Info section (ако е предоставена)
        if (options.info) {
            receiptData.info = options.info;
        }

        return receiptData;
    }

    /**
     * Форматира уникален номер на продажбата според ErpNet.FP изискванията
     *
     * Формат: XX123456-YYYY-1234567
     * - XX123456: Printer ID (например DT279013, dt737851 -> DT737851)
     * - YYYY: 4 буквено-цифрени символа (POS session илиsequencial counter)
     * - 1234567: 7 цифри (order sequence number)
     *
     * Regex: ^[A-Z]{2}[0-9]{6}-[A-Z0-9]{4}-[0-9]{7}$
     *
     * @param {Object} order - POS Order обект
     * @param {Object} posConfig - POS Configuration
     * @returns {String} Форматиран уникален номер
     */
    async _formatUniqueSaleNumber(order, posConfig) {
        // НАП-compliant: server-side allocator (atomic +1 per ФУ, реален
        // ИН на ФУ от устройството). Fall-back на локалната евристика ако
        // RPC-то fail-не (offline POS, или сървърна грешка).
        const operatorCode =
            order?.cashier?.id
            ?? order?.user_id?.id
            ?? posConfig?.session_id
            ?? posConfig?.id
            ?? 1;

        // JS fetch на ИН на ФУ от проксито (Odoo сървърът не може да го направи
        // в browser-proxy topology). Подаваме serial-а на ORM allocator-а.
        let deviceSerial = "";
        try {
            const url = this.baseUrl + "/printers/" + encodeURIComponent(this.printerId);
            const resp = await fetch(url, { method: "GET" });
            if (resp.ok) {
                const data = await resp.json();
                deviceSerial = (data.serialNumber || "").trim();
            }
        } catch (e) {
            console.warn("[ErpNetFPPrinter] proxy serial fetch fail:", e);
        }

        try {
            const orm = this.env?.services?.orm;
            if (orm) {
                const uns = await orm.call(
                    "fiscal.printer.device",
                    "l10n_bg_allocate_uns",
                    [this.printerId, String(operatorCode), deviceSerial || null],
                );
                if (uns) {
                    console.log("[ErpNetFPPrinter] УНП от ORM allocator:", uns,
                                "(serial from proxy:", deviceSerial, ")");
                    return uns;
                }
                console.warn(
                    "[ErpNetFPPrinter] ORM allocator върна null — fallback на локалната евристика"
                );
            }
        } catch (e) {
            console.warn("[ErpNetFPPrinter] ORM allocator грешка:", e,
                         "— fallback на локалната евристика");
        }
        return this._formatUniqueSaleNumberLocal(order, posConfig);
    }

    _formatUniqueSaleNumberLocal(order, posConfig) {
        // Fallback — само ако сървърният allocator е недостъпен. Не е
        // NRA-compliant (нумерацията се нулира между сесии при липса на
        // tracking_number; може да дава дубликати). Ползва се само за да не
        // блокира продажбата при временно сървърен срив.
        const printerIdUpper = this.printerId.toUpperCase();

        // Извличаме букви и цифри от printer ID
        let letters = "";
        let digits = "";

        for (let char of printerIdUpper) {
            if (/[A-Z]/.test(char) && letters.length < 2) {
                letters += char;
            } else if (/[0-9]/.test(char) && digits.length < 6) {
                digits += char;
            }
        }

        // Гарантираме, че имаме точно 2 букви и 6 цифри
        while (letters.length < 2) letters += "XX"[letters.length];
        while (digits.length < 6) digits = "0" + digits;

        const printerPart = letters + digits;

        // Част 2: 4 буквено-цифрени символа - POS config ID като 4-символен код
        const posId = posConfig?.id || posConfig?.session_id || 1;
        const posPart = String(posId).padStart(4, '0').slice(-4);

        // Част 3: 7 ЦИФРИ — order sequence. В Odoo 19 order.id често е низ
        // (uuid, напр. "b1d2f81") и order.name = "/", затова извличаме САМО
        // цифрите от наличните източници; ако никъде няма цифри — резервен
        // timestamp. Иначе буквите чупят УНП-то (устройството връща E401
        // "Syntax error in the received data").
        let orderNumber = "";
        for (const cand of [order.tracking_number, order.sequence_number,
                            order.pos_reference, order.name, order.id]) {
            if (cand !== undefined && cand !== null) {
                const digits = String(cand).replace(/\D/g, "");
                if (digits) {
                    orderNumber = digits;
                    break;
                }
            }
        }
        if (!orderNumber) {
            orderNumber = String(Date.now());
        }

        // Вземаме последните 7 цифри или допълваме с нули
        const orderSeq = orderNumber.padStart(7, '0').slice(-7);

        // Комбинираме всички части
        const uniqueSaleNumber = `${printerPart}-${posPart}-${orderSeq}`;

        console.log("[ErpNetFPPrinter] Generated uniqueSaleNumber:", uniqueSaleNumber);
        console.log("[ErpNetFPPrinter]    Printer ID part:", printerPart, `(from ${this.printerId})`);
        console.log("[ErpNetFPPrinter]    POS/Session part:", posPart);
        console.log("[ErpNetFPPrinter]    Order seq:", orderSeq);

        return uniqueSaleNumber;
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
        // Чете explicit полето `l10n_bg_fiscal_payment_type` от pos.payment.
        // method (auto-default-нато при инсталация по use_payment_terminal/
        // is_cash_count/type, editable от касиера за coupon/voucher/internal).
        // Заменя предишния fragile name-heuristic (cash/каса/datecs/...) —
        // имената са user-конфигурируеми и не са надежден ключ.
        const pm = payment.payment_method || payment.payment_method_id || {};
        if (pm.l10n_bg_fiscal_payment_type) {
            return pm.l10n_bg_fiscal_payment_type;
        }
        // Defensive fallback ако полето не е заредено (стар bundle/missing -u):
        if (pm.use_payment_terminal) return "card";
        if (pm.is_cash_count) return "cash";
        return "cash";
    }

    /**
     * Изпраща заявка към fiscal printer
     */
    /**
     * Builds the /invoice payload — same shape as receipt + customer
     * fields read from `partner` (Odoo res.partner record exposed in
     * the POS frontend).
     *
     * EIK type heuristic: BG VAT ID `BG<9-or-10>` → BULSTAT (0);
     * 10-digit `EGN` → 1; non-BG → 2.
     */
    _prepareFiscalInvoiceData(receiptData, partner) {
        const vat = (partner.vat || "").trim();
        const eik = vat.replace(/^BG/i, "").replace(/\s/g, "");
        let eikType = "0";  // BULSTAT
        if (eik && eik.length === 10 && /^\d+$/.test(eik)) {
            eikType = "1";  // EGN
        } else if (vat && !/^BG/i.test(vat)) {
            eikType = "2";  // foreign
        }
        const addressParts = [
            partner.street, partner.street2, partner.city,
        ].filter(Boolean).join(", ");
        return {
            ...receiptData,
            customerName: (partner.name || "").substring(0, 26),
            customerEik: eik || (partner.company_registry || ""),
            customerEikType: eikType,
            customerAddress: addressParts.substring(0, 30),
            customerBuyer: (partner.contact_name || partner.name || "").substring(0, 16),
            customerVat: /^BG/i.test(vat) ? vat.substring(0, 13) : "",
        };
    }

    async _sendToFiscalPrinter(data, endpoint = "receipt") {
        const url = `${this.baseUrl}/printers/${encodeURIComponent(this.printerId)}/${endpoint}`;

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
     * Fetch с timeout.
     *
     * Default 60s — a single receipt produces 4+ ISL commands
     * (open + N sales + payment + close), each ~5s round-trip on
     * RS-232; the previous 15s budget aborted half-way through
     * legitimate operations and surfaced as 'Timeout при връзка с
     * принтера' in the POS UI.
     */
    async _fetchWithTimeout(url, options = {}, timeout = 60000) {
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

    // ═══════════════════════════════════════════════════════════════
    // ДОПЪЛНИТЕЛНИ ERPNET.FP МЕТОДИ
    // ═══════════════════════════════════════════════════════════════

    /**
     * Печат на сторно бон (Reversal Receipt)
     * КРИТИЧНО: Законово изискване в България!
     *
     * @param {Object} originalOrder - Оригиналната поръчка (която се сторнира)
     * @param {Object} refundOrder - Текущата сторно поръчка
     * @param {String} reason - Причина: "operator-error", "refund", "tax-base-reduction"
     * @returns {Promise<Object>} Result
     */
    async printReversalReceipt(originalOrder, refundOrder, reason = "refund") {
        console.log("[ErpNetFPPrinter] 🔄 printReversalReceipt() called");
        console.log("[ErpNetFPPrinter]    Original order:", originalOrder?.name);
        console.log("[ErpNetFPPrinter]    Refund order:", refundOrder?.name);

        if (!this.baseUrl || !this.printerId) {
            console.error("[ErpNetFPPrinter] ❌ Printer not configured!");
            return this.getConfigError();
        }

        if (!originalOrder) {
            return {
                successful: false,
                message: {
                    title: _t("Липсва оригинална поръчка"),
                    body: _t("Не може да се намери оригиналната поръчка за сторниране."),
                },
            };
        }

        // ════════════════════════════════════════════════════════════
        // ИЗВЛИЧАМЕ ФИСКАЛНИТЕ ДАННИ ОТ ОРИГИНАЛНАТА ПОРЪЧКА
        // ════════════════════════════════════════════════════════════
        const originalFiscalData = {
            receiptNumber: originalOrder.l10n_bg_fiscal_receipt_number,
            receiptDateTime: originalOrder.l10n_bg_fiscal_receipt_datetime,
            fiscalMemorySerialNumber: originalOrder.l10n_bg_fiscal_memory_number,
            uniqueSaleNumber: originalOrder.l10n_bg_unique_sale_number,
        };

        console.log("[ErpNetFPPrinter] 📋 Original fiscal data:");
        console.log("[ErpNetFPPrinter]    Receipt #:", originalFiscalData.receiptNumber);
        console.log("[ErpNetFPPrinter]    Receipt DateTime:", originalFiscalData.receiptDateTime);
        console.log("[ErpNetFPPrinter]    Fiscal Memory #:", originalFiscalData.fiscalMemorySerialNumber);
        console.log("[ErpNetFPPrinter]    Unique Sale #:", originalFiscalData.uniqueSaleNumber);

        // Валидация
        if (!originalFiscalData.receiptNumber) {
            return {
                successful: false,
                message: {
                    title: _t("Липсва фискален номер"),
                    body: _t("Оригиналната поръчка няма фискален номер. Не може да се направи сторно."),
                },
            };
        }

        // Ако няма uniqueSaleNumber, опитваме се да го реконструираме
        if (!originalFiscalData.uniqueSaleNumber) {
            console.warn("[ErpNetFPPrinter] ⚠️ uniqueSaleNumber not found in original order, reconstructing...");
            const posConfig = originalOrder.pos?.config || originalOrder.config || { name: "POS" };
            originalFiscalData.uniqueSaleNumber = this._formatUniqueSaleNumber(originalOrder, posConfig);
        }

        // Конвертираме receiptDateTime към ErpNet.FP формат ако е в Odoo формат
        if (originalFiscalData.receiptDateTime && originalFiscalData.receiptDateTime.includes(' ')) {
            // От "2019-05-17 13:55:18" към "2019-05-17T13:55:18"
            originalFiscalData.receiptDateTime = originalFiscalData.receiptDateTime.replace(' ', 'T');
        }

        // ════════════════════════════════════════════════════════════
        // ПОДГОТВЯМЕ СТОРНО ДАННИТЕ С ПОЛОЖИТЕЛНИ СТОЙНОСТИ
        // ════════════════════════════════════════════════════════════
        const posConfig = refundOrder.pos?.config || refundOrder.config || { name: "POS" };

        // Per-cashier operator credentials (mirrors the receipt path
        // above — see comments at line ~96)
        const session = refundOrder.pos?.session || refundOrder.session;
        const operatorOpts = { isReversal: true };
        if (session?.l10n_bg_fp_operator) {
            operatorOpts.operator = session.l10n_bg_fp_operator;
        }
        if (session?.l10n_bg_fp_operator_password) {
            operatorOpts.operatorPassword = session.l10n_bg_fp_operator_password;
        }

        // ВАЖНО: Подаваме isReversal: true за да конвертира към положителни стойности
        const receiptData = await this._prepareFiscalReceiptData(refundOrder, posConfig, operatorOpts);

        // Добавяме данните от оригиналния бон
        receiptData.receiptNumber = originalFiscalData.receiptNumber;
        receiptData.receiptDateTime = originalFiscalData.receiptDateTime;
        receiptData.fiscalMemorySerialNumber = originalFiscalData.fiscalMemorySerialNumber;
        receiptData.reason = reason;

        // ВАЖНО: uniqueSaleNumber трябва да е същият като оригиналния!
        receiptData.uniqueSaleNumber = originalFiscalData.uniqueSaleNumber;

        console.log("[ErpNetFPPrinter] 📤 Reversal receipt data:");
        console.log("[ErpNetFPPrinter]    uniqueSaleNumber:", receiptData.uniqueSaleNumber);
        console.log("[ErpNetFPPrinter]    receiptNumber:", receiptData.receiptNumber);
        console.log("[ErpNetFPPrinter]    receiptDateTime:", receiptData.receiptDateTime);
        console.log("[ErpNetFPPrinter]    fiscalMemorySerialNumber:", receiptData.fiscalMemorySerialNumber);
        console.log("[ErpNetFPPrinter]    reason:", receiptData.reason);
        console.log("[ErpNetFPPrinter]    items:", receiptData.items);
        console.log("[ErpNetFPPrinter]    payments:", receiptData.payments);

        // ════════════════════════════════════════════════════════════
        // ИЗПРАЩАМЕ КЪМ FISCAL PRINTER
        // ════════════════════════════════════════════════════════════
        try {
            const url = `${this.baseUrl}/printers/${encodeURIComponent(this.printerId)}/reversalreceipt`;

            console.log("[ErpNetFPPrinter] 🌐 POST reversal to:", url);
            console.log("[ErpNetFPPrinter] 📤 Body:", JSON.stringify(receiptData, null, 2));

            const response = await this._fetchWithTimeout(url, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                body: JSON.stringify(receiptData),
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.error("[ErpNetFPPrinter] ❌ HTTP error:", response.status, errorText);
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }

            const result = await response.json();
            console.log("[ErpNetFPPrinter] 📥 Reversal response:", result);

            if (result.ok) {
                console.log("[ErpNetFPPrinter] ✅ Reversal print SUCCESS!");
                console.log("[ErpNetFPPrinter]    Reversal Receipt #:", result.receiptNumber);

                // Актуализираме refund order с данните от сторно бона
                if (refundOrder) {
                    refundOrder.l10n_bg_fiscal_receipt_number = result.receiptNumber;

                    if (result.receiptDateTime) {
                        const dateTimeStr = result.receiptDateTime
                            .replace('T', ' ')
                            .replace('Z', '')
                            .split('.')[0];
                        refundOrder.l10n_bg_fiscal_receipt_datetime = dateTimeStr;
                    }

                    refundOrder.l10n_bg_fiscal_memory_number = result.fiscalMemorySerialNumber;
                    refundOrder.l10n_bg_is_fiscalized = true;
                    refundOrder.l10n_bg_is_reversal = true;  // Маркираме като сторно

                    console.log("[ErpNetFPPrinter] ✅ Reversal order updated with fiscal data");
                }

                return {
                    successful: true,
                    fiscalData: {
                        receiptNumber: result.receiptNumber,
                        receiptDateTime: result.receiptDateTime,
                        fiscalMemorySerialNumber: result.fiscalMemorySerialNumber,
                    },
                };
            } else {
                throw new Error(this._extractErrorMessages(result));
            }
        } catch (error) {
            console.error("[ErpNetFPPrinter] ❌ Reversal error:", error);
            return {
                successful: false,
                message: {
                    title: _t("Грешка при сторно печат"),
                    body: error.message || _t("Неизвестна грешка"),
                },
                errorCode: "ERPNET_FP_REVERSAL_ERROR",
            };
        }
    }

    /**
     * X Отчет (междинен, без нулиране)
     *
     * @param {String} operator - Оператор ID
     * @param {String} operatorPassword - Парола на оператор
     * @returns {Promise<Object>} Result
     */
    async printXReport(operator = "1", operatorPassword = "0000") {
        console.log("[ErpNetFPPrinter] 📊 printXReport() called");

        if (!this.baseUrl || !this.printerId) {
            return this.getConfigError();
        }

        try {
            const url = `${this.baseUrl}/printers/${encodeURIComponent(this.printerId)}/xreport`;

            const response = await this._fetchWithTimeout(url, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                body: JSON.stringify({
                    operator: operator,
                    operatorPassword: operatorPassword,
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const result = await response.json();

            if (result.ok) {
                console.log("[ErpNetFPPrinter] ✅ X Report SUCCESS!");
                return { successful: true };
            } else {
                throw new Error(this._extractErrorMessages(result));
            }
        } catch (error) {
            console.error("[ErpNetFPPrinter] ❌ X Report error:", error);
            return {
                successful: false,
                message: {
                    title: _t("Грешка при X отчет"),
                    body: error.message,
                },
            };
        }
    }

    /**
     * Z Отчет (дневен фискален, с нулиране)
     * КРИТИЧНО: Законово изискване - задължителен в края на деня!
     *
     * @param {String} operator - Оператор ID
     * @param {String} operatorPassword - Парола на оператор
     * @returns {Promise<Object>} Result
     */
    async printZReport(operator = "1", operatorPassword = "0000") {
        console.log("[ErpNetFPPrinter] 📊 printZReport() called");

        if (!this.baseUrl || !this.printerId) {
            return this.getConfigError();
        }

        try {
            const url = `${this.baseUrl}/printers/${encodeURIComponent(this.printerId)}/zreport`;

            const response = await this._fetchWithTimeout(url, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                body: JSON.stringify({
                    operator: operator,
                    operatorPassword: operatorPassword,
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const result = await response.json();

            if (result.ok) {
                console.log("[ErpNetFPPrinter] ✅ Z Report SUCCESS!");
                return { successful: true };
            } else {
                throw new Error(this._extractErrorMessages(result));
            }
        } catch (error) {
            console.error("[ErpNetFPPrinter] ❌ Z Report error:", error);
            return {
                successful: false,
                message: {
                    title: _t("Грешка при Z отчет"),
                    body: error.message,
                },
            };
        }
    }

    /**
     * Служебно вкарване на пари в касата (Deposit)
     *
     * @param {Number} amount - Сума
     * @param {String} text - Описание
     * @returns {Promise<Object>} Result
     */
    async depositMoney(amount, text = "Начална каса") {
        console.log("[ErpNetFPPrinter] 💰 depositMoney() called");

        if (!this.baseUrl || !this.printerId) {
            return this.getConfigError();
        }

        try {
            const url = `${this.baseUrl}/printers/${encodeURIComponent(this.printerId)}/deposit`;

            const response = await this._fetchWithTimeout(url, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                body: JSON.stringify({
                    amount: amount,
                    text: text,
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const result = await response.json();

            if (result.ok) {
                console.log("[ErpNetFPPrinter] ✅ Deposit SUCCESS!");
                return { successful: true };
            } else {
                throw new Error(this._extractErrorMessages(result));
            }
        } catch (error) {
            console.error("[ErpNetFPPrinter] ❌ Deposit error:", error);
            return {
                successful: false,
                message: {
                    title: _t("Грешка при вкарване на пари"),
                    body: error.message,
                },
            };
        }
    }

    /**
     * Служебно изкарване на пари от касата (Withdraw)
     *
     * @param {Number} amount - Сума
     * @param {String} text - Описание
     * @returns {Promise<Object>} Result
     */
    async withdrawMoney(amount, text = "Разход") {
        console.log("[ErpNetFPPrinter] 💸 withdrawMoney() called");

        if (!this.baseUrl || !this.printerId) {
            return this.getConfigError();
        }

        try {
            const url = `${this.baseUrl}/printers/${encodeURIComponent(this.printerId)}/withdraw`;

            const response = await this._fetchWithTimeout(url, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                body: JSON.stringify({
                    amount: amount,
                    text: text,
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const result = await response.json();

            if (result.ok) {
                console.log("[ErpNetFPPrinter] ✅ Withdraw SUCCESS!");
                return { successful: true };
            } else {
                throw new Error(this._extractErrorMessages(result));
            }
        } catch (error) {
            console.error("[ErpNetFPPrinter] ❌ Withdraw error:", error);
            return {
                successful: false,
                message: {
                    title: _t("Грешка при изкарване на пари"),
                    body: error.message,
                },
            };
        }
    }

    /**
     * Проверка на статуса на принтера
     *
     * @returns {Promise<Object>} Status information
     */
    async getStatus() {
        if (!this.baseUrl || !this.printerId) {
            return { successful: false, online: false };
        }

        try {
            const url = `${this.baseUrl}/printers/${encodeURIComponent(this.printerId)}/status`;

            const response = await this._fetchWithTimeout(url, {
                method: "GET",
                headers: {
                    "Accept": "application/json",
                },
            }, 5000); // По-кратък timeout за status check

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const result = await response.json();

            return {
                successful: true,
                online: result.ok,
                deviceDateTime: result.deviceDateTime,
                messages: result.messages,
            };
        } catch (error) {
            console.error("[ErpNetFPPrinter] Status check error:", error);
            return {
                successful: false,
                online: false,
            };
        }
    }

    /**
     * Получаване на информация за принтера
     *
     * @returns {Promise<Object>} Printer information
     */
    async getPrinterInfo() {
        if (!this.baseUrl || !this.printerId) {
            return { successful: false };
        }

        try {
            const url = `${this.baseUrl}/printers/${encodeURIComponent(this.printerId)}`;

            const response = await this._fetchWithTimeout(url, {
                method: "GET",
                headers: {
                    "Accept": "application/json",
                },
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const result = await response.json();

            return {
                successful: true,
                info: result,
            };
        } catch (error) {
            console.error("[ErpNetFPPrinter] Get info error:", error);
            return {
                successful: false,
                message: error.message,
            };
        }
    }

    /**
     * Получаване на текущата сума в касата
     *
     * @returns {Promise<Object>} Cash amount
     */
    async getCurrentCash() {
        if (!this.baseUrl || !this.printerId) {
            return { successful: false };
        }

        try {
            const url = `${this.baseUrl}/printers/${encodeURIComponent(this.printerId)}/cash`;

            const response = await this._fetchWithTimeout(url, {
                method: "GET",
                headers: {
                    "Accept": "application/json",
                },
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const result = await response.json();

            if (result.ok) {
                return {
                    successful: true,
                    amount: result.amount,
                };
            } else {
                throw new Error(this._extractErrorMessages(result));
            }
        } catch (error) {
            console.error("[ErpNetFPPrinter] Get cash error:", error);
            return {
                successful: false,
                message: error.message,
            };
        }
    }

    /**
     * Печат на дубликат на последния бон
     *
     * @returns {Promise<Object>} Result
     */
    async printLastReceiptDuplicate() {
        console.log("[ErpNetFPPrinter] 📄 printLastReceiptDuplicate() called");

        if (!this.baseUrl || !this.printerId) {
            return this.getConfigError();
        }

        try {
            const url = `${this.baseUrl}/printers/${encodeURIComponent(this.printerId)}/lastreceipt`;

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

            if (result.ok) {
                console.log("[ErpNetFPPrinter] ✅ Duplicate print SUCCESS!");
                return { successful: true };
            } else {
                throw new Error(this._extractErrorMessages(result));
            }
        } catch (error) {
            console.error("[ErpNetFPPrinter] ❌ Duplicate print error:", error);
            return {
                successful: false,
                message: {
                    title: _t("Грешка при печат на дубликат"),
                    body: error.message,
                },
            };
        }
    }

    /**
     * Helper: Извлича error съобщения от result
     */
    _extractErrorMessages(result) {
        if (Array.isArray(result.messages)) {
            return result.messages
                .filter((m) => m.type === "error")
                .map((m) => m.text || m.code)
                .join("; ");
        }
        return _t("Принтерът върна грешка");
    }
}
