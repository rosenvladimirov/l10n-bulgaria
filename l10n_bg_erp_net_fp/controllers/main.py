# -*- coding: utf-8 -*-
import logging
import json
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class FiscalPrinterController(http.Controller):

    @http.route('/fiscal_printer/update_status', type='json', auth='user')
    def update_printer_status(self, printer_id, status_data):
        """Приема статус данни от JavaScript"""
        try:
            printer = request.env['fiscal.printer.device'].browse(printer_id)

            if not printer.exists():
                return {'error': 'Printer not found'}

            request.env['fiscal.printer.status'].create({
                'printer_id': printer.id,
                'status': status_data.get('status'),
                'error_message': status_data.get('errorMessage'),
                'is_ready': status_data.get('ok', False),
                'paper_available': status_data.get('paperAvailable', False),
                'fiscal_memory_available': status_data.get('fiscalMemoryAvailable', False),
                'document_number': status_data.get('documentNumber'),
                'serial_number': status_data.get('serialNumber'),
                'firmware_version': status_data.get('firmwareVersion')
            })

            request.env['bus.bus']._sendone(
                'fiscal.printer.status',
                'printer_status_update',
                {
                    'type': 'printer_status_update',
                    'printer_id': printer.id,
                    'name': printer.name,
                    'status': status_data.get('status'),
                    'is_ready': status_data.get('ok', False),
                    'error_message': status_data.get('errorMessage'),
                }
            )

            return {'success': True}

        except Exception as e:
            _logger.error(f"Error updating printer status: {str(e)}")
            return {'error': str(e)}

    @http.route('/fiscal_printer/get_printer_config', type='json', auth='user')
    def get_printer_config(self, printer_id):
        """Връща конфигурацията на принтера за JavaScript"""
        try:
            printer = request.env['fiscal.printer.device'].browse(printer_id)

            if not printer.exists():
                return {'error': 'Printer not found'}

            return {
                'id': printer.id,
                'name': printer.name,
                'host': printer.host,
                'printer_id': printer.printer_id,
                'timeout': printer.timeout,
            }

        except Exception as e:
            _logger.error(f"Error getting printer config: {str(e)}")
            return {'error': str(e)}

    @http.route('/fiscal_printer/send_response', type='json', auth='user')
    def send_response(self, request_id, printer_id, success, response_data=None, error_message=None):
        """
        Приема отговор от client-side заявка
        """
        try:
            request.env['fiscal.printer.response'].create_from_client(
                request_id=request_id,
                printer_id=printer_id,
                success=success,
                response_data=response_data,
                error_message=error_message
            )
            request.env.cr.commit()

            return {'success': True}

        except Exception as e:
            _logger.error(f"Error saving printer response: {str(e)}")
            return {'error': str(e)}
