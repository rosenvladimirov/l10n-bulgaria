# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class CryptoWalletChangePasswordWizard(models.TransientModel):
    _name = 'crypto.wallet.change.password.wizard'
    _description = 'Wizard за промяна на главната парола на портфела'

    wallet_id = fields.Many2one('crypto.wallet', 'Портфел')

    old_password = fields.Char('Стара парола',
                               help='Въведете текущата главна парола')
    new_password = fields.Char('Нова парола',
                               help='Въведете новата главна парола')
    confirm_password = fields.Char('Потвърди новата парола',
                                   help='Въведете отново новата парола за потвърждение')

    use_current_user_password = fields.Boolean('Използвай паролата на потребителя като стара',
                                               default=True,
                                               help='Използва паролата на текущия потребител като стара парола')
    update_user_password = fields.Boolean('Обнови паролата на потребителя', default=False,
                                          help='Обновява и паролата на потребителя в системата')

    @api.onchange('use_current_user_password')
    def _onchange_use_current_user_password(self):
        """Автоматично попълва старата парола"""
        if self.use_current_user_password:
            try:
                self.old_password = self.env.user.password
            except Exception:
                pass

    @api.constrains('new_password', 'confirm_password')
    def _check_password_match(self):
        """Проверява дали новите пароли съвпадат"""
        for record in self:
            if record.new_password and record.confirm_password:
                if record.new_password != record.confirm_password:
                    raise ValidationError(_('Новата парола и потвърждението не съвпадат!'))

    @api.constrains('new_password')
    def _check_password_strength(self):
        """Проверява силата на новата парола"""
        for record in self:
            if record.new_password:
                if len(record.new_password) < 8:
                    raise ValidationError(_('Новата парола трябва да съдържа поне 8 символа!'))

    def change_password(self):
        """Променя главната парола на портфела"""
        self.ensure_one()

        try:
            # Проверява дали новите пароли съвпадат
            if self.new_password != self.confirm_password:
                raise UserError(_('Новата парола и потвърждението не съвпадат!'))

            # Променя главната парола
            success = self.wallet_id.change_master_password(
                old_password=self.old_password,
                new_password=self.new_password
            )

            if success:
                # Ако е избрано, обновява и паролата на потребителя
                if self.update_user_password:
                    self.env.user.password = self.new_password

                _logger.info(f"Password changed for wallet {self.wallet_id.name} by user {self.env.user.name}")

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Успех'),
                        'message': _('Главната парола на портфел "%s" е променена успешно!') % self.wallet_id.name,
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                raise UserError(_('Неуспешна промяна на паролата'))

        except UserError as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Грешка'),
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }
        except Exception as e:
            _logger.error(f"Error changing wallet password: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Неочаквана грешка'),
                    'message': _('Възникна грешка при промяната на паролата: %s') % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def change_password_and_unlock(self):
        """Променя паролата и отключва портфела"""
        change_result = self.change_password()

        if change_result.get('params', {}).get('type') == 'success':
            # Ако промяната е успешна, отключва с новата парола
            try:
                self.wallet_id.unlock_wallet_with_password(self.new_password)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Успех'),
                        'message': _('Паролата е променена и портфелът е отключен успешно!'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            except Exception as e:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Частичен успех'),
                        'message': _('Паролата е променена, но възникна грешка при отключването: %s') % str(e),
                        'type': 'warning',
                        'sticky': True,
                    }
                }

        return change_result
