import logging
import requests
from datetime import datetime
from urllib.parse import urlparse, urljoin
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.addons.l10n_bg_erp_net_fp.models.exceptions import (
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
    ssl_verify = fields.Boolean('Verify SSL', default=True,
                               help='Verify SSL certificates using system CA certificates')

    auto_z_report = fields.Boolean('Автоматичен Z отчет', default=False,
                                   help='Автоматично генериране на Z отчет')
    z_report_hour = fields.Integer('Час за Z отчет', default=23,
                                   help='Час за генериране на Z отчет (0-23)')
    z_report_minute = fields.Integer('Минута за Z отчет', default=59,
                                     help='Минута за генериране на Z отчет (0-59)')
    last_z_report = fields.Datetime('Последен Z отчет', readonly=True)

    @api.constrains('z_report_hour', 'z_report_minute')
    def _check_time_values(self):
        for record in self:
            if not 0 <= record.z_report_hour <= 23:
                raise ValidationError(_('Часът трябва да бъде между 0 и 23'))
            if not 0 <= record.z_report_minute <= 59:
                raise ValidationError(_('Минутите трябва да бъдат между 0 и 59'))

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
                _logger.info(f"Започване на автоматичен Z отчет за {device.name}")
                result = device.print_z_report()
                device.last_z_report = fields.Datetime.now()

                # Добавяме съобщение в чата
                device.message_post(
                    body=_("Успешно генериран Z отчет"),
                    message_type='notification',
                    subtype_id=self.env.ref('mail.mt_note').id
                )

                device.env.cr.commit()
                _logger.info(f"Успешен Z отчет за {device.name}")

            except Exception as e:
                error_message = f"Грешка при генериране на Z отчет: {str(e)}"
                _logger.error(f"{device.name}: {error_message}")
                device.env.cr.rollback()

                # Добавяме съобщение за грешка в чата
                device.message_post(
                    body=error_message,
                    message_type='notification',
                    subtype_id=self.env.ref('mail.mt_note').id
                )

    def action_test_z_report(self):
        """
        Тестово действие за Z отчет
        """
        self.ensure_one()
        try:
            self.print_z_report()
            self.last_z_report = fields.Datetime.now()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Успех'),
                    'message': _('Z отчетът е генериран успешно'),
                    'type': 'success',
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Грешка'),
                    'message': str(e),
                    'type': 'danger',
                }
            }

    def _get_session(self):
        """Създава нова сесия за HTTP заявки с SSL поддръжка"""
        session = requests.Session()
        session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

        # Използваме системните CA сертификати
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
                # Проверка дали HTTPS се използва правилно
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
        Общ метод за HTTP заявки
        :param method: HTTP метод ('GET' или 'POST')
        :param endpoint: крайна точка на API
        :param data: данни за заявката (за POST)
        :param params: параметри на URL (за GET)
        :return: JSON отговор
        :raises: FiscalPrinterError при проблем с комуникацията
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
                        verify=True
                    )
                elif method == 'POST':
                    response = session.post(
                        url,
                        json=data,
                        timeout=self.timeout,
                        verify=True
                    )
                else:
                    raise FiscalPrinterError(_(f'Unsupported HTTP method: {method}'))

                response.raise_for_status()
                return response.json()

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

    # Информационни методи
    def get_printers(self):
        """Получаване на списък с всички принтери"""
        return self._make_request('GET', 'printers')

    def get_printer_info(self):
        """Информация за конкретен принтер"""
        return self._make_request('GET', f'printers/{self.printer_id}')

    def get_printer_status(self):
        """Статус на принтера"""
        return self._make_request('GET', f'printers/{self.printer_id}/status')

    # Печат на документи
    def print_receipt(self, receipt_data):
        """
        Печат на фискален бон
        :param receipt_data: dict с данни за бона
        :raises: ValidationError при невалидни данни
        Пример:
        {
            "uniqueSale": true,
            "items": [
                {
                    "text": "Продукт 1",
                    "quantity": 1,
                    "unitPrice": 10.50,
                    "taxGroup": "Б"
                }
            ],
            "payments": [
                {
                    "amount": 10.50,
                    "paymentType": "cash"
                }
            ]
        }
        """
        if not isinstance(receipt_data, dict):
            raise ValidationError(_('Receipt data must be a dictionary'))

        required_fields = ['items', 'payments']
        for field in required_fields:
            if field not in receipt_data:
                raise ValidationError(_(f'Missing required field: {field}'))

        return self._make_request('POST', f'printers/{self.printer_id}/receipt', receipt_data)

    def print_reversal_receipt(self, reversal_data):
        """
        Печат на сторно бон
        :param reversal_data: dict с данни за сторно бона
        :raises: ValidationError при невалидни данни
        """
        if not isinstance(reversal_data, dict):
            raise ValidationError(_('Reversal data must be a dictionary'))

        return self._make_request('POST', f'printers/{self.printer_id}/reversalreceipt', reversal_data)

    def print_withdraw(self, amount):
        """
        Служебно изведени
        :param amount: сума за извеждане
        :raises: ValidationError при невалидна сума
        """
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValidationError(_('Amount must be a positive number'))

        data = {"amount": amount}
        return self._make_request('POST', f'printers/{self.printer_id}/withdraw', data)

    def print_deposit(self, amount):
        """
        Служебно въведени
        :param amount: сума за въвеждане
        :raises: ValidationError при невалидна сума
        """
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValidationError(_('Amount must be a positive number'))

        data = {"amount": amount}
        return self._make_request('POST', f'printers/{self.printer_id}/deposit', data)

    # X и Z отчети
    def print_x_report(self):
        """Печат на X отчет"""
        return self._make_request('POST', f'printers/{self.printer_id}/xreport')

    def print_z_report(self):
        """Печат на Z отчет"""
        return self._make_request('POST', f'printers/{self.printer_id}/zreport')

    # Допълнителни отчети
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
        :raises: ValidationError при невалиден формат на дата
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
        :raises: ValidationError при невалидна команда
        """
        if not isinstance(command, str) or not command.strip():
            raise ValidationError(_('Command must be a non-empty string'))

        data = {"Command": command}
        return self._make_request('POST', f'printers/{self.printer_id}/raw', data)
