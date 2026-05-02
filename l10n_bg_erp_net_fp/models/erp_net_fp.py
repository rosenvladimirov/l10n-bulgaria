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

    def _proxy_or_direct_action(self, endpoint, success_title, success_msg,
                                  method="POST", on_success=None):
        # Proxy mode → връщаме client action; browser-а сам fetch-ва
        # printer URL директно (без bus channels, без server-side
        # timeout). Direct mode → server-side request както досега.
        self.ensure_one()
        if self.connection_mode == "proxy":
            return {
                "type": "ir.actions.client",
                "tag": "l10n_bg_fiscal_browser_proxy",
                "params": {
                    "device_id": self.id,
                    "host": self.host,
                    "printer_id": self.printer_id,
                    "method": method,
                    "endpoint": endpoint,
                    "ssl_verify": self.ssl_verify,
                    "success_title": success_title,
                    "success_message": success_msg,
                    "on_success": on_success,  # ORM call name on device, optional
                },
            }
        # Direct mode — keep the existing server-side path
        try:
            self._make_request(method, endpoint)
            if on_success:
                getattr(self, on_success, lambda: None)()
            return {
                "type": "ir.actions.client", "tag": "display_notification",
                "params": {"title": success_title, "message": success_msg,
                           "type": "success"},
            }
        except Exception as e:
            return {
                "type": "ir.actions.client", "tag": "display_notification",
                "params": {"title": _("Error"), "message": str(e),
                           "type": "danger"},
            }

    def action_test_z_report(self):
        return self._proxy_or_direct_action(
            endpoint=f"printers/{self.printer_id}/zreport",
            success_title=_("Success"),
            success_msg=_("The Z report has been generated successfully"),
            on_success="_mark_last_z_report",
        )

    def _mark_last_z_report(self):
        self.last_z_report = fields.Datetime.now()

    def action_test_x_report(self):
        return self._proxy_or_direct_action(
            endpoint=f"printers/{self.printer_id}/xreport",
            success_title=_("Success"),
            success_msg=_("X report generated successfully"),
        )

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

        # Проверка дали браузърът е свързан
        base_url = self.host.rstrip('/')
        full_url = f"{base_url}/printers/{self.printer_id}"

        # Няма свързан браузър
        if not self.proxy_connected:
            last_seen = ''
            if self.proxy_last_seen:
                last_seen = fields.Datetime.to_string(self.proxy_last_seen)
            raise FiscalPrinterConnectionError(_(
                'No browser connected for proxy printer.\n'
                '\n'
                'Printer:        %(name)s\n'
                'Host:           %(host)s\n'
                'Printer ID:     %(printer_id)s\n'
                'URL:            %(url)s\n'
                'Mode:           %(mode)s\n'
                'Last heartbeat: %(last_seen)s\n'
                '\n'
                'Open Odoo in a browser on a machine that has network access to the printer.',
                name=self.name,
                host=self.host,
                printer_id=self.printer_id,
                url=full_url,
                mode=self.connection_mode,
                last_seen=last_seen or 'never',
            ))

        # Браузърът е свързан, но принтерът не е достъпен
        if not self.proxy_printer_ok:
            user_name = self.proxy_user_id.name or '?'
            raise FiscalPrinterConnectionError(_(
                'Browser is connected but the printer is not reachable.\n'
                '\n'
                'Printer:      %(name)s\n'
                'Host:         %(host)s\n'
                'Printer ID:   %(printer_id)s\n'
                'URL:          %(url)s\n'
                'Connected by: %(user)s\n'
                '\n'
                'Please check:\n'
                '  - Is ErpNet.FP running on %(host)s?\n'
                '  - Is the printer powered on and connected?\n'
                '  - Does the browser have network access to %(host)s?',
                name=self.name,
                host=self.host,
                printer_id=self.printer_id,
                url=full_url,
                user=user_name,
            ))

        request_id = str(uuid.uuid4())

        _logger.info(f"[PROXY] STARTING PROXY REQUEST: {method} {endpoint} "
                      f"printer={self.name} request_id={request_id}")

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

        self.env['bus.bus']._sendone(
            'fiscal.printer.request',
            'fiscal.printer.request',
            bus_message
        )
        self.env.cr.commit()

        _logger.info(f"[PROXY] Waiting for response (timeout: {self.timeout}s)...")

        # Чакаме отговор от браузъра
        start_time = time.time()
        timeout = self.timeout
        check_count = 0

        while time.time() - start_time < timeout:
            check_count += 1
            elapsed = time.time() - start_time

            if check_count % 10 == 1:
                _logger.info(f"[PROXY] Waiting... ({elapsed:.1f}s / {timeout}s)")

            response = self.env['fiscal.printer.response'].search([
                ('request_id', '=', request_id),
                ('printer_id', '=', self.id)
            ], limit=1)

            if response:
                _logger.info(f"[PROXY] Response received after {elapsed:.1f}s "
                              f"success={response.success}")

                if response.success:
                    response_data = response.get_data()
                    response.unlink()
                    return response_data
                else:
                    error_msg = response.error_message
                    response.unlink()
                    raise FiscalPrinterError(error_msg)

            self.env.cr.commit()
            time.sleep(0.5)

        _logger.error(f"[PROXY] TIMEOUT after {timeout}s, checks={check_count}")

        raise FiscalPrinterConnectionError(_(
            'Timeout: no response from browser within %(timeout)ds.\n'
            '\n'
            'Printer:     %(name)s\n'
            'Host:        %(host)s\n'
            'Printer ID:  %(printer_id)s\n'
            'URL:         %(url)s\n'
            'Endpoint:    %(endpoint)s\n'
            '\n'
            'The browser is connected but did not respond in time.\n'
            'Check if the printer is responding and no operation is blocking it.',
            timeout=timeout,
            name=self.name,
            host=self.host,
            printer_id=self.printer_id,
            url=full_url,
            endpoint=endpoint,
        ))

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
            message = _('Printer is available and ready')
            if result.get('status'):
                status = result['status']
                if isinstance(status, dict):
                    details = []
                    if status.get('deviceSerialNumber'):
                        details.append(f"Serial: {status['deviceSerialNumber']}")
                    if status.get('firmwareVersion'):
                        details.append(f"Firmware: {status['firmwareVersion']}")
                    if details:
                        message += '\n\n' + '\n'.join(details)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection successful'),
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            error_msg = result.get('error', _('Unknown error'))
            mode = result.get('mode', 'unknown')

            help_text = ''
            if mode == 'proxy':
                help_text = _(
                    '\n\nFor "Browser Proxy" mode:\n'
                    '- Open a browser on the machine with access to the printer\n'
                    '- Make sure ErpNet.FP is running\n'
                    '- Make sure the printer is powered on and connected'
                )
            elif mode == 'direct':
                help_text = _(
                    '\n\nFor "Direct" mode:\n'
                    '- Check if the ErpNet.FP server is running\n'
                    '- Verify host address: %s\n'
                    '- Make sure the printer is reachable from the server'
                ) % self.host

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection failed'),
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
