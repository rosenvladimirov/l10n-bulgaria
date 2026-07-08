import logging
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

# Per-operation browser-fetch timeouts (in milliseconds).
# Datecs ISL devices (DP-150 / DP-150X / FP-700X) drive the floor here:
# X/Z-reports run 60-90s end-to-end. The transport layer (base) exposes the
# same constants; kept here for the fiscal report calls below.
OP_TIMEOUT_REPORT_MS = 90000   # X-report, Z-report


class FiscalPrinterDevice(models.Model):
    """Фискален слой върху транспортното ядро `fiscal.printer.device`.

    Транспортът (host/connection_mode + HTTP/bus заявки) е дефиниран в
    `l10n_bg_erp_net_base`. Тук се добавят САМО фискалните операции:
    Z/X отчети, служебни суми, дубликат, КЛЕН, сторно + авто-Z крон.
    """

    _inherit = 'fiscal.printer.device'

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

    # ========== X И Z ОТЧЕТИ ==========

    def action_test_z_report(self):
        return self._proxy_or_direct_action(
            endpoint=f"printers/{self.printer_id}/zreport",
            success_title=_("Success"),
            success_msg=_("The Z report has been generated successfully"),
            on_success="_mark_last_z_report",
            timeout_ms=OP_TIMEOUT_REPORT_MS,
        )

    def _mark_last_z_report(self):
        self.last_z_report = fields.Datetime.now()

    def action_test_x_report(self):
        return self._proxy_or_direct_action(
            endpoint=f"printers/{self.printer_id}/xreport",
            success_title=_("Success"),
            success_msg=_("X report generated successfully"),
            timeout_ms=OP_TIMEOUT_REPORT_MS,
        )

    def print_x_report(self):
        """Печат на X отчет — в proxy mode връща client action; в
        direct mode прави HTTP заявка от сървъра."""
        self.ensure_one()
        if self.connection_mode == "proxy":
            return self._proxy_or_direct_action(
                endpoint=f"printers/{self.printer_id}/xreport",
                success_title=_("Success"),
                success_msg=_("X report generated successfully"),
                timeout_ms=OP_TIMEOUT_REPORT_MS,
            )
        # timeout=90s: Datecs ISL X-report върви 60-90s (виж
        # OP_TIMEOUT_REPORT_MS) — device default-ът 30s не стига.
        return self._make_request(
            "POST", f"printers/{self.printer_id}/xreport",
            timeout=OP_TIMEOUT_REPORT_MS / 1000)

    def print_z_report(self):
        """Печат на Z отчет — в proxy mode връща client action; в
        direct mode прави HTTP заявка от сървъра + update-ва
        last_z_report."""
        self.ensure_one()
        if self.connection_mode == "proxy":
            return self._proxy_or_direct_action(
                endpoint=f"printers/{self.printer_id}/zreport",
                success_title=_("Success"),
                success_msg=_("The Z report has been generated successfully"),
                on_success="_mark_last_z_report",
                timeout_ms=OP_TIMEOUT_REPORT_MS,
            )
        # timeout=90s: Datecs ISL Z-report върви 60-90s — device
        # default-ът 30s ще timeout-не докато принтерът още печата.
        result = self._make_request(
            "POST", f"printers/{self.printer_id}/zreport",
            timeout=OP_TIMEOUT_REPORT_MS / 1000)
        self._mark_last_z_report()
        return result

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

    # ========== МЕТОДИ ЗА СТОРНО И ОБРАТНИ БОНОВЕ ==========

    def print_reversal_receipt(self, reversal_data):
        """
        Печат на сторно бон
        :param reversal_data: dict с данни за сторно бона
        """
        if not isinstance(reversal_data, dict):
            raise ValidationError(_('Reversal data must be a dictionary'))

        return self._make_request('POST', f'printers/{self.printer_id}/reversalreceipt', reversal_data)
