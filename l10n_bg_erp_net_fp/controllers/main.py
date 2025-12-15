# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)
_logger.info("=" * 80)
_logger.info("🚀 FiscalPrinterController LOADING")
_logger.info("=" * 80)


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
        """Сигнал от браузъра че е готов"""
        _logger.info(f"[ProxyController] 🌐 Browser ready signal received from user: {request.env.user.name}")
        _logger.info(f"[ProxyController]    Session ID: {request.session.sid}")
        _logger.info(f"[ProxyController]    DB: {request.env.cr.dbname}")
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
