/** @odoo-module **/

import { registry } from "@web/core/registry";
import { jsonrpc } from "@web/core/network/rpc_service";

/**
 * Глобален сервис за комуникация с фискални принтери
 * Слуша за bus notifications и обработва заявки към принтери
 */
export const fiscalPrinterService = {
    dependencies: ["bus_service", "notification"],

    start(env, { bus_service, notification }) {
        let isSubscribed = false;

        /**
         * Абонира се за bus каналите
         */
        const subscribeToBus = () => {
            if (!isSubscribed && bus_service) {
                bus_service.addChannel("fiscal.printer.status");
                bus_service.addChannel("fiscal.printer.request");
                bus_service.addEventListener("notification", onBusNotification);
                isSubscribed = true;
                console.log("[FiscalPrinter] Service subscribed to bus channels");
            }
        };

        /**
         * Обработва bus notifications
         */
        const onBusNotification = ({ detail: notifications }) => {
            for (const notif of notifications) {
                const { type, payload } = notif;

                // Генерична заявка към принтера
                if (type === "fiscal.printer.request" && payload.type === "printer_request") {
                    handlePrinterRequest(payload);
                }

                // Заявка за проверка на статус
                if (type === "fiscal.printer.status" && payload.type === "check_printer_status") {
                    handleCheckStatusRequest(payload);
                }

                // Обновление на статус
                if (type === "fiscal.printer.status" && payload.type === "printer_status_update") {
                    handleStatusUpdate(payload, notification);
                }
            }
        };

        /**
         * Обработва генерична заявка към принтера
         */
        const handlePrinterRequest = async (data) => {
            const { request_id, printer_id, method, endpoint, data: requestData, params } = data;

            console.log(`[FiscalPrinter] Handling request ${request_id} for printer ${printer_id}`);

            try {
                // Взимаме конфигурация
                const config = await jsonrpc('/fiscal_printer/get_printer_config', {
                    printer_id: printer_id
                });

                if (config.error) {
                    throw new Error(config.error);
                }

                // Изграждаме URL
                const baseUrl = config.host.replace(/\/$/, '');
                const url = `${baseUrl}/${endpoint}`;

                console.log(`[FiscalPrinter] Making ${method} request to ${url}`);

                // Правим заявка
                const response = await makePrinterRequest(url, method, requestData, params);

                // Изпращаме отговор към сървъра
                await jsonrpc('/fiscal_printer/send_response', {
                    request_id: request_id,
                    printer_id: printer_id,
                    success: true,
                    response_data: response
                });

                console.log(`[FiscalPrinter] Request ${request_id} completed successfully`);

            } catch (error) {
                console.error(`[FiscalPrinter] Error handling request ${request_id}:`, error);

                // Изпращаме грешката към сървъра
                await jsonrpc('/fiscal_printer/send_response', {
                    request_id: request_id,
                    printer_id: printer_id,
                    success: false,
                    error_message: error.message || 'Unknown error'
                });
            }
        };

        /**
         * Обработва заявка за проверка на статус
         */
        const handleCheckStatusRequest = async (data) => {
            console.log(`[FiscalPrinter] Status check requested for printer ${data.name}`);

            try {
                const config = await jsonrpc('/fiscal_printer/get_printer_config', {
                    printer_id: data.printer_id
                });

                if (config.error) {
                    console.error(`Error getting printer config: ${config.error}`);
                    return;
                }

                const baseUrl = config.host.replace(/\/$/, '');
                const url = `${baseUrl}/printers/${config.printer_id}/status`;

                const statusData = await makePrinterRequest(url, 'GET');

                await jsonrpc('/fiscal_printer/update_status', {
                    printer_id: data.printer_id,
                    status_data: statusData
                });

                console.log(`[FiscalPrinter] Status updated for printer ${data.name}`);

            } catch (error) {
                console.error(`[FiscalPrinter] Error checking status:`, error);

                await jsonrpc('/fiscal_printer/update_status', {
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
            console.log(`[FiscalPrinter] Status update received for ${data.name}`);

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
        const makePrinterRequest = async (url, method, data = null, params = null) => {
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

            const response = await fetch(url, options);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        };

        // Абонираме се веднага
        subscribeToBus();

        // Връщаме публичен API на сервиза
        return {
            subscribeToBus,
        };
    },
};

registry.category("services").add("fiscal_printer", fiscalPrinterService);
