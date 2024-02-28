#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_bg_narration = fields.Char('Narration for audit report', translate=True, copy=False)
    l10n_bg_doc_type = fields.Selection(selection=lambda self: self._get_doc_type(),
                                        string="Vat type document",
                                        default='01',
                                        copy=False)
