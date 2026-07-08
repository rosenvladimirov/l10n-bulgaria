# -*- coding: utf-8 -*-
from odoo import models, fields, api
import json


class FiscalPrinterResponse(models.Model):
    _name = 'fiscal.printer.response'
    _description = 'Fiscal Printer Response'
    _rec_name = 'request_id'
    _order = 'create_date desc'

    request_id = fields.Char('Request ID', required=True, index=True)
    printer_id = fields.Many2one('fiscal.printer.device', 'Printer', required=True, ondelete='cascade')
    success = fields.Boolean('Success', default=False)
    response_data = fields.Text('Response Data')
    error_message = fields.Text('Error Message')

    def get_data(self):
        """Връща response данните като dict/list"""
        self.ensure_one()
        if self.response_data:
            return json.loads(self.response_data)
        return None

    @api.model
    def create_from_client(self, request_id, printer_id, success, response_data=None, error_message=None):
        """Създава response запис от client-side заявка"""
        return self.create({
            'request_id': request_id,
            'printer_id': printer_id,
            'success': success,
            'response_data': json.dumps(response_data) if response_data else None,
            'error_message': error_message,
        })

    @api.model
    def _cron_cleanup_old_responses(self):
        """Изчиства отговори по-стари от 1 час"""
        from datetime import timedelta
        cutoff = fields.Datetime.now() - timedelta(hours=1)
        old_responses = self.search([('create_date', '<', cutoff)])
        count = len(old_responses)
        old_responses.unlink()
        return count
