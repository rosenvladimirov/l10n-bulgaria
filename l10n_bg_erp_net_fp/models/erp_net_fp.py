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

    # Нов режим на работа
    connection_mode = fields.Selection([
        ('direct', 'Direct (Server can access printer)'),
        ('proxy', 'Browser Proxy (Printer in local network)'),
    ], string='Connection Mode', default='direct', required=True, tracking=True,
        help='Direct: Server connects directly to printer\n'
             'Browser Proxy: Browser makes requests and sends results to server')

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

    @api.onchange('host')
    def _onchange_host(self):
        """Автоматично определя режима на работа базирано на host"""
        if self.host:
            parsed = urlparse(self.host)
            hostname = parsed.hostname or ''

            # Ако е localhost или 127.0.0.1 - direct mode
            if hostname in ['localhost', '127.0.0.1', '::1']:
                self.connection_mode = 'direct'
            # Ако е локален IP (192.168.x.x, 10.x.x.x, 172.16-31.x.x) или .local
            elif (hostname.startswith('192.168.') or
                  hostname.startswith('10.') or
                  hostname.startswith('172.') or
                  hostname.endswith('.local')):
                self.connection_mode = 'proxy'
                return {
                    'warning': {
                        'title': _('Connection Mode'),
                        'message': _('Local network address detected. Connection mode set to "Browser Proxy".')
                    }
                }

    def _make_request(self, method, endpoint, data=None, params=None):
        """
        Унифициран метод за HTTP заявки
        Автоматично избира между direct и proxy режим
        """
        if self.connection_mode == 'direct':
            return self._make_direct_request(method, endpoint, data, params)
        else:
            return self._make_proxy_request(method, endpoint, data, params)

    def _make_direct_request(self, method, endpoint, data=None, params=None):
        """
        Директна HTTP заявка от сървъра към принтера
        Използва се когато сървърът има достъп до принтера
        """
        url = urljoin(self.host, endpoint)
        session = self._get_session()

        for attempt in range(self.retry_count):
            try:
                _logger.debug(f"[DIRECT] Making {method} request to {url}")

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
                    raise FiscalPrinterConnectionError(_(error_msg))
            finally:
                session.close()

    def _make_proxy_request(self, method, endpoint, data=None, params=None):
        """
        Proxy HTTP заявка през браузъра
        Използва се когато принтерът е в локална мрежа и сървърът няма достъп
        """
        import uuid
        import time

        request_id = str(uuid.uuid4())

        _logger.info("=" * 80)
        _logger.info(f"[PROXY] 🚀 STARTING PROXY REQUEST")
        _logger.info(f"[PROXY] Request ID: {request_id}")
        _logger.info(f"[PROXY] Printer: {self.name} (ID: {self.id})")
        _logger.info(f"[PROXY] Method: {method}")
        _logger.info(f"[PROXY] Endpoint: {endpoint}")
        _logger.info(f"[PROXY] Data: {data}")
        _logger.info(f"[PROXY] Params: {params}")
        _logger.info("=" * 80)

        # Изпращаме заявка към браузъра
        bus_message = {
            'type': 'printer_request',
            'request_id': request_id,
            'printer_id': self.id,
            'printer_name': self.name,
            'method': method,
            'endpoint': endpoint,
            'data': data,
            'params': params,
        }

        _logger.info(f"[PROXY] 📡 Sending bus notification...")
        _logger.info(f"[PROXY]    Channel: fiscal.printer.request")
        _logger.info(f"[PROXY]    User: {self.env.user.name} (ID: {self.env.user.id})")
        _logger.info(f"[PROXY]    Message: {bus_message}")

        # Изпращаме bus notification
        self.env['bus.bus']._sendone(
            'fiscal.printer.request',
            'fiscal.printer.request',
            bus_message
        )

        # Commit за да се изпрати bus notification-а
        self.env.cr.commit()

        _logger.info(f"[PROXY] ✅ Bus notification sent and committed!")

        # Чакаме отговор от браузъра
        start_time = time.time()
        timeout = self.timeout
        check_count = 0

        _logger.info(f"[PROXY] ⏳ Waiting for response (timeout: {timeout}s)...")

        while time.time() - start_time < timeout:
            check_count += 1
            elapsed = time.time() - start_time

            if check_count % 10 == 1:  # Лог на всеки 5 секунди (10 * 0.5s)
                _logger.info(f"[PROXY] ⏱️ Still waiting... ({elapsed:.1f}s / {timeout}s)")

            # Проверяваме за отговор
            response = self.env['fiscal.printer.response'].search([
                ('request_id', '=', request_id),
                ('printer_id', '=', self.id)
            ], limit=1)

            if response:
                _logger.info(f"[PROXY] 📬 Response found! (after {elapsed:.2f}s)")
                _logger.info(f"[PROXY]    Response ID: {response.id}")
                _logger.info(f"[PROXY]    Success: {response.success}")
                _logger.info(f"[PROXY]    Error: {response.error_message}")

                if response.success:
                    # Изтриваме отговора след прочитане
                    response_data = response.get_data()
                    _logger.info(f"[PROXY] ✅ Request successful!")
                    _logger.info(f"[PROXY]    Data: {response_data}")
                    response.unlink()
                    _logger.info("=" * 80)
                    return response_data
                else:
                    error_msg = response.error_message
                    _logger.error(f"[PROXY] ❌ Request failed: {error_msg}")
                    response.unlink()
                    _logger.info("=" * 80)
                    raise FiscalPrinterError(error_msg)

            # Commit за да видим новите записи
            self.env.cr.commit()
            time.sleep(0.5)

        _logger.error(f"[PROXY] ⏰ TIMEOUT after {timeout}s!")
        _logger.error(f"[PROXY]    No response received from browser")
        _logger.error(f"[PROXY]    Checks performed: {check_count}")
        _logger.info("=" * 80)

        raise FiscalPrinterConnectionError(
            _('Timeout waiting for browser response. Make sure browser is open and has access to printer.')
        )

    def check_printer_available(self):
        """
        Проверява дали принтерът е достъпен
        Връща dict с информация за статуса
        """
        try:
            if self.connection_mode == 'direct':
                # За direct режим - проверяваме директно
                result = self._make_direct_request('GET', f'printers/{self.printer_id}/status')
                return {
                    'available': True,
                    'mode': 'direct',
                    'status': result
                }
            else:
                # За proxy режим - проверяваме през браузъра
                result = self._make_proxy_request('GET', f'printers/{self.printer_id}/status')
                return {
                    'available': True,
                    'mode': 'proxy',
                    'status': result
                }
        except FiscalPrinterConnectionError as e:
            return {
                'available': False,
                'error': str(e),
                'mode': self.connection_mode
            }
        except Exception as e:
            return {
                'available': False,
                'error': str(e),
                'mode': self.connection_mode
            }

    def action_check_connection(self):
        """Action за проверка на връзката от UI"""
        self.ensure_one()

        result = self.check_printer_available()

        if result['available']:
            message = _('Принтерът е достъпен и готов за работа')
            if result.get('status'):
                status = result['status']
                if isinstance(status, dict):
                    details = []
                    if status.get('deviceSerialNumber'):
                        details.append(f"Сериен №: {status['deviceSerialNumber']}")
                    if status.get('firmwareVersion'):
                        details.append(f"Firmware: {status['firmwareVersion']}")
                    if details:
                        message += '\n\n' + '\n'.join(details)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('✅ Връзка успешна'),
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            error_msg = result.get('error', _('Непозната грешка'))
            mode = result.get('mode', 'unknown')

            help_text = ''
            if mode == 'proxy':
                help_text = _(
                    '\n\nЗа режим "Browser Proxy":\n'
                    '• Отворете браузър на машината с достъп до принтера\n'
                    '• Стартирайте ErpNet.FP прокси приложението\n'
                    '• Уверете се, че принтерът е включен и свързан'
                )
            elif mode == 'direct':
                help_text = _(
                    '\n\nЗа режим "Direct":\n'
                    '• Проверете дали ErpNet.FP сървърът е стартиран\n'
                    '• Проверете host адреса: %s\n'
                    '• Уверете се, че принтерът е достъпен от сървъра'
                ) % self.host

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('❌ Няма връзка'),
                    'message': error_msg + help_text,
                    'type': 'danger',
                    'sticky': True,
                }
            }

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

    # ========== X И Z ОТЧЕТИ ==========

    def print_x_report(self):
        """Печат на X отчет"""
        return self._make_request('POST', f'printers/{self.printer_id}/xreport')

    def print_z_report(self):
        """Печат на Z отчет"""
        return self._make_request('POST', f'printers/{self.printer_id}/zreport')

    # ========== СЛУЖЕБНИ ОПЕРАЦИИ ==========

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

    # ========== ДОПЪЛНИТЕЛНИ ОТЧЕТИ ==========

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

    # ========== МЕТОДИ ЗА СТОРНО И ОБРАТНИ БОНОВЕ ==========

    def print_reversal_receipt(self, reversal_data):
        """
        Печат на сторно бон
        :param reversal_data: dict с данни за сторно бона
        """
        if not isinstance(reversal_data, dict):
            raise ValidationError(_('Reversal data must be a dictionary'))

        return self._make_request('POST', f'printers/{self.printer_id}/reversalreceipt', reversal_data)
