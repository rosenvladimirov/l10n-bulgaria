# wizard/fiscal_cash_operation_wizard.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class FiscalCashOperationWizard(models.TransientModel):
    _name = 'fiscal.cash.operation.wizard'
    _description = 'Служебни касови операции'

    session_id = fields.Many2one('pos.session', string='POS Сесия', required=True)
    operation_type = fields.Selection([
        ('withdraw', 'Служебно изведени'),
        ('deposit', 'Служебно въведени')
    ], string='Тип операция', required=True)
    amount = fields.Float('Сума', required=True)
    reason = fields.Char('Причина')

    def action_execute(self):
        """Изпълнява служебната операция"""
        self.ensure_one()

        if self.amount <= 0:
            raise UserError(_('Сумата трябва да е положително число'))

        printer = self.session_id.l10n_bg_fiscal_printer_id
        if not printer:
            raise UserError(_('Няма конфигуриран фискален принтер'))

        try:
            if self.operation_type == 'withdraw':
                printer.print_withdraw(self.amount)
                message = _('Служебно изведени: %.2f') % self.amount
            else:
                printer.print_deposit(self.amount)
                message = _('Служебно въведени: %.2f') % self.amount

            # Добавяме запис в сесията
            self.session_id.message_post(
                body=f"{message}\nПричина: {self.reason or 'Не е посочена'}",
                message_type='notification'
            )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Успех'),
                    'message': message,
                    'type': 'success',
                }
            }
        except Exception as e:
            raise UserError(_('Грешка при изпълнение на операцията: %s') % str(e))
