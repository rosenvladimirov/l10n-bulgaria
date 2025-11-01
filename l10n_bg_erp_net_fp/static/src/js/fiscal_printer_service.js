/** @odoo-module **/

import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

/**
 * Глобален сервис за комуникация с фискални принтери
 * Слуша за bus notifications и обработва заявки към принтери
 *
 * ОДОБРЕНО ЗА ODOO 18 ✅
 */
export const fiscalPrinterService = {
    dependencies: ["bus_service", "notification"],

    start(env, { bus_service, notification }) {
        let requestCounter = 0;

        console.log("%c[FiscalPrinter] 🚀 SERVICE STARTING (Odoo 18)", "color: #4CAF50; font-weight: bold; font-size: 14px");
        console.log("[FiscalPrinter] Environment:", env);
        console.log("[FiscalPrinter] Bus service available:", !!bus_service);
        console.log("[FiscalPrinter] Notification service available:", !!notification);

        // ========================================
        // DEBUG: Проверяваме методите на bus_service
        // ========================================
        console.log("%c[FiscalPrinter] 🔍 DEBUG - Bus service analysis", "color: #FF00FF; font-weight: bold");
        console.log("[FiscalPrinter] Bus service methods:", Object.getOwnPropertyNames(Object.getPrototypeOf(bus_service)));
        console.log("[FiscalPrinter] Bus service object:", bus_service);

        // Проверяваме за съществуващи канали
        if (bus_service._channels || bus_service.channels) {
            console.log("[FiscalPrinter] Existing channels:", bus_service._channels || bus_service.channels);
        }

        /**
         * Обработва bus notifications - ПОДОБРЕНА ВЕРСИЯ
         */
        const onBusNotification = (event) => {
            console.log("%c[FiscalPrinter] 📬 RAW BUS EVENT RECEIVED", "color: #FF9800; font-weight: bold; font-size: 14px");
            console.log("[FiscalPrinter] Event structure:", event);
            console.log("[FiscalPrinter] Event type:", typeof event);
            console.log("[FiscalPrinter] Event keys:", Object.keys(event));

            // Опитваме различни начини за достъп до notifications
            let notifications = null;

            // Вариант 1: event.detail
            if (event.detail) {
                notifications = event.detail;
                console.log("[FiscalPrinter] Found notifications in event.detail");
            }
            // Вариант 2: event.notifications
            else if (event.notifications) {
                notifications = event.notifications;
                console.log("[FiscalPrinter] Found notifications in event.notifications");
            }
            // Вариант 3: директно в event
            else if (Array.isArray(event)) {
                notifications = event;
                console.log("[FiscalPrinter] Event is directly an array");
            }
            // Вариант 4: event като единичен обект
            else {
                notifications = [event];
                console.log("[FiscalPrinter] Treating event as single notification");
            }

            // Правим сигурни че имаме масив
            if (!Array.isArray(notifications)) {
                notifications = [notifications];
            }

            console.log("[FiscalPrinter] Processing", notifications.length, "notifications");
            console.log("[FiscalPrinter] Full notifications array:", notifications);

            for (let i = 0; i < notifications.length; i++) {
                const notif = notifications[i];
                console.log(`%c[FiscalPrinter] Processing notification #${i}`, "color: #9C27B0; font-weight: bold");
                console.log("[FiscalPrinter] Raw notification:", notif);

                // Опитваме различни структури за извличане на type и payload
                let type = null;
                let payload = null;

                // Структура 1: { type: "...", payload: {...} }
                if (notif && typeof notif === 'object' && notif.type) {
                    type = notif.type;
                    payload = notif.payload || notif;
                    console.log("[FiscalPrinter] Structure 1 - type/payload object");
                }
                // Структура 2: { message: { type: "...", payload: {...} } }
                else if (notif && notif.message) {
                    type = notif.message.type;
                    payload = notif.message.payload || notif.message;
                    console.log("[FiscalPrinter] Structure 2 - message wrapper");
                }
                // Структура 3: ["type", payload]
                else if (Array.isArray(notif)) {
                    type = notif[0];
                    payload = notif[1];
                    console.log("[FiscalPrinter] Structure 3 - array format");
                }
                // Структура 4: { id: ..., message: {...} }
                else if (notif && notif.id && notif.message) {
                    type = notif.message.type;
                    payload = notif.message.payload;
                    console.log("[FiscalPrinter] Structure 4 - id/message format");
                }

                console.log("[FiscalPrinter] Extracted type:", type);
                console.log("[FiscalPrinter] Extracted payload:", payload);

                // Проверяваме за нашите канали - с различни варианти на имената
                const possibleRequestTypes = [
                    "fiscal.printer.request",
                    "fiscal_printer_request",
                    "fiscal/printer/request"
                ];

                const possibleStatusTypes = [
                    "fiscal.printer.status",
                    "fiscal_printer_status",
                    "fiscal/printer/status"
                ];

                // Генерична заявка към принтера
                if (possibleRequestTypes.includes(type)) {
                    console.log("%c[FiscalPrinter] 🎯 PRINTER REQUEST DETECTED!", "color: #00BCD4; font-weight: bold; font-size: 14px");
                    handlePrinterRequest(payload);
                }
                // Заявка за проверка на статус
                else if (possibleStatusTypes.includes(type) && payload && payload.action === "check_status") {
                    console.log("%c[FiscalPrinter] 🔍 STATUS CHECK REQUEST DETECTED!", "color: #00BCD4; font-weight: bold; font-size: 14px");
                    handleCheckStatusRequest(payload);
                }
                // Обновление на статус
                else if (possibleStatusTypes.includes(type) && payload && payload.action === "status_update") {
                    console.log("%c[FiscalPrinter] 🔄 STATUS UPDATE DETECTED!", "color: #00BCD4; font-weight: bold; font-size: 14px");
                    handleStatusUpdate(payload, notification);
                }
                else {
                    console.log("[FiscalPrinter] ⚠️ Unknown notification type:", type);
                }
            }
        };

        /**
         * Обработва генерична заявка към принтера
         */
        const handlePrinterRequest = async (data) => {
            requestCounter++;
            const localRequestId = requestCounter;

            console.log("%c[FiscalPrinter] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "color: #F44336; font-weight: bold");
            console.log(`%c[FiscalPrinter] 🔴 REQUEST #${localRequestId} START`, "color: #F44336; font-weight: bold; font-size: 13px");
            console.log("[FiscalPrinter] Full request data:", data);

            const { request_id, printer_id, method, endpoint, data: requestData, params } = data;

            console.log("[FiscalPrinter] Request ID:", request_id);
            console.log("[FiscalPrinter] Printer ID:", printer_id);
            console.log("[FiscalPrinter] Method:", method);
            console.log("[FiscalPrinter] Endpoint:", endpoint);
            console.log("[FiscalPrinter] Request Data:", requestData);
            console.log("[FiscalPrinter] Params:", params);

            try {
                // Взимаме конфигурация
                console.log(`[FiscalPrinter] #${localRequestId} 📡 Fetching printer config...`);
                const config = await rpc('/fiscal_printer/get_printer_config', {
                    printer_id: printer_id
                });

                if (config.error) {
                    throw new Error(config.error);
                }

                // Изграждаме URL
                const baseUrl = config.host.replace(/\/$/, '');
                const url = `${baseUrl}/${endpoint}`;

                console.log(`%c[FiscalPrinter] #${localRequestId} 🌐 MAKING HTTP REQUEST`, "color: #3F51B5; font-weight: bold");
                console.log(`[FiscalPrinter] #${localRequestId}    URL: ${url}`);

                // Правим заявка
                const response = await makePrinterRequest(url, method, requestData, params, localRequestId);

                // Изпращаме отговор към сървъра
                await rpc('/fiscal_printer/send_response', {
                    request_id: request_id,
                    printer_id: printer_id,
                    success: true,
                    response_data: response
                });

                console.log(`%c[FiscalPrinter] #${localRequestId} ✅ REQUEST COMPLETED`, "color: #4CAF50; font-weight: bold");

            } catch (error) {
                console.error(`[FiscalPrinter] #${localRequestId} ❌ REQUEST FAILED:`, error);

                // Изпращаме грешката към сървъра
                try {
                    await rpc('/fiscal_printer/send_response', {
                        request_id: request_id,
                        printer_id: printer_id,
                        success: false,
                        error_message: error.message || 'Unknown error'
                    });
                } catch (rpcError) {
                    console.error(`[FiscalPrinter] #${localRequestId} ❌ Failed to send error:`, rpcError);
                }
            }
        };

        /**
         * Обработва заявка за проверка на статус
         */
        const handleCheckStatusRequest = async (data) => {
            requestCounter++;
            const localRequestId = requestCounter;

            console.log(`%c[FiscalPrinter] 🟠 STATUS CHECK #${localRequestId}`, "color: #FF9800; font-weight: bold");

            try {
                const config = await rpc('/fiscal_printer/get_printer_config', {
                    printer_id: data.printer_id
                });

                if (config.error) {
                    throw new Error(config.error);
                }

                const baseUrl = config.host.replace(/\/$/, '');
                const url = `${baseUrl}/printers/${config.printer_id}/status`;

                const statusData = await makePrinterRequest(url, 'GET', null, null, localRequestId);

                await rpc('/fiscal_printer/update_status', {
                    printer_id: data.printer_id,
                    status_data: statusData
                });

                console.log(`%c[FiscalPrinter] #${localRequestId} ✅ STATUS CHECK COMPLETE`, "color: #4CAF50; font-weight: bold");

            } catch (error) {
                console.error(`[FiscalPrinter] #${localRequestId} ❌ STATUS CHECK FAILED:`, error);

                await rpc('/fiscal_printer/update_status', {
                    printer_id: data.printer_id,
                    status_data: {
                        status: 'error',
                        errorMessage: error.message || 'Connection error',
                        ok: false
                    }
                });
            }
        };

        /**
         * Обработва обновление на статус
         */
        const handleStatusUpdate = (data, notificationService) => {
            console.log("%c[FiscalPrinter] 🔔 STATUS UPDATE NOTIFICATION", "color: #9C27B0; font-weight: bold");
            console.log("[FiscalPrinter] Printer:", data.name);
            console.log("[FiscalPrinter] Status:", data.status);

            notificationService.add(
                `Принтер ${data.name}: ${data.status}`,
                {
                    type: data.is_ready ? "success" : "warning",
                }
            );
        };

        /**
         * Прави HTTP заявка към принтера
         */
        const makePrinterRequest = async (url, method, data = null, params = null, requestId = 0) => {
            const options = {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                mode: 'cors',
            };

            if (method === 'POST' && data) {
                options.body = JSON.stringify(data);
            }

            if (method === 'GET' && params) {
                const queryString = new URLSearchParams(params).toString();
                url = `${url}?${queryString}`;
            }

            console.log(`[FiscalPrinter] #${requestId} 🚀 Fetch to: ${url}`);

            const response = await fetch(url, options);

            console.log(`[FiscalPrinter] #${requestId} 📥 Response status: ${response.status}`);

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }

            const result = await response.json();
            return result;
        };

        // ========================================
        // ИНИЦИАЛИЗАЦИЯ И ПОДПИСВАНЕ
        // ========================================

        console.log("%c[FiscalPrinter] 📡 INITIALIZING BUS CONNECTION", "color: #2196F3; font-weight: bold");

        // 1. ПЪРВО: Стартираме bus service ако има такава функция
        if (typeof bus_service.start === 'function') {
            bus_service.start();
            console.log("[FiscalPrinter] ✅ Bus service started");
        }

        // 2. ВТОРО: Добавяме каналите - опитваме различни варианти
        const channelVariants = [
            ["fiscal.printer.request", "fiscal.printer.status"],
            ["fiscal_printer_request", "fiscal_printer_status"],
            ["fiscal/printer/request", "fiscal/printer/status"]
        ];

        let channelsAdded = false;
        for (const [reqChannel, statusChannel] of channelVariants) {
            try {
                bus_service.addChannel(reqChannel);
                bus_service.addChannel(statusChannel);
                console.log(`[FiscalPrinter] ✅ Channels added: ${reqChannel}, ${statusChannel}`);
                channelsAdded = true;
                break;
            } catch (e) {
                console.log(`[FiscalPrinter] ⚠️ Could not add channels ${reqChannel}, ${statusChannel}:`, e.message);
            }
        }

        // 3. ТРЕТО: Опитваме различни начини за подписване

        // Метод 1: addEventListener на bus_service
        if (bus_service.addEventListener) {
            bus_service.addEventListener("notification", onBusNotification);
            console.log("[FiscalPrinter] ✅ Added event listener via addEventListener");
        }

        // Метод 2: on метод на bus_service
        if (bus_service.on) {
            bus_service.on("notification", onBusNotification);
            console.log("[FiscalPrinter] ✅ Added event listener via on method");
        }

        // Метод 3: subscribe метод за директно подписване към канали
        if (bus_service.subscribe) {
            try {
                bus_service.subscribe("fiscal.printer.request", (payload) => {
                    console.log("%c[FiscalPrinter] 🎯 DIRECT CHANNEL SUBSCRIPTION - REQUEST", "color: #00BCD4; font-weight: bold");
                    handlePrinterRequest(payload);
                });

                bus_service.subscribe("fiscal.printer.status", (payload) => {
                    console.log("%c[FiscalPrinter] 🔍 DIRECT CHANNEL SUBSCRIPTION - STATUS", "color: #00BCD4; font-weight: bold");
                    if (payload.action === "check_status") {
                        handleCheckStatusRequest(payload);
                    } else if (payload.action === "status_update") {
                        handleStatusUpdate(payload, notification);
                    }
                });

                console.log("[FiscalPrinter] ✅ Direct channel subscriptions added");
            } catch (e) {
                console.log("[FiscalPrinter] ⚠️ Could not use subscribe method:", e.message);
            }
        }

        // Метод 4: Опитваме през env.bus ако съществува
        if (env.bus) {
            try {
                env.bus.on("notification", null, onBusNotification);
                console.log("[FiscalPrinter] ✅ Added listener via env.bus");
            } catch (e) {
                console.log("[FiscalPrinter] ⚠️ Could not use env.bus:", e.message);
            }
        }

        // DEBUG: Презаписваме някои методи за да видим какво се случва
        if (bus_service._onWebsocketMessage) {
            const original = bus_service._onWebsocketMessage.bind(bus_service);
            bus_service._onWebsocketMessage = function(...args) {
                console.log("%c[FiscalPrinter] 🔴 INTERCEPTED WebSocket Message", "color: red; font-weight: bold; font-size: 14px");
                console.log("[FiscalPrinter] WebSocket args:", args);

                // Извикваме onBusNotification директно с данните
                if (args && args[0]) {
                    onBusNotification(args[0]);
                }

                return original(...args);
            };
            console.log("[FiscalPrinter] ✅ WebSocket interceptor installed");
        }

        console.log("%c[FiscalPrinter] ✅ BUS INITIALIZATION COMPLETE", "color: #4CAF50; font-weight: bold");

        // Уведомяваме сървъра че браузърът е готов
        rpc('/fiscal_printer/browser_ready', {}).then(() => {
            console.log("[FiscalPrinter] ✅ Server notified that browser is ready");
        }).catch(err => {
            console.warn("[FiscalPrinter] ⚠️ Could not notify server:", err.message);
        });

        console.log("%c[FiscalPrinter] ✅ SERVICE STARTED SUCCESSFULLY", "color: #4CAF50; font-weight: bold; font-size: 14px");

        // Публичен API с destroy метод
        return {
            name: "fiscal_printer",

            // Cleanup при унищожаване
            destroy() {
                console.log("[FiscalPrinter] 🧹 Cleaning up service");

                if (bus_service.removeEventListener) {
                    bus_service.removeEventListener("notification", onBusNotification);
                }

                if (bus_service.off) {
                    bus_service.off("notification", onBusNotification);
                }

                console.log("[FiscalPrinter] Service destroyed");
            }
        };
    },
};

registry.category("services").add("fiscal_printer", fiscalPrinterService);
