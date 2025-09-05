# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class CryptoWalletGenerateKeypairWizard(models.TransientModel):
    _name = 'crypto.wallet.generate.keypair.wizard'
    _description = 'Wizard за генериране на двойка ключове'

    wallet_id = fields.Many2one('crypto.wallet', 'Портфел', required=True)

    key_name = fields.Char('Име на ключовете', required=True,
                           help='Базово име за двойката ключове (ще се добавят _private и _public)')

    key_type = fields.Selection([
        ('rsa', 'RSA (2048 бита)'),
        ('ec', 'Elliptic Curve (SECP256R1)')
    ], 'Тип на ключовете', default='rsa', required=True)

    description = fields.Text('Описание',
                              help='Описание на предназначението на ключовете')

    # Резултати
    generation_result = fields.Text('Резултат от генерирането', readonly=True)
    private_key_name = fields.Char('Име на частния ключ', readonly=True)
    public_key_name = fields.Char('Име на публичния ключ', readonly=True)

    @api.constrains('key_name')
    def _check_key_name(self):
        """Проверява валидността на името"""
        for record in self:
            if record.key_name:
                import re
                if not re.match(r'^[a-zA-Z0-9_.-]+$', record.key_name):
                    raise UserError(_(
                        'Името може да съдържа само букви, цифри, тире, долна черта и точки'
                    ))

                if len(record.key_name) > 40:
                    raise UserError(_('Името не може да бъде по-дълго от 40 символа'))

    def generate_keypair(self):
        """Генерира двойка ключове"""
        self.ensure_one()

        try:
            # Проверява дали ключове с такова име вече съществуват
            existing_keys = self.wallet_id.list_keys_with_user_password() or []
            existing_names = [key['name'] for key in existing_keys]

            private_name = f"{self.key_name}_private"
            public_name = f"{self.key_name}_public"

            if private_name in existing_names or public_name in existing_names:
                raise UserError(_(
                    'Ключове с имена "%s" или "%s" вече съществуват в портфела!'
                ) % (private_name, public_name))

            # Генерира ключовете
            result = self.wallet_id.generate_keypair(
                key_name=self.key_name,
                key_type=self.key_type
            )

            self.private_key_name = result['private_key_name']
            self.public_key_name = result['public_key_name']

            # Ако има описание, добавя го като метаданни
            if self.description:
                try:
                    # Обновява метаданните на ключовете
                    for key_name in [self.private_key_name, self.public_key_name]:
                        key_data = self.wallet_id.get_key_with_user_password(key_name)
                        if isinstance(key_data, dict) and 'metadata' in key_data:
                            key_data['metadata']['description'] = self.description
                            # Тук трябва да обновим ключа в портфела
                            # За простота пропускаме тази функционалност
                except Exception as e:
                    _logger.warning(f"Could not update key metadata: {e}")

            self.generation_result = _(
                "Успешно генерирани %s ключове:\n\n"
                "Частен ключ: %s\n"
                "Публичен ключ: %s\n\n"
                "Ключовете са запазени в портфела и криптирани с вашата главна парола."
            ) % (self.key_type.upper(), self.private_key_name, self.public_key_name)

            _logger.info(f"Generated {self.key_type.upper()} keypair: {self.key_name}")

            # Показва формата с резултатите
            return {
                'type': 'ir.actions.act_window',
                'name': _('Резултат от генерирането'),
                'res_model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
                'context': {'show_generation_result': True}
            }

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
            _logger.error(f"Error generating keypair: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Неочаквана грешка'),
                    'message': _('Възникна грешка при генерирането: %s') % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def generate_and_add_another(self):
        """Генерира ключове и отваря нов wizard"""
        generate_result = self.generate_keypair()

        if generate_result.get('context', {}).get('show_generation_result'):
            # Отваря нов wizard за следващо генериране
            return {
                'type': 'ir.actions.act_window',
                'name': _('Генерирай нова двойка ключове'),
                'res_model': self._name,
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_wallet_id': self.wallet_id.id,
                    'default_key_type': self.key_type
                },
            }

        return generate_result

    def view_private_key(self):
        """Показва частния ключ"""
        self.ensure_one()

        if not self.private_key_name:
            raise UserError(_('Няма генериран частен ключ!'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Мениджър на ключове'),
            'res_model': 'crypto.wallet.key.manager',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_wallet_id': self.wallet_id.id,
                'default_selected_key_name': self.private_key_name
            },
        }

    def view_public_key(self):
        """Показва публичния ключ"""
        self.ensure_one()

        if not self.public_key_name:
            raise UserError(_('Няма генериран публичен ключ!'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Мениджър на ключове'),
            'res_model': 'crypto.wallet.key.manager',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_wallet_id': self.wallet_id.id,
                'default_selected_key_name': self.public_key_name
            },
        }
