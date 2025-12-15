from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PosSession(models.Model):
    _inherit = "pos.session"

    l10n_bg_fiscal_printer_id = fields.Many2one(
        'fiscal.printer.device',
        string='Fiscal printer',
        related='config_id.l10n_bg_fiscal_printer_id',
        store=True,
        readonly=True
    )
    l10n_bg_last_x_report = fields.Datetime(
        'Last X report',
        readonly=True
    )
    l10n_bg_z_report_printed = fields.Boolean(
        'Z report printed',
        readonly=True,
        default=False
    )
    l10n_bg_z_report_datetime = fields.Datetime(
        'Z Report Date/Time',
        readonly=True
    )
    l10n_bg_erp_net_fp_ip = fields.Char(
        'ErpNet.FP IP',
        compute='_compute_l10n_bg_erp_net_fp_ip',
        store=True
    )
    l10n_bg_erp_net_fp_host = fields.Char(
        'ErpNet.FP Host',
        compute='_compute_l10n_bg_erp_net_fp_host',
        store=True
    )

    @api.depends('l10n_bg_fiscal_printer_id', 'l10n_bg_fiscal_printer_id.printer_id')
    def _compute_l10n_bg_erp_net_fp_ip(self):
        for config in self:
            config.l10n_bg_erp_net_fp_ip = config.l10n_bg_fiscal_printer_id.printer_id

    @api.depends('l10n_bg_fiscal_printer_id', 'l10n_bg_fiscal_printer_id.host')
    def _compute_l10n_bg_erp_net_fp_host(self):
        for config in self:
            config.l10n_bg_erp_net_fp_host = config.l10n_bg_fiscal_printer_id.host

    @api.model
    def _load_pos_data_fields(self, config_id):
        """Зареждане на необходимите полета за фискален принтер"""
        res = super()._load_pos_data_fields(config_id)

        # Добавяме полета за сесията
        fiscal_fields = [
            'l10n_bg_erp_net_fp_host',
            'l10n_bg_erp_net_fp_ip',
            'l10n_bg_last_x_report',
            'l10n_bg_z_report_printed',
            'l10n_bg_z_report_datetime',
        ]

        res.extend(fiscal_fields)
        return res

    # ========== X ОТЧЕТ ==========

    def action_print_x_report(self):
        """Отпечатване на X отчет от сесията"""
        self.ensure_one()

        if not self.l10n_bg_fiscal_printer_id:
            raise UserError(_('There is no fiscal printer configured for this POS session'))

        if self.state != 'opened':
            raise UserError(_('An X report can only be printed with an open session'))

        # Проверка дали принтерът е достъпен
        printer_check = self.l10n_bg_fiscal_printer_id.check_printer_available()

        if not printer_check['available']:
            error_msg = printer_check.get('error', _('Принтерът не е достъпен'))
            mode = printer_check.get('mode', 'unknown')

            help_text = ''
            if mode == 'proxy':
                help_text = _(
                    '\n\nМоля, уверете се че:\n'
                    '• Браузърът с ErpNet прокси е отворен\n'
                    '• Принтерът е свързан и включен\n'
                    '• Прокси приложението има достъп до принтера'
                )
            elif mode == 'direct':
                help_text = _(
                    '\n\nМоля, проверете:\n'
                    '• ErpNet.FP сървърът е стартиран\n'
                    '• Принтерът е достъпен от сървъра'
                )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Принтерът не е достъпен'),
                    'message': error_msg + help_text,
                    'type': 'danger',
                    'sticky': True,
                }
            }

        try:
            result = self.l10n_bg_fiscal_printer_id.print_x_report()
            self.l10n_bg_last_x_report = fields.Datetime.now()

            self.message_post(
                body=_('X отчет отпечатан успешно'),
                message_type='notification'
            )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Успех'),
                    'message': _('X отчетът е отпечатан успешно'),
                    'type': 'success',
                }
            }
        except Exception as e:
            error_msg = str(e)
            if 'Timeout waiting for browser' in error_msg:
                error_msg = _(
                    'Няма връзка с фискалния принтер.\n\n'
                    'Моля, отворете браузъра с ErpNet прокси приложението.'
                )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Грешка'),
                    'message': error_msg,
                    'type': 'danger',
                    'sticky': True,
                }
            }

    # ========== Z ОТЧЕТ ==========

    def action_print_z_report(self):
        """Отпечатване на Z отчет при затваряне на сесията"""
        self.ensure_one()

        if not self.l10n_bg_fiscal_printer_id:
            raise UserError(_('Няма конфигуриран фискален принтер за тази POS сесия'))

        if self.l10n_bg_z_report_printed:
            raise UserError(_('Z отчет вече е отпечатан за тази сесия'))

        # Проверка дали принтерът е достъпен
        printer_check = self.l10n_bg_fiscal_printer_id.check_printer_available()

        if not printer_check['available']:
            error_msg = printer_check.get('error', _('Принтерът не е достъпен'))
            mode = printer_check.get('mode', 'unknown')

            help_text = ''
            if mode == 'proxy':
                help_text = _(
                    '\n\nМоля, уверете се че:\n'
                    '• Браузърът с ErpNet прокси е отворен\n'
                    '• Принтерът е свързан и включен\n'
                    '• Прокси приложението има достъп до принтера'
                )
            elif mode == 'direct':
                help_text = _(
                    '\n\nМоля, проверете:\n'
                    '• ErpNet.FP сървърът е стартиран\n'
                    '• Принтерът е достъпен от сървъра'
                )

            raise UserError(error_msg + help_text)

        try:
            result = self.l10n_bg_fiscal_printer_id.print_z_report()

            self.write({
                'l10n_bg_z_report_printed': True,
                'l10n_bg_z_report_datetime': fields.Datetime.now()
            })

            self.message_post(
                body=_('Z отчет отпечатан успешно'),
                message_type='notification'
            )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Успех'),
                    'message': _('Z отчетът е отпечатан успешно. Сесията може да бъде затворена.'),
                    'type': 'success',
                }
            }
        except Exception as e:
            error_msg = str(e)
            if 'Timeout waiting for browser' in error_msg:
                error_msg = _(
                    'Няма връзка с фискалния принтер.\n\n'
                    'Моля, отворете браузъра с ErpNet прокси приложението.'
                )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Грешка'),
                    'message': error_msg,
                    'type': 'danger',
                    'sticky': True,
                }
            }

    # ========== СЛУЖЕБНИ ОПЕРАЦИИ ==========

    def action_fiscal_withdraw(self):
        """Отваря wizard за служебно изведени"""
        self.ensure_one()
        return {
            'name': _('Officially removed'),
            'type': 'ir.actions.act_window',
            'res_model': 'fiscal.cash.operation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_session_id': self.id,
                'default_operation_type': 'withdraw'
            }
        }

    def action_fiscal_deposit(self):
        """Отваря wizard за служебно въведени"""
        self.ensure_one()
        return {
            'name': _('Officially introduced'),
            'type': 'ir.actions.act_window',
            'res_model': 'fiscal.cash.operation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_session_id': self.id,
                'default_operation_type': 'deposit'
            }
        }

    def action_check_printer(self):
        """Проверка на връзката с фискалния принтер"""
        self.ensure_one()

        if not self.l10n_bg_fiscal_printer_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Attention'),
                    'message': _('There is no fiscal printer configured'),
                    'type': 'warning',
                }
            }

        return self.l10n_bg_fiscal_printer_id.action_check_connection()
