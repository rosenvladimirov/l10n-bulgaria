# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class CryptoWalletKeyManager(models.TransientModel):
    _name = 'crypto.wallet.key.manager'
    _description = 'Мениджър за ключове в криптиран портфел'

    wallet_id = fields.Many2one('crypto.wallet', 'Портфел', required=True)

    # Състояние на портфела
    is_wallet_locked = fields.Boolean('Портфелът е заключен', compute='_compute_wallet_state')
    keys_count = fields.Integer('Брой ключове', compute='_compute_wallet_state')

    # Списък с ключове
    key_list = fields.Text('Списък с ключове', compute='_compute_key_list')

    # За показване на конкретен ключ
    selected_key_name = fields.Char('Избран ключ')
    selected_key_data = fields.Text('Данни на ключа', readonly=True)
    selected_key_type = fields.Char('Тип на ключа', readonly=True)
    selected_key_created = fields.Char('Дата на създаване', readonly=True)

    @api.depends('wallet_id')
    def _compute_wallet_state(self):
        """Изчислява състоянието на портфела"""
        for record in self:
            if record.wallet_id:
                record.is_wallet_locked = record.wallet_id.is_locked
                try:
                    keys_info = record.wallet_id.list_keys_with_user_password()
                    record.keys_count = len(keys_info) if keys_info else 0
                except Exception:
                    record.keys_count = 0
            else:
                record.is_wallet_locked = True
                record.keys_count = 0

    @api.depends('wallet_id')
    def _compute_key_list(self):
        """Изчислява списъка с ключове"""
        for record in self:
            if record.wallet_id:
                try:
                    keys_info = record.wallet_id.list_keys_with_user_password()
                    if keys_info:
                        key_lines = []
                        for i, key_info in enumerate(keys_info, 1):
                            key_lines.append(f"{i}. {key_info['name']} ({key_info['type']}) - {key_info['created']}")
                        record.key_list = '\n'.join(key_lines)
                    else:
                        record.key_list = _('Няма съхранени ключове в този портфел.')
                except Exception as e:
                    record.key_list = _('Грешка при зареждане на ключовете: %s') % str(e)
            else:
                record.key_list = ''

    def unlock_wallet(self):
        """Отваря wizard за отключване на портфела"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Отключи портфела'),
            'res_model': 'crypto.wallet.unlock.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_wallet_id': self.wallet_id.id},
        }

    def add_key(self):
        """Отваря wizard за добавяне на ключ"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Добави нов ключ'),
            'res_model': 'crypto.wallet.add.key.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_wallet_id': self.wallet_id.id},
        }

    def view_key(self):
        """Показва данните на избрания ключ"""
        self.ensure_one()

        if not self.selected_key_name:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Грешка'),
                    'message': _('Моля, въведете името на ключа.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        try:
            key_data = self.wallet_id.get_key_with_user_password(self.selected_key_name)

            self.selected_key_data = str(key_data.get('data', ''))
            self.selected_key_type = key_data.get('type', '')
            self.selected_key_created = key_data.get('created', '')

            return {
                'type': 'ir.actions.act_window',
                'name': _('Данни на ключа'),
                'res_model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
                'context': {'show_key_data': True}
            }

        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Грешка'),
                    'message': _('Не може да се зареди ключът: %s') % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def remove_key(self):
        """Премахва избрания ключ"""
        self.ensure_one()

        if not self.selected_key_name:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Грешка'),
                    'message': _('Моля, въведете името на ключа.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        try:
            success = self.wallet_id.remove_key_with_user_password(self.selected_key_name)

            if success:
                # Обновява списъка с ключове
                self._compute_key_list()
                self._compute_wallet_state()

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Успех'),
                        'message': _('Ключът "%s" е премахнат успешно.') % self.selected_key_name,
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                raise UserError(_('Неуспешно премахване на ключа'))

        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Грешка'),
                    'message': _('Не може да се премахне ключът: %s') % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def generate_keypair(self):
        """Отваря wizard за генериране на двойка ключове"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Генерирай двойка ключове'),
            'res_model': 'crypto.wallet.generate.keypair.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_wallet_id': self.wallet_id.id},
        }

    def refresh_keys(self):
        """Обновява списъка с ключове"""
        self.ensure_one()
        self._compute_key_list()
        self._compute_wallet_state()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Мениджър на ключове'),
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def export_key(self):
        """Експортира конкретен ключ"""
        self.ensure_one()

        if not self.selected_key_name:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Грешка'),
                    'message': _('Моля, въведете името на ключа.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        return {
            'type': 'ir.actions.act_window',
            'name': _('Експортиране на ключ'),
            'res_model': 'crypto.wallet.export.key.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_wallet_id': self.wallet_id.id,
                'default_key_name': self.selected_key_name
            },
        }
