# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class CryptoWalletUnlockWizard(models.TransientModel):
    _name = 'crypto.wallet.unlock.wizard'
    _description = 'Wizard за отключване на криптиран портфел'

    wallet_id = fields.Many2one('crypto.wallet', 'Портфел', required=True)
    master_password = fields.Char('Главна парола', required=True, password=True,
                                  help='Въведете главната парола за отключване на портфела')

    use_user_password = fields.Boolean('Използвай паролата на потребителя', default=True,
                                       help='Използва паролата на текущия потребител като главна парола')

    @api.onchange('use_user_password')
    def _onchange_use_user_password(self):
        """Автоматично попълва паролата на потребителя"""
        if self.use_user_password:
            try:
                self.master_password = self.env.user.password
            except:
                pass  # Ако не може да достъпи паролата, остава празно

    def unlock_wallet(self):
        """Отключва портфела"""
        self.ensure_one()

        try:
            # Отключва портфела с предоставената парола
            wallet_data = self.wallet_id.unlock_wallet_with_password(self.master_password)

            keys_count = len(wallet_data.get('keys', {}))

            # Показва success notification
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Успех'),
                    'message': _('Портфелът "%s" е отключен успешно!\nНамерени са %d ключа.') % (
                        self.wallet_id.name, keys_count
                    ),
                    'type': 'success',
                    'sticky': False,
                }
            }

        except UserError as e:
            # Показва грешка в notification
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Грешка при отключване'),
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }
        except Exception as e:
            _logger.error(f"Error unlocking wallet: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Неочаквана грешка'),
                    'message': _('Възникна неочаквана грешка при отключването: %s') % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def unlock_and_show_keys(self):
        """Отключва портфела и показва списък с ключовете"""
        unlock_result = self.unlock_wallet()

        if unlock_result.get('params', {}).get('type') == 'success':
            # Ако отключването е успешно, показва ключовете
            return self.wallet_id.action_list_keys()

        return unlock_result
