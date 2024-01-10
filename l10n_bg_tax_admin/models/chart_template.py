#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, Command, _, osv


class AccountTaxTemplate(models.Model):
    _name = 'account.fiscal.position.type.template'
    _description = 'Type Mapping Template of Fiscal Position'
    _order = 'position_id'

    position_id = fields.Many2one('account.fiscal.position.template',
                                  string='Fiscal Position',
                                  required=True,
                                  ondelete='cascade')
    position_dest_id = fields.Many2one('account.fiscal.position',
                                       string='Replacement fiscal position')
    invoice_type = fields.Selection([
        ('out_invoice', 'Customer Invoice'),
        ('out_refund', 'Customer Credit Note'),
        ('in_invoice', 'Vendor Bill'),
        ('in_refund', 'Vendor Credit Note'),
        ('out_receipt', 'Sales Receipt'),
        ('in_receipt', 'Purchase Receipt'),
    ], 'Invoice type',
        index=True,
        copy=False
    )
    l10n_bg_type_vat = fields.Selection(selection=lambda self: self.env['account.move']._get_type_vat(),
                                        string="Type of numbering",
                                        default='standard',
                                        copy=False,
                                        index=True,
                                        )
    l10n_bg_doc_type = fields.Selection(selection=lambda self: self._get_doc_type(),
                                        string="Vat type document",
                                        default='01',
                                        copy=False,
                                        index=True,
                                        )
    l10n_bg_narration = fields.Char('Narration for audit report', translate=True)
    new_account_entry = fields.Boolean('Create new account entry')
