import logging
import requests
from datetime import datetime
from urllib.parse import urlparse, urljoin
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.addons.l10n_bg_erp_net_fp.models.erp_net_fp_exceptions import (
    FiscalPrinterError,
    FiscalPrinterConnectionError,
    FiscalPrinterValidationError,
    FiscalPrinterResponseError
)

_logger = logging.getLogger(__name__)


class FiscalPrinterDevice(models.Model):
    _name = 'fiscal.printer.device'
    _description = 'Fiscal printer server ErpNet.FP'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', required=True)
    host = fields.Char('Host', required=True, default='http://localhost:8001')
    printer_id = fields.Char('ID on a printer', required=True)
    active = fields.Boolean('Active', default=True)
    timeout = fields.Integer('Timeout', default=30, help='Timeout in seconds')
    retry_count = fields.Integer('Retry Count', default=3, help='Number of retries on failure')
    ssl_verify = fields.Boolean('Verify SSL', default=False,
                                help='Verify SSL certificates (disable for self-signed certificates)')

    auto_z_report = fields.Boolean('Automatic Z report', default=False,
                                   help='Automatic generation of Z report')
    z_report_hour = fields.Integer('Z report time', default=23,
                                   help='Time to generate Z report (0-23)')
    z_report_minute = fields.Integer('Minute for Z report', default=59,
                                     help='Minute to generate Z report (0-59)')
    last_z_report = fields.Datetime('Last Z report', readonly=True)

    @api.constrains('z_report_hour', 'z_report_minute')
    def _check_time_values(self):
        for record in self:
            if not 0 <= record.z_report_hour <= 23:
                raise ValidationError(_('The time must be between 0 and 23'))
            if not 0 <= record.z_report_minute <= 59:
                raise ValidationError(_('Minutes must be between 0 and 59'))

    @api.model
    def _cron_generate_z_reports(self):
        """
        Крон задача за генериране на Z отчети
        Изпълнява се на всеки час
        """
        current_hour = fields.Datetime.now().hour
        current_minute = fields.Datetime.now().minute

        devices = self.search([
            ('active', '=', True),
            ('auto_z_report', '=', True),
            ('z_report_hour', '=', current_hour),
        ])

        for device in devices:
            if current_minute != device.z_report_minute:
                continue

            try:
                _logger.info(f"Start an automatic Z report for {device.name}")
                result = device.print_z_report()
                device.last_z_report = fields.Datetime.now()

                device.message_post(
                    body=_("Successfully generated Z report"),
                    message_type='notification',
                    subtype_id=self.env.ref('mail.mt_note').id
                )

                device.env.cr.commit()
                _logger.info(f"Successful Z report for {device.name}")

            except Exception as e:
                error_message = f"Error generating Z report: {str(e)}"
                _logger.error(f"{device.name}: {error_message}")
                device.env.cr.rollback()

                device.message_post(
                    body=error_message,
                    message_type='notification',
                    subtype_id=self.env.ref('mail.mt_note').id
                )

    def action_test_z_report(self):
        """Тестово действие за Z отчет"""
        self.ensure_one()
        try:
            self.print_z_report()
            self.last_z_report = fields.Datetime.now()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('The Z report has been generated successfully'),
                    'type': 'success',
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': str(e),
                    'type': 'danger',
                }
            }

    def action_test_x_report(self):
        """Тестово действие за X отчет"""
        self.ensure_one()
        try:
            self.print_x_report()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('X report generated successfully'),
                    'type': 'success',
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': str(e),
                    'type': 'danger',
                }
            }

    def _get_session(self):
        """Създава нова сесия за HTTP заявки"""
        session = requests.Session()
        session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        session.verify = self.ssl_verify
        return session

    @api.constrains('host')
    def _check_host(self):
        for record in self:
            try:
                parsed = urlparse(record.host)
                if not parsed.scheme or not parsed.netloc:
                    raise ValidationError(_('Invalid host URL format'))
                if parsed.scheme not in ['http', 'https']:
                    raise ValidationError(_('URL scheme must be http or https'))
                if parsed.scheme == 'https' and not record.ssl_verify:
                    _logger.warning('HTTPS is used with disabled SSL verification for %s', record.name)
            except Exception as e:
                raise ValidationError(_('Invalid host URL: %s') % str(e))

    @api.onchange('ssl_verify')
    def _onchange_ssl_verify(self):
        if not self.ssl_verify:
            parsed = urlparse(self.host)
            if parsed.scheme == 'https':
                return {
                    'warning': {
                        'title': _('Security Warning'),
                        'message': _('Disabling SSL verification for HTTPS connection is not recommended!')
                    }
                }

    def _make_request(self, method, endpoint, data=None, params=None):
        """
        Общ метод за HTTP заявки към ErpNet.FP
        Използва се само от backend операции (Z отчети, X отчети и др.)
        """
        url = urljoin(self.host, endpoint)
        session = self._get_session()

        for attempt in range(self.retry_count):
            try:
                _logger.debug(f"Making {method} request to {url}")

                if method == 'GET':
                    response = session.get(
                        url,
                        params=params,
                        timeout=self.timeout,
                        verify=self.ssl_verify
                    )
                elif method == 'POST':
                    response = session.post(
                        url,
                        json=data,
                        timeout=self.timeout,
                        verify=self.ssl_verify
                    )
                else:
                    raise FiscalPrinterError(_(f'Unsupported HTTP method: {method}'))

                response.raise_for_status()
                return response.json()

            except requests.exceptions.SSLError as e:
                error_msg = f"SSL Error: {str(e)}. Try disabling SSL verification."
                _logger.error(error_msg)
                if attempt == self.retry_count - 1:
                    raise FiscalPrinterError(_(error_msg))
            except requests.exceptions.HTTPError as e:
                error_msg = f"HTTP Error: {e.response.status_code} - {e.response.text}"
                _logger.error(error_msg)
                if attempt == self.retry_count - 1:
                    raise FiscalPrinterError(_(error_msg))
            except requests.exceptions.RequestException as e:
                error_msg = f"Communication error: {str(e)}"
                _logger.error(error_msg)
                if attempt == self.retry_count - 1:
                    raise FiscalPrinterError(_(error_msg))
            finally:
                session.close()

    # ========== ИНФОРМАЦИОННИ МЕТОДИ ==========

    def get_printers(self):
        """Получаване на списък с всички принтери"""
        return self._make_request('GET', 'printers')

    def get_printer_info(self):
        """Информация за конкретен принтер"""
        return self._make_request('GET', f'printers/{self.printer_id}')

    def get_printer_status(self):
        """Статус на принтера"""
        return self._make_request('GET', f'printers/{self.printer_id}/status')

    # ========== X И Z ОТЧЕТИ (BACKEND) ==========

    def print_x_report(self):
        """Печат на X отчет"""
        return self._make_request('POST', f'printers/{self.printer_id}/xreport')

    def print_z_report(self):
        """Печат на Z отчет"""
        return self._make_request('POST', f'printers/{self.printer_id}/zreport')

    # ========== СЛУЖЕБНИ ОПЕРАЦИИ (BACKEND) ==========

    def print_withdraw(self, amount):
        """
        Служебно изведени
        :param amount: сума за извеждане
        """
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValidationError(_('Amount must be a positive number'))

        data = {"amount": amount}
        return self._make_request('POST', f'printers/{self.printer_id}/withdraw', data)

    def print_deposit(self, amount):
        """
        Служебно въведени
        :param amount: сума за въвеждане
        """
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValidationError(_('Amount must be a positive number'))

        data = {"amount": amount}
        return self._make_request('POST', f'printers/{self.printer_id}/deposit', data)

    # ========== ДОПЪЛНИТЕЛНИ ОТЧЕТИ (BACKEND) ==========

    def print_duplicate(self):
        """Печат на дубликат на последния бон"""
        return self._make_request('POST', f'printers/{self.printer_id}/duplicate')

    def print_zero_report(self):
        """Нулиране на оперативната памет с печат на дневен отчет"""
        return self._make_request('POST', f'printers/{self.printer_id}/zeroing')

    def get_journal_info(self, from_date=None, to_date=None):
        """
        Информация за КЛЕН
        :param from_date: начална дата (ISO формат)
        :param to_date: крайна дата (ISO формат)
        """
        params = {}

        for date_str, param_name in [(from_date, 'fromDate'), (to_date, 'toDate')]:
            if date_str:
                try:
                    datetime.fromisoformat(date_str)
                    params[param_name] = date_str
                except ValueError:
                    raise ValidationError(_(f'Invalid date format for {param_name}. Use ISO format (YYYY-MM-DD)'))

        return self._make_request('GET', f'printers/{self.printer_id}/journal', params=params)

    def open_cash_drawer(self):
        """Отваряне на чекмедже"""
        return self._make_request('POST', f'printers/{self.printer_id}/drawer')

    def get_diagnostic_info(self):
        """Диагностична информация"""
        return self._make_request('GET', 'printers/status')

    def raw_device_command(self, command):
        """
        Изпращане на директна команда към устройството
        :param command: командата като string
        """
        if not isinstance(command, str) or not command.strip():
            raise ValidationError(_('Command must be a non-empty string'))

        data = {"Command": command}
        return self._make_request('POST', f'printers/{self.printer_id}/raw', data)

    # ========== МЕТОДИ ЗА СТОРНО И ОБРАТНИ БОНОВЕ (BACKEND) ==========

    def print_reversal_receipt(self, reversal_data):
        """
        Печат на сторно бон
        :param reversal_data: dict с данни за сторно бона
        """
        if not isinstance(reversal_data, dict):
            raise ValidationError(_('Reversal data must be a dictionary'))

        return self._make_request('POST', f'printers/{self.printer_id}/reversalreceipt', reversal_data)
