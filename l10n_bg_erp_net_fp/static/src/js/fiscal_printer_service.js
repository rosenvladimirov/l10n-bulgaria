/** @odoo-module **/

import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

/**
 * Глобален сервис за комуникация с фискални принтери
 * Слуша за bus notifications и обработва заявки към принтери
 */
export const fiscalPrinterService = {
    dependencies: ["bus_service", "notification"],

    start(env, { bus_service, notification }) {
        let isSubscribed = false;
        let requestCounter = 0;

        console.log("%c[FiscalPrinter] 🚀 SERVICE STARTING", "color: #4CAF50; font-weight: bold; font-size: 14px");
        console.log("[FiscalPrinter] Environment:", env);
        console.log("[FiscalPrinter] Bus service available:", !!bus_service);
        console.log("[FiscalPrinter] Notification service available:", !!notification);

        /**
         * Абонира се за bus каналите
         */
        const subscribeToBus = () => {
            if (!isSubscribed && bus_service) {
                console.log("%c[FiscalPrinter] 📡 SUBSCRIBING TO BUS CHANNELS", "color: #2196F3; font-weight: bold");

                bus_service.addChannel("fiscal.printer.status");
                console.log("[FiscalPrinter] ✅ Subscribed to: fiscal.printer.status");

                bus_service.addChannel("fiscal.printer.request");
                console.log("[FiscalPrinter] ✅ Subscribed to: fiscal.printer.request");

                bus_service.addEventListener("notification", onBusNotification);
                console.log("[FiscalPrinter] ✅ Event listener added");

                isSubscribed = true;
                console.log("%c[FiscalPrinter] ✅ SUBSCRIPTION COMPLETE", "color: #4CAF50; font-weight: bold");
            } else {
                if (isSubscribed) {
                    console.log("[FiscalPrinter] ⚠️ Already subscribed");
                } else {
                    console.error("[FiscalPrinter] ❌ Bus service not available");
                }
            }
        };

        /**
         * Обработва bus notifications
         */
        const onBusNotification = ({ detail: notifications }) => {
            console.log("%c[FiscalPrinter] 📬 BUS NOTIFICATION RECEIVED", "color: #FF9800; font-weight: bold");
            console.log("[FiscalPrinter] Number of notifications:", notifications.length);
            console.log("[FiscalPrinter] Full notifications:", notifications);

            for (const notif of notifications) {
                const { type, payload } = notif;

                console.log("%c[FiscalPrinter] 📦 Processing notification", "color: #9C27B0; font-weight: bold");
                console.log("[FiscalPrinter]    Type:", type);
                console.log("[FiscalPrinter]    Payload:", payload);

                // Генерична заявка към принтера
                if (type === "fiscal.printer.request" && payload.type === "printer_request") {
                    console.log("%c[FiscalPrinter] 🎯 PRINTER REQUEST DETECTED", "color: #00BCD4; font-weight: bold");
                    handlePrinterRequest(payload);
                }

                // Заявка за проверка на статус
                if (type === "fiscal.printer.status" && payload.type === "check_printer_status") {
                    console.log("%c[FiscalPrinter] 🔍 STATUS CHECK REQUEST DETECTED", "color: #00BCD4; font-weight: bold");
                    handleCheckStatusRequest(payload);
                }

                // Обновление на статус
                if (type === "fiscal.printer.status" && payload.type === "printer_status_update") {
                    console.log("%c[FiscalPrinter] 🔄 STATUS UPDATE DETECTED", "color: #00BCD4; font-weight: bold");
                    handleStatusUpdate(payload, notification);
                }
            }
        };

        /**
         * Обработва генерична заявка към принтера
         */
        const handlePrinterRequest = async (data) => {
            requestCounter++;
            const localRequestId = requestCounter;

            const { request_id, printer_id, method, endpoint, data: requestData, params } = data;

            console.log("%c[FiscalPrinter] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "color: #F44336; font-weight: bold");
            console.log(`%c[FiscalPrinter] 🔴 REQUEST #${localRequestId} START`, "color: #F44336; font-weight: bold; font-size: 13px");
            console.log("[FiscalPrinter] Request ID:", request_id);
            console.log("[FiscalPrinter] Printer ID:", printer_id);
            console.log("[FiscalPrinter] Method:", method);
            console.log("[FiscalPrinter] Endpoint:", endpoint);
            console.log("[FiscalPrinter] Request Data:", requestData);
            console.log("[FiscalPrinter] Params:", params);
            console.log("[FiscalPrinter] Timestamp:", new Date().toISOString());

            try {
                // Взимаме конфигурация
                console.log(`[FiscalPrinter] #${localRequestId} 📡 Fetching printer config from server...`);
                const config = await rpc('/fiscal_printer/get_printer_config', {
                    printer_id: printer_id
                });
                console.log(`[FiscalPrinter] #${localRequestId} ✅ Config received:`, config);

                if (config.error) {
                    throw new Error(config.error);
                }

                // Изграждаме URL
                const baseUrl = config.host.replace(/\/$/, '');
                const url = `${baseUrl}/${endpoint}`;

                console.log(`%c[FiscalPrinter] #${localRequestId} 🌐 MAKING HTTP REQUEST`, "color: #3F51B5; font-weight: bold");
                console.log(`[FiscalPrinter] #${localRequestId}    Method: ${method}`);
                console.log(`[FiscalPrinter] #${localRequestId}    URL: ${url}`);
                console.log(`[FiscalPrinter] #${localRequestId}    Base URL: ${baseUrl}`);
                console.log(`[FiscalPrinter] #${localRequestId}    Endpoint: ${endpoint}`);

                // Правим заявка
                const startTime = Date.now();
                const response = await makePrinterRequest(url, method, requestData, params, localRequestId);
                const duration = Date.now() - startTime;

                console.log(`%c[FiscalPrinter] #${localRequestId} ✅ HTTP REQUEST SUCCESS`, "color: #4CAF50; font-weight: bold");
                console.log(`[FiscalPrinter] #${localRequestId}    Duration: ${duration}ms`);
                console.log(`[FiscalPrinter] #${localRequestId}    Response:`, response);

                // Изпращаме отговор към сървъра
                console.log(`[FiscalPrinter] #${localRequestId} 📤 Sending response to server...`);
                await rpc('/fiscal_printer/send_response', {
                    request_id: request_id,
                    printer_id: printer_id,
                    success: true,
                    response_data: response
                });

                console.log(`%c[FiscalPrinter] #${localRequestId} ✅ REQUEST COMPLETED SUCCESSFULLY`, "color: #4CAF50; font-weight: bold; font-size: 13px");
                console.log("%c[FiscalPrinter] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "color: #4CAF50; font-weight: bold");

            } catch (error) {
                console.log(`%c[FiscalPrinter] #${localRequestId} ❌ REQUEST FAILED`, "color: #F44336; font-weight: bold; font-size: 13px");
                console.error(`[FiscalPrinter] #${localRequestId} Error:`, error);
                console.error(`[FiscalPrinter] #${localRequestId} Error message:`, error.message);
                console.error(`[FiscalPrinter] #${localRequestId} Error stack:`, error.stack);

                // Изпращаме грешката към сървъра
                console.log(`[FiscalPrinter] #${localRequestId} 📤 Sending error to server...`);
                try {
                    await rpc('/fiscal_printer/send_response', {
                        request_id: request_id,
                        printer_id: printer_id,
                        success: false,
                        error_message: error.message || 'Unknown error'
                    });
                    console.log(`[FiscalPrinter] #${localRequestId} ✅ Error sent to server`);
                } catch (rpcError) {
                    console.error(`[FiscalPrinter] #${localRequestId} ❌ Failed to send error to server:`, rpcError);
                }

                console.log("%c[FiscalPrinter] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "color: #F44336; font-weight: bold");
            }
        };

        /**
         * Обработва заявка за проверка на статус
         */
        const handleCheckStatusRequest = async (data) => {
            requestCounter++;
            const localRequestId = requestCounter;

            console.log("%c[FiscalPrinter] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "color: #FF9800; font-weight: bold");
            console.log(`%c[FiscalPrinter] 🟠 STATUS CHECK #${localRequestId}`, "color: #FF9800; font-weight: bold; font-size: 13px");
            console.log(`[FiscalPrinter] #${localRequestId} Printer name:`, data.name);
            console.log(`[FiscalPrinter] #${localRequestId} Printer ID:`, data.printer_id);

            try {
                console.log(`[FiscalPrinter] #${localRequestId} 📡 Getting printer config...`);
                const config = await rpc('/fiscal_printer/get_printer_config', {
                    printer_id: data.printer_id
                });
                console.log(`[FiscalPrinter] #${localRequestId} Config:`, config);

                if (config.error) {
                    console.error(`[FiscalPrinter] #${localRequestId} Config error:`, config.error);
                    return;
                }

                const baseUrl = config.host.replace(/\/$/, '');
                const url = `${baseUrl}/printers/${config.printer_id}/status`;

                console.log(`[FiscalPrinter] #${localRequestId} 🌐 Checking status at:`, url);
                const startTime = Date.now();
                const statusData = await makePrinterRequest(url, 'GET', null, null, localRequestId);
                const duration = Date.now() - startTime;

                console.log(`[FiscalPrinter] #${localRequestId} ✅ Status received (${duration}ms):`, statusData);

                console.log(`[FiscalPrinter] #${localRequestId} 📤 Updating status on server...`);
                await rpc('/fiscal_printer/update_status', {
                    printer_id: data.printer_id,
                    status_data: statusData
                });

                console.log(`%c[FiscalPrinter] #${localRequestId} ✅ STATUS CHECK COMPLETE`, "color: #4CAF50; font-weight: bold");
                console.log("%c[FiscalPrinter] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "color: #4CAF50; font-weight: bold");

            } catch (error) {
                console.log(`%c[FiscalPrinter] #${localRequestId} ❌ STATUS CHECK FAILED`, "color: #F44336; font-weight: bold");
                console.error(`[FiscalPrinter] #${localRequestId} Error:`, error);

                console.log(`[FiscalPrinter] #${localRequestId} 📤 Sending error status to server...`);
                await rpc('/fiscal_printer/update_status', {
                    printer_id: data.printer_id,
                    status_data: {
                        status: 'error',
                        errorMessage: error.message || 'Connection error',
                        ok: false
                    }
                });

                console.log("%c[FiscalPrinter] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "color: #F44336; font-weight: bold");
            }
        };

        /**
         * Обработва обновление на статус
         */
        const handleStatusUpdate = (data, notificationService) => {
            console.log("%c[FiscalPrinter] 🔔 STATUS UPDATE NOTIFICATION", "color: #9C27B0; font-weight: bold");
            console.log("[FiscalPrinter] Printer name:", data.name);
            console.log("[FiscalPrinter] Status:", data.status);
            console.log("[FiscalPrinter] Is ready:", data.is_ready);

            // Показваме notification
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
            console.log(`[FiscalPrinter] #${requestId} 🔧 Preparing fetch request...`);

            const options = {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                mode: 'cors',
            };

            console.log(`[FiscalPrinter] #${requestId}    Headers:`, options.headers);
            console.log(`[FiscalPrinter] #${requestId}    Mode:`, options.mode);

            if (method === 'POST' && data) {
                options.body = JSON.stringify(data);
                console.log(`[FiscalPrinter] #${requestId}    Body:`, options.body);
            }

            if (method === 'GET' && params) {
                const queryString = new URLSearchParams(params).toString();
                url = `${url}?${queryString}`;
                console.log(`[FiscalPrinter] #${requestId}    Query params:`, queryString);
            }

            console.log(`[FiscalPrinter] #${requestId} 🚀 Executing fetch to:`, url);
            console.log(`[FiscalPrinter] #${requestId}    Full options:`, options);

            const fetchStart = Date.now();
            const response = await fetch(url, options);
            const fetchDuration = Date.now() - fetchStart;

            console.log(`[FiscalPrinter] #${requestId} 📥 Fetch response received (${fetchDuration}ms)`);
            console.log(`[FiscalPrinter] #${requestId}    Status:`, response.status);
            console.log(`[FiscalPrinter] #${requestId}    Status text:`, response.statusText);
            console.log(`[FiscalPrinter] #${requestId}    OK:`, response.ok);
            console.log(`[FiscalPrinter] #${requestId}    Headers:`, Array.from(response.headers.entries()));

            if (!response.ok) {
                const errorText = await response.text();
                console.error(`[FiscalPrinter] #${requestId} ❌ HTTP Error response body:`, errorText);
                throw new Error(`HTTP error! status: ${response.status}, body: ${errorText}`);
            }

            console.log(`[FiscalPrinter] #${requestId} 📄 Parsing JSON response...`);
            const jsonStart = Date.now();
            const result = await response.json();
            const jsonDuration = Date.now() - jsonStart;

            console.log(`[FiscalPrinter] #${requestId} ✅ JSON parsed (${jsonDuration}ms)`);
            console.log(`[FiscalPrinter] #${requestId}    Result:`, result);

            return result;
        };

        // Абонираме се веднага
        console.log("[FiscalPrinter] 🎬 Calling subscribeToBus()...");
        subscribeToBus();

        console.log("%c[FiscalPrinter] ✅ SERVICE STARTED SUCCESSFULLY", "color: #4CAF50; font-weight: bold; font-size: 14px");

        // Връщаме публичен API на сервиза
        return {
            subscribeToBus,
        };
    },
};

registry.category("services").add("fiscal_printer", fiscalPrinterService);
