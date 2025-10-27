from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PosSession(models.Model):
    _inherit = "pos.session"

    l10n_bg_fiscal_printer_id = fields.Many2one(
        'fiscal.printer.device',
        string='Фискален принтер',
        related='config_id.l10n_bg_fiscal_printer_id',
        store=True,
        readonly=True
    )
    l10n_bg_last_x_report = fields.Datetime('Последен X отчет', readonly=True)
    l10n_bg_z_report_printed = fields.Boolean('Z отчет отпечатан', readonly=True, default=False)
    l10n_bg_z_report_datetime = fields.Datetime('Дата/Час на Z отчет', readonly=True)

    @api.model
    def _load_pos_data_fields(self, config_id):
        """Зареждане на необходимите полета за фискален принтер"""
        fields = super()._load_pos_data_fields(config_id)

        # Добавяме полета за сесията
        fields.extend([
            'l10n_bg_fiscal_printer_id',
            'l10n_bg_last_x_report',
            'l10n_bg_z_report_printed',
            'l10n_bg_z_report_datetime',
        ])

        return fields

    # ========== X ОТЧЕТ ==========

    def action_print_x_report(self):
        """Отпечатване на X отчет от сесията"""
        self.ensure_one()

        if not self.l10n_bg_fiscal_printer_id:
            raise UserError(_('Няма конфигуриран фискален принтер за тази POS сесия'))

        if self.state != 'opened':
            raise UserError(_('X отчет може да се отпечата само при отворена сесия'))

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
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Грешка'),
                    'message': str(e),
                    'type': 'danger',
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
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Грешка'),
                    'message': str(e),
                    'type': 'danger',
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

    # ========== ВАЛИДАЦИЯ ПРИ ЗАТВАРЯНЕ ==========

    def action_pos_session_closing_control(self, balancing_account=False, amount_to_balance=0,
                                           bank_payment_method_diffs=None):
        """Разширение за автоматичен Z отчет при затваряне"""
        # Проверка дали трябва да се отпечата Z отчет
        if self.config_id.l10n_bg_auto_z_on_close and self.l10n_bg_fiscal_printer_id:
            if not self.l10n_bg_z_report_printed:
                try:
                    self.action_print_z_report()
                except Exception as e:
                    raise UserError(
                        _('Грешка при печат на Z отчет: %s\n'
                          'Моля, отпечатайте Z отчета ръчно преди затваряне.') % str(e)
                    )

        return super().action_pos_session_closing_control(balancing_account, amount_to_balance,
                                                          bank_payment_method_diffs)
