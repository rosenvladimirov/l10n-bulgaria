#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models, _
from .chart_template import get_invoice_type, get_type_vat
from odoo.addons.l10n_bg_config.models.account_move import get_doc_type

_logger = logging.getLogger(__name__)


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    type_ids = fields.One2many('account.fiscal.position.type', 'position_id', string='Type Mapping', copy=True)

    def _map_type_domain(self, invoice_id):
        move_type = invoice_id and invoice_id.move_type or False
        if invoice_id.debit_origin_id:
            if invoice_id.is_sale_document:
                move_type = 'in_debit_note'
            elif invoice_id.is_purchase_document:
                move_type = 'out_debit_note'
        return [
            ('position_id', '=', self.id),
            ('invoice_type', '=', move_type),
            # ('l10n_bg_type_vat', '=', invoice_id.l10n_bg_type_vat)
        ]

    def map_type(self, invoice_id):
        # _logger.info(f"invoice id: {invoice_id}")
        if not invoice_id:
            return False
        return self.env['account.fiscal.position.type'].search(self._map_type_domain(invoice_id))


class AccountFiscalPositionType(models.Model):
    _name = 'account.fiscal.position.type'
    _description = 'Accounts Mapping of Fiscal Position'
    _rec_name = 'position_id'
    _check_company_auto = True

    position_id = fields.Many2one('account.fiscal.position',
                                  string='Fiscal Position',
                                  required=True, ondelete='cascade')
    position_dest_id = fields.Many2one('account.fiscal.position',
                                       string='Replacement fiscal position')
    invoice_type = fields.Selection(selection=get_invoice_type(),
                                    string='Invoice type',
                                    index=True,
                                    copy=False
                                    )
    l10n_bg_type_vat = fields.Selection(selection=get_type_vat(),
                                        string="Type of numbering",
                                        default='standard',
                                        copy=False,
                                        index=True,
                                        )
    l10n_bg_doc_type = fields.Selection(selection=get_doc_type(),
                                        string="Vat type document",
                                        default='01',
                                        copy=False,
                                        index=True,
                                        )
    l10n_bg_narration = fields.Char('Narration for audit report', translate=True)
    new_account_entry = fields.Boolean('Create new account entry')
