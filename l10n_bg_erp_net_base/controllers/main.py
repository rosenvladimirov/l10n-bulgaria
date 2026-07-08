# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class FiscalPrinterController(http.Controller):
    """Контролер за browser proxy комуникация"""

    @http.route('/fiscal_printer/get_printer_config', type='json', auth='user')
    def get_printer_config(self, printer_id, **kw):
        """Връща конфигурацията на принтера за браузъра"""
        try:
            _logger.info(f"[ProxyController] Getting config for printer ID: {printer_id}")

            printer = request.env['fiscal.printer.device'].sudo().browse(printer_id)

            if not printer.exists():
                _logger.error(f"[ProxyController] Printer {printer_id} not found")
                return {'error': 'Printer not found'}

            config = {
                'id': printer.id,
                'name': printer.name,
                'host': printer.host,
                'printer_id': printer.printer_id,
                'connection_mode': printer.connection_mode,
            }

            _logger.info(f"[ProxyController] Returning config: {config}")
            return config

        except Exception as e:
            _logger.error(f"[ProxyController] Error getting config: {str(e)}", exc_info=True)
            return {'error': str(e)}

    @http.route('/fiscal_printer/send_response', type='json', auth='user')
    def send_response(self, request_id, printer_id, success, response_data=None, error_message=None, **kw):
        """Приема отговор от браузъра и го записва в базата"""
        try:
            _logger.info(f"[ProxyController] Received response for request {request_id}")
            _logger.info(f"[ProxyController]    Printer ID: {printer_id}")
            _logger.info(f"[ProxyController]    Success: {success}")
            _logger.info(f"[ProxyController]    Error: {error_message}")

            response = request.env['fiscal.printer.response'].sudo().create({
                'request_id': request_id,
                'printer_id': printer_id,
                'success': success,
                'response_data': json.dumps(response_data) if response_data else None,
                'error_message': error_message,
            })

            _logger.info(f"[ProxyController] Response record created: {response.id}")
            return {'status': 'ok', 'response_id': response.id}

        except Exception as e:
            _logger.error(f"[ProxyController] Error saving response: {str(e)}", exc_info=True)
            return {'error': str(e)}

    @http.route('/fiscal_printer/update_status', type='json', auth='user')
    def update_status(self, printer_id, status_data, **kw):
        """Обновява статуса на принтера"""
        try:
            _logger.info(f"[ProxyController] Updating status for printer {printer_id}")
            _logger.info(f"[ProxyController]    Status data: {status_data}")

            printer = request.env['fiscal.printer.device'].sudo().browse(printer_id)

            if not printer.exists():
                _logger.error(f"[ProxyController] Printer {printer_id} not found")
                return {'error': 'Printer not found'}

            # Създаваме статус запис
            status_record = request.env['fiscal.printer.status'].sudo().create({
                'printer_id': printer_id,
                'status': status_data.get('status', 'unknown'),
                'error_message': status_data.get('errorMessage'),
                'is_ready': status_data.get('ok', False),
                'serial_number': status_data.get('deviceSerialNumber'),
                'firmware_version': status_data.get('firmwareVersion'),
            })

            _logger.info(f"[ProxyController] Status record created: {status_record.id}")
            return {'status': 'ok', 'status_id': status_record.id}

        except Exception as e:
            _logger.error(f"[ProxyController] Error updating status: {str(e)}", exc_info=True)
            return {'error': str(e)}

    @http.route('/fiscal_printer/browser_ready', type='json', auth='user')
    def browser_ready(self, **kw):
        """Сигнал от браузъра че е готов — връща proxy принтерите за health check"""
        _logger.info(f"[ProxyController] Browser ready from user: {request.env.user.name}")

        printers = request.env['fiscal.printer.device'].sudo().search([
            ('active', '=', True),
            ('connection_mode', '=', 'proxy'),
        ])

        # Записваме начален статус — браузър свързан
        Status = request.env['fiscal.printer.status'].sudo()
        now = datetime.now()
        for p in printers:
            p.write({
                'proxy_last_seen': now,
                'proxy_user_id': request.env.user.id,
            })
            Status.create({
                'printer_id': p.id,
                'status': 'browser_connected',
                'is_ready': False,
                'error_message': False,
            })

        printer_list = [{
            'id': p.id,
            'name': p.name,
            'host': p.host,
            'printer_id': p.printer_id,
        } for p in printers]

        return {'status': 'ok', 'proxy_printers': printer_list}

    @http.route('/fiscal_printer/heartbeat', type='json', auth='user')
    def heartbeat(self, printer_results=None, **kw):
        """Периодичен heartbeat от браузъра с резултати от health check"""
        now = datetime.now()
        user = request.env.user

        if not printer_results:
            return {'status': 'ok'}

        Printer = request.env['fiscal.printer.device'].sudo()
        Status = request.env['fiscal.printer.status'].sudo()

        for result in printer_results:
            printer = Printer.browse(result['id'])
            if not printer.exists() or printer.connection_mode != 'proxy':
                continue

            reachable = result.get('reachable', False)
            prev_ok = printer.proxy_printer_ok

            printer.write({
                'proxy_last_seen': now,
                'proxy_user_id': user.id,
                'proxy_printer_ok': reachable,
            })

            # Записваме в историята при промяна на статуса
            if reachable != prev_ok:
                if reachable:
                    status_text = 'online'
                    error_msg = False
                else:
                    status_text = 'unreachable'
                    error_msg = f'Browser proxy: printer not reachable at {printer.host}'

                Status.create({
                    'printer_id': printer.id,
                    'status': status_text,
                    'is_ready': reachable,
                    'error_message': error_msg,
                })

        return {'status': 'ok'}

    @http.route('/fiscal_printer/test_notification', type='json', auth='user')
    def test_notification(self, **kw):
        """Тестова заявка за проверка на bus notifications"""
        _logger.info(f"[ProxyController] 🧪 Test notification requested")

        # Изпращаме тестово съобщение
        request.env['bus.bus']._sendone(
            'fiscal.printer.request',
            'test',
            {
                'type': 'test',
                'message': 'Test notification from server',
                'timestamp': datetime.now().isoformat()
            }
        )

        _logger.info(f"[ProxyController] ✅ Test notification sent")
        return {'status': 'ok', 'message': 'Test notification sent'}
