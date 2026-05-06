# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json
import base64
import logging

_logger = logging.getLogger(__name__)


class CryptoWalletExportWizard(models.TransientModel):
    _name = 'crypto.wallet.export.wizard'
    _description = 'Wizard за експортиране на криптиран портфел'

    wallet_id = fields.Many2one('crypto.wallet', 'Портфел')

    master_password = fields.Char('Главна парола',
                                  help='Enter the master password to unlock the wallet')

    export_format = fields.Selection([
        ('json', 'JSON (незащитен)'),
        ('encrypted', 'Криптиран експорт')
    ], 'Формат на експорта', default='encrypted', required=True)

    export_password = fields.Char('Парола за експорта',
                                  help='Password to encrypt the export (only for encrypted format)')
    confirm_export_password = fields.Char('Потвърди паролата',
                                          help='Confirm the export password')

    include_metadata = fields.Boolean('Включи метаданни', default=True,
                                      help='Includes creation date, user, etc.')

    use_user_password = fields.Boolean('Използвай паролата на потребителя', default=True,
                                       help='Use current user password')

    # Резултати от експорта
    export_data = fields.Text('Експортирани данни', readonly=True)
    export_filename = fields.Char('Име на файла', readonly=True)

    @api.onchange('use_user_password')
    def _onchange_use_user_password(self):
        """Автоматично попълва паролата на потребителя"""
        if self.use_user_password:
            try:
                self.master_password = self.env.user.password
            except Exception:
                pass

    @api.onchange('export_format')
    def _onchange_export_format(self):
        """Задава изискания за парола при криптиран експорт"""
        if self.export_format == 'encrypted':
            if not self.export_password:
                self.export_password = ''

    @api.constrains('export_password', 'confirm_export_password')
    def _check_export_passwords_match(self):
        """Проверява дали паролите за експорт съвпадат"""
        for record in self:
            if record.export_format == 'encrypted':
                if record.export_password != record.confirm_export_password:
                    raise UserError(_('Паролата за експорта и потвърждението не съвпадат!'))
                if not record.export_password:
                    raise UserError(_('Паролата за експорта е задължителна при криптиран формат!'))

    def export_wallet(self):
        """Експортира портфела"""
        self.ensure_one()

        try:
            # Валидация на пароли при криптиран експорт
            if self.export_format == 'encrypted':
                if self.export_password != self.confirm_export_password:
                    raise UserError(_('Паролите за експорта не съвпадат!'))
                if not self.export_password:
                    raise UserError(_('Паролата за експорта е задължителна!'))

            # Експортира портфела
            export_password = self.export_password if self.export_format == 'encrypted' else None

            export_result = self.wallet_id.export_wallet(
                master_password=self.master_password,
                export_password=export_password
            )

            # Подготвя данните за показване
            if self.export_format == 'json':
                self.export_data = json.dumps(export_result['data'], indent=2, ensure_ascii=False)
                self.export_filename = f"{self.wallet_id.name}_export.json"
            else:
                self.export_data = json.dumps(export_result, indent=2)
                self.export_filename = f"{self.wallet_id.name}_export_encrypted.json"

            _logger.info(f"Wallet '{self.wallet_id.name}' exported successfully")

            # Показва формата с резултатите
            return {
                'type': 'ir.actions.act_window',
                'name': _('Резултат от експорта'),
                'res_model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
                'context': {'show_export_result': True}
            }

        except UserError as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Грешка при експорта'),
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }
        except Exception as e:
            _logger.error(f"Error exporting wallet: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Неочаквана грешка'),
                    'message': _('Възникна грешка при експорта: %s') % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def download_export(self):
        """Създава файл за изтегляне"""
        self.ensure_one()

        if not self.export_data:
            raise UserError(_('Няма данни за експорт!'))

        # Създава attachment за изтегляне
        attachment = self.env['ir.attachment'].create({
            'name': self.export_filename,
            'type': 'binary',
            'datas': base64.b64encode(self.export_data.encode('utf-8')),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/json',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def copy_to_clipboard(self):
        """Копира данните в clipboard (чрез JavaScript)"""
        self.ensure_one()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Копиране'),
                'message': _('Данните са готови за копиране. Моля, селектирайте и копирайте текста по-долу.'),
                'type': 'info',
                'sticky': True,
            }
        }
