# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

"""Wizard за импорт на криптиран ZIP файл с ключове в портфейла.

Операторът качва AES-256 ZIP (експортиран от друга инстанция или
back-up на собствения портфейл), въвежда паролата на архива и
паролата на портфейла, и wizard-ът извиква
``crypto.wallet.import_keys_from_zip_bytes`` за да слее ключовете в
текущия портфейл."""

import base64
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CryptoWalletImportWizard(models.TransientModel):
    _name = 'crypto.wallet.import.wizard'
    _description = 'Wizard за импорт на ключове от ZIP в портфейла'

    wallet_id = fields.Many2one(
        'crypto.wallet', string='Wallet',
        required=True,
    )
    zip_file = fields.Binary(
        string='ZIP file',
        required=True,
        help='AES-256 password-protected ZIP exported from another '
             'crypto.wallet (or a backup of this one).',
    )
    zip_filename = fields.Char(string='Filename')
    zip_password = fields.Char(
        string='ZIP password',
        required=True,
        help='Password used when the ZIP was created.',
    )
    master_password = fields.Char(
        string='Master password',
        help='Master password for the destination wallet.  Leave '
             'blank to use the current user password.',
    )
    use_user_password = fields.Boolean(
        string='Use current user password',
        default=True,
        help='Take the master password from the logged-in user '
             'instead of asking explicitly.',
    )
    overwrite = fields.Boolean(
        string='Overwrite existing keys',
        default=False,
        help='If a key with the same name already exists, replace '
             'it.  Default: skip duplicates (safer).',
    )

    # Резултати от import — readonly, попълват се след action_import
    result_imported = fields.Integer(string='Imported', readonly=True)
    result_skipped = fields.Integer(string='Skipped', readonly=True)
    result_overwritten = fields.Integer(
        string='Overwritten', readonly=True,
    )
    result_summary = fields.Text(string='Summary', readonly=True)

    @api.onchange('use_user_password')
    def _onchange_use_user_password(self):
        # Изчистваме master_password ако ще ползваме user password
        if self.use_user_password:
            self.master_password = False

    def action_import(self):
        # Главен entry point: validate + call wallet import API
        self.ensure_one()
        if not self.wallet_id:
            raise UserError(_('Wallet is required.'))
        if not self.zip_file:
            raise UserError(_('Please upload a ZIP file.'))
        if not self.zip_password:
            raise UserError(_('ZIP password is required.'))

        # Decode binary upload (Odoo дава base64 за binary fields)
        try:
            zip_bytes = base64.b64decode(self.zip_file)
        except Exception as exc:
            raise UserError(_('Cannot decode the uploaded file.')) from exc

        # Master password fallback към user-а
        master_pwd = (
            None if self.use_user_password else self.master_password
        )

        # Извикваме wallet API — exceptions се пропускат към UI
        result = self.wallet_id.import_keys_from_zip_bytes(
            zip_bytes=zip_bytes,
            zip_password=self.zip_password,
            master_password=master_pwd,
            overwrite=self.overwrite,
        )

        # Попълваме readonly резултатите за да се покажат на оператора
        self.result_imported = result.get('imported', 0)
        self.result_skipped = result.get('skipped', 0)
        self.result_overwritten = result.get('overwritten', 0)
        lines = []
        if result.get('keys_imported'):
            lines.append(
                'Imported: ' + ', '.join(result['keys_imported']),
            )
        if result.get('keys_overwritten'):
            lines.append(
                'Overwritten: ' + ', '.join(result['keys_overwritten']),
            )
        if result.get('keys_skipped'):
            lines.append(
                'Skipped (already present): '
                + ', '.join(result['keys_skipped']),
            )
        self.result_summary = '\n'.join(lines)

        _logger.info(
            "Wallet '%s' import done via wizard: +%d, skip %d, "
            "overwrite %d.",
            self.wallet_id.name, self.result_imported,
            self.result_skipped, self.result_overwritten,
        )

        # Re-открива wizard формата с резултатите
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'show_import_result': True},
        }
