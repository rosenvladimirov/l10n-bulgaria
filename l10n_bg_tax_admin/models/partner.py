# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import logging
from odoo import api, fields, models, _
from odoo.addons.l10n_bg_reports_audit.models.l10n_bg_file_helper import (
    get_doc_type,
    get_type_vat,
)

_logger = logging.getLogger(__name__)

MOVE_TYPES_TYPE_VAT = {
    'standard' : 'standard',
    '117_protocol_82_2': 'protocol',
    '117_protocol_84': 'protocol',
    '117_protocol_6_4': 'protocol',
    '117_protocol_6_3': 'private',
    '117_protocol_15': 'protocol',
    '117_protocol_82_2_2': 'protocol',
    '119_report': 'protocol_119',
}

BG_MOVE_TYPES = [
    ('standard', 'Standard'),
    ('customs', 'Customs'),
    ('invoice_customs', 'Invoice include in customs'),
    ('private', 'Private'),
    ('protocol', 'Protocol'),
]

MOVE_TYPES = [
    ('entry', 'Journal Entry'),
    ('out_invoice', 'Customer Invoice'),
    ('out_refund', 'Customer Credit Note'),
    ('in_invoice', 'Vendor Bill'),
    ('in_refund', 'Vendor Credit Note'),
    ('out_receipt', 'Sales Receipt'),
    ('in_receipt', 'Purchase Receipt'),
]


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    tax_action_map_ids = fields.One2many(
        'account.fiscal.position.tax.action',
        'position_id',
        string='Tax Action Map'
    )
    tax_action_map = fields.Binary(compute='_compute_tax_action_map')

    @api.depends('tax_action_map_ids')
    def _compute_tax_action_map(self):
        tax_action_map = defaultdict(dict)
        for position in self:
            for tl in position.tax_action_map_ids:
                tax_action_map[f"{tl.move_type}-{position.id}"].update({
                    'l10n_bg_move_type': tl.l10n_bg_move_type,
                    'l10n_bg_type_vat': tl.l10n_bg_type_vat,
                    'move_type': tl.move_type,
                    # Auto fill entries
                    'l10n_bg_doc_type': tl.l10n_bg_doc_type, # compatible remove next version
                    'l10n_bg_document_type': tl.l10n_bg_document_type,
                    'l10n_bg_narration': tl.l10n_bg_narration,
                    'partner_id': tl.partner_id.id,
                    # Replacement
                    'dest_move_type': tl.dest_move_type,
                    'position_dest_id': tl.position_dest_id.id,
                    'account_id': tl.account_id.id,
                    'factor_percent': tl.factor_percent,
                })
                if tl.position_dest_id:
                    tax_action_map.update(tl.position_dest_id._compute_tax_action_map())
            position.tax_action_map = dict(tax_action_map)


class AccountFiscalPositionTaxAction(models.Model):
    _name = 'account.fiscal.position.tax.action'
    _description = 'Tax Action of Fiscal Position'
    _rec_name = 'position_id'
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of

    position_id = fields.Many2one(
        'account.fiscal.position',
        string='Fiscal Position',
        required=True,
        ondelete='cascade'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='position_id.company_id',
        store=True
    )
    l10n_bg_move_type = fields.Selection(
        BG_MOVE_TYPES,
        string="Type of fiscal position",
        default="standard",
        copy=False,
    )
    move_type = fields.Selection(
        MOVE_TYPES,
        string="Type of move",
        copy=False,
    )
    # If new entry need
    dest_move_type = fields.Selection(
        MOVE_TYPES,
        string="Replacement Type of move",
        copy=False,
    )
    position_dest_id = fields.Many2one(
        "account.fiscal.position",
        string="Replacement fiscal position"
    )
    account_id = fields.Many2one(
        "account.account",
        string="Account",
        help="Account to use for base amount of tax"
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        help="Partner to use on generated tax lines",
    )
    factor_percent = fields.Float(
        string="%",
        default=100,
        help="Factor to apply on the account move lines generated from this distribution line, in percents",
    )

    # Auto fill entries
    l10n_bg_type_vat = fields.Selection(
        selection=get_type_vat(),
        string="Type of VAT",
        default="standard",
        copy=False,
        required=True,
    )
    # compatible remove next version
    l10n_bg_doc_type = fields.Selection(
        selection=get_doc_type(),
        string="VAT type document",
        default="01",
        copy=False,
        required=True,
    )
    l10n_bg_document_type = fields.Selection(
        selection=get_doc_type(),
        string="Document Type (BG)",
        default="01",
        copy=False,
        required=True,
    )
    l10n_bg_narration = fields.Char(
        "Narration for audit report",
        translate=True,
        required=True,
    )

    @api.onchange('l10n_bg_type_vat')
    def onchange_l10n_bg_type_vat(self):
        for record in self:
            if MOVE_TYPES_TYPE_VAT.get(record.l10n_bg_type_vat):
                record.l10n_bg_move_type = MOVE_TYPES_TYPE_VAT[record.l10n_bg_type_vat]
