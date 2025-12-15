# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class L10nBgTaricImportWizard(models.TransientModel):
    _name = 'l10n_bg.taric.import.wizard'
    _description = 'TARIC Data Import Wizard'

    import_method = fields.Selection([
        ('file', 'Upload File'),
        ('url', 'Download from URL'),
    ], string='Import Method', default='file', required=True)

    file_data = fields.Binary(
        string='TARIC File',
        help="Upload Excel (.xlsx) or CSV file with TARIC data"
    )

    filename = fields.Char(string='Filename')

    circabc_url = fields.Char(
        string='CIRCABC URL',
        help="Direct link to TARIC Excel/CSV file on CIRCABC"
    )

    def action_import(self):
        """Изпълнява импорта"""
        self.ensure_one()

        TaricCache = self.env['l10n_bg.taric.cache']

        try:
            if self.import_method == 'file':
                if not self.file_data or not self.filename:
                    raise UserError(_("Please upload a file"))

                result = TaricCache.import_from_file(self.file_data, self.filename)

            elif self.import_method == 'url':
                if not self.circabc_url:
                    raise UserError(_("Please enter CIRCABC URL"))

                result = TaricCache.import_from_circabc_url(self.circabc_url)
            else:
                result = {}
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Import Successful'),
                    'message': result.get('message', _('TARIC data imported successfully')),
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            raise UserError(_("Import failed: %s") % str(e))
