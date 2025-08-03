# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class CryptoWalletAddKeyWizard(models.TransientModel):
    _name = 'crypto.wallet.add.key.wizard'
    _description = 'Wizard за добавяне на ключ в криптиран портфел'

    key_name = fields.Char('Име на ключа', required=True,
                          help='Уникално име за идентификация на ключа')
    key_type = fields.Selection([
        ('rsa_private', 'RSA Частен ключ'),
        ('rsa_public', 'RSA Публичен ключ'),
        ('api_key', 'API ключ'),
        ('password', 'Парола'),
        ('certificate', 'Сертификат'),
        ('token', 'Токен'),
        ('ssh_key', 'SSH ключ'),
        ('pgp_key', 'PGP ключ'),
        ('other', 'Друго')
    ], 'Тип на ключа', required=True, default='api_key')

    key_data = fields.Text('Данни на ключа', required=True,
                          help='Съдържанието на ключа (ще бъде криптирано)')

    description = fields.Text('Описание',
                             help='Допълнителна информация за ключа')

    @api.model
    def default_get(self, fields_list):
        """Задава defaults при отворяне на wizard-a"""
        res = super().default_get(fields_list)

        # Можем да предложим следващо име на ключ
        existing_keys = self._get_existing_keys()
        suggested_name = self._suggest_key_name(existing_keys)
        if suggested_name:
            res['key_name'] = suggested_name

        return res

    def _get_existing_keys(self):
        """Взема списък със съществуващите ключове"""
        try:
            wallet = self.env['crypto.wallet'].get_user_wallet()
            return wallet.list_keys_with_user_password() or {}
        except Exception as e:
            _logger.warning(f"Could not load existing keys: {e}")
            return {}

    def _suggest_key_name(self, existing_keys):
        """Предлага име за нов ключ"""
        base_name = "new_key"
        counter = 1

        while f"{base_name}_{counter}" in existing_keys:
            counter += 1

        return f"{base_name}_{counter}"

    @api.constrains('key_name')
    def _check_key_name(self):
        """Проверява валидността на името на ключа"""
        for record in self:
            if not record.key_name:
                continue

            # Проверява за валидни символи
            import re
            if not re.match(r'^[a-zA-Z0-9_.-]+$', record.key_name):
                raise UserError(_(
                    'Името на ключа може да съдържа само букви, цифри, тире, долна черта и точки'
                ))

            # Проверява дължината
            if len(record.key_name) > 50:
                raise UserError(_('Името на ключа не може да бъде по-дълго от 50 символа'))

    @api.constrains('key_data')
    def _check_key_data(self):
        """Проверява размера на данните"""
        for record in self:
            if record.key_data and len(record.key_data.encode('utf-8')) > 65536:  # 64KB
                raise UserError(_('Данните на ключа не могат да надвишават 64KB'))

    def add_key_to_wallet(self):
        """Добавя ключа в портфела на потребителя"""
        self.ensure_one()

        try:
            # Взема или създава портфела на потребителя
            wallet = self.env['crypto.wallet'].get_user_wallet()
            _logger.info(f"Adding key '{self.key_name}' to wallet for user {self.env.user.id}")

            # Проверява дали ключът вече съществува
            existing_keys = wallet.list_keys_with_user_password() or {}
            if self.key_name in existing_keys:
                raise UserError(_('Ключ с име "%s" вече съществува в портфела') % self.key_name)

            # Подготвя данните за съхранение
            key_data_with_meta = {
                'data': self.key_data,
                'description': self.description or '',
                'created': fields.Datetime.now().isoformat(),
                'created_by': self.env.user.name
            }

            # Добавя ключа използвайки паролата на потребителя като master password
            success = wallet.add_key_with_user_password(
                key_name=self.key_name,
                key_type=self.key_type,
                key_data=key_data_with_meta
            )

            if success:
                _logger.info(f"Successfully added key '{self.key_name}' to wallet")

                # Показва success notification
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Успех'),
                        'message': _('Ключът "%s" (тип: %s) е добавен успешно в портфела') % (
                            self.key_name,
                            dict(self._fields['key_type'].selection).get(self.key_type, self.key_type)
                        ),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                raise UserError(_('Неуспешно добавяне на ключа в портфела'))

        except UserError:
            # Препредава UserError-и директно
            raise
        except Exception as e:
            _logger.error(f"Error adding key to wallet: {e}")
            raise UserError(_('Грешка при добавяне на ключ: %s') % str(e))

    def add_key_and_add_another(self):
        """Добавя ключа и отваря нов wizard за следващ ключ"""
        # Първо добавя текущия ключ
        result = self.add_key_to_wallet()

        if result and result.get('params', {}).get('type') == 'success':
            # Отваря нов wizard
            return {
                'type': 'ir.actions.act_window',
                'name': _('Добави нов ключ'),
                'res_model': 'crypto.wallet.add.key.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_key_type': self.key_type}  # Запазва типа
            }

        return result

    def preview_key_info(self):
        """Показва preview на информацията за ключа"""
        info = {
            'name': self.key_name,
            'type': dict(self._fields['key_type'].selection).get(self.key_type, self.key_type),
            'size': f"{len(self.key_data.encode('utf-8'))} bytes" if self.key_data else "0 bytes",
            'description': self.description or _('Няма описание')
        }

        message = _("""
        <strong>Преглед на ключа:</strong><br/>
        <strong>Име:</strong> %(name)s<br/>
        <strong>Тип:</strong> %(type)s<br/>
        <strong>Размер:</strong> %(size)s<br/>
        <strong>Описание:</strong> %(description)s
        """) % info

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Информация за ключа'),
                'message': message,
                'type': 'info',
                'sticky': True,
            }
        }
