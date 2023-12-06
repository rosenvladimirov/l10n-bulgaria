#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from contextlib import contextmanager
from functools import lru_cache

from odoo import api, fields, models, _, Command
from odoo.osv import expression

_logger = logging.getLogger(__name__)


# TYPE_VAT_CODE = {
#     '117_protocol': 'PR',
#     'in_customs': 'IMP',
#     'out_customs': 'EXP',
# }


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_type_vat(self):
        return [
            ('standard', _('Accounting document')),
            ('117_protocol', _('Art. 117 - Protocols')),
            ('in_customs', _('Import Customs declaration')),
            ('out_customs', _('Export Customs declaration')),
        ]

    def _get_doc_type(self):
        return [
            ('01', _('Invoice')),
            ('02', _('Debit note')),
            ('03', _('Credit note')),
            ('04', _('Storeable goods sent to EU')),
            # Register of goods under the regime of storage of goods on demand,
            # sent or transported from the territory of the country to the territory of another member state
            ('05', _('Storeable goods receive from EU')),
            ('07', _('Customs declarations')),
            # Customs declaration/customs document certifying completion of customs formalities
            ('09', _('Protocols or other')),
            ('11', _('Invoice - cash reporting')),
            ('12', _('Debit notice - cash reporting')),
            ('13', _('Credit notice - cash statement')),
            ('50', _('Protocols fuel supplies')),
            ('81', _('Sales report - tickets')),
            ('82', _('Special tax order')),  # Report on the sales made under a special tax order
            ('83', _('sales of bread')),  # Report on the sales of bread
            ('84', _('Sales of flour')),  # Report on the sales of flour
            ('23', _('Credit note art. 126b')),  # Credit notification under Art. 126b, para. 1 of VAT
            ('29', _('Protocol under Art. 126b')),  # Protocol under Art. 126b, para. 2 and 7 of VAT
            ('91', _('Protocol under Art. 151c')),  # Protocol for the required tax under Art. 151c, para. 3 of the law
            ('92', _('Protocol under Art. 151g')),
            # Protocol on the tax credit under Art. 151g,
            # para. 8 of the law or a report under Art. 104g, para. 14
            ('93', _('Protocol under Art. 151c')),
            # Protocol for the required tax under Art. 151c,
            # para. 7 of the law with a delivery recipient who does not apply the special regime
            ('94', _('Protocol under Art. 151c, para. 7')),
            # Protocol for the required tax under Art. 151c,
            # para. 7 of the law with a delivery recipient, a person who applies the special regime
            ('95', _('Protocol for free provision of foodstuffs')),
            # Protocol for free provision of foodstuffs, to which Art. 6, para. 4, item 4 VAT
        ]

    l10n_bg_type_vat = fields.Selection(selection=lambda self: self._get_type_vat(),
                                        string="Type of numbering",
                                        default='standard',
                                        copy=False)
    l10n_bg_doc_type = fields.Selection(selection=lambda self: self._get_doc_type(),
                                        string="Vat type document",
                                        default='01',
                                        copy=False)
    l10n_bg_name = fields.Char('Number of locale document', index='trigram', tracking=True, copy=False)

    # ---------------
    # PROTOCOL FIELDS
    # ---------------

    l10n_bg_protocol_date = fields.Date("Protocol date", copy=False, default=fields.Date.today())
    l10n_bg_protocol_invoice_id = fields.Many2one(
        'account.move.bg.protocol',
        'Protocol',
        states={'draft': [('readonly', True)]},
    )
    l10n_bg_protocol_line_ids = fields.One2many(  # /!\ protocol_line_ids is just a subset of line_ids.
        'account.move.line',
        'move_id',
        string='Protocol lines',
        copy=False,
        readonly=True,
        domain=[('display_type', 'in', ('product', 'line_section', 'line_note'))],
        states={'draft': [('readonly', True)]},
    )

    # --------------
    # CUSTOMS FIELDS
    # --------------

    l10n_bg_currency_rate = fields.Float('Statistics currency rate',
                                         default=lambda self: self._default_l10n_bg_currency_rate(),
                                         help="Statistics currency rate for customs in Bulgaria.",
                                         )
    l10n_bg_customs_date = fields.Char("Customs date", copy=False)
    l10n_bg_customs_invoice_id = fields.Many2one('account.move',
                                                 string='Base invoice',
                                                 check_company=True,
                                                 copy=False,
                                                 readonly=True,
                                                 states={'draft': [('readonly', True)]},
                                                 )
    # === Partner fields === #
    l10n_bg_customs_partner_id = fields.Many2one('res.partner',
                                                 string='Included invoices in Customs',
                                                 related='l10n_bg_customs_invoice_id.partner_id')
    l10n_bg_customs_commercial_partner_id = fields.Many2one(
        'res.partner',
        string='Commercial Entity Customs',
        related='l10n_bg_customs_invoice_id.commercial_partner_id',
        ondelete='restrict',
    )
    l10n_bg_customs_partner_shipping_id = fields.Many2one(
        comodel_name='res.partner',
        string='Delivery Address Customs',
        related='l10n_bg_customs_invoice_id.partner_shipping_id',
        help="Delivery address for current invoice.",
    )
    l10n_bg_customs_invoice_ids = fields.Many2many('account.move',
                                                   'customs_invoices_rel',
                                                   'invoice_id',
                                                   'customs_id',
                                                   string='Used invoices in customs',
                                                   check_company=True,
                                                   copy=False,
                                                   readonly=True,
                                                   states={'draft': [('readonly', False)]},
                                                   )
    l10n_bg_customs_line_ids = fields.One2many(  # /!\ invoice_line_ids is just a subset of line_ids.
        'account.move.line',
        'move_id',
        string='Invoices lines for customs',
        copy=False,
        readonly=True,
        domain=[('display_type', 'in', ('product', 'line_section', 'line_note'))],
        states={'draft': [('readonly', False)]},
    )

    # -------------------------------------------------------------------------
    # DEFAULT METHODS
    # -------------------------------------------------------------------------

    @api.depends('currency_id', 'company_id', 'date')
    def _default_l10n_bg_currency_rate(self):
        @lru_cache()
        def get_rate(from_currency, to_currency, company, date):
            return self.env['res.currency'].with_context(dict(self._context, statistic_rate=True))._get_conversion_rate(
                from_currency=from_currency,
                to_currency=to_currency,
                company=company,
                date=date,
            )

        for move in self:
            if move.l10n_bg_type_vat not in ('in_customs', 'out_customs'):
                move.l10n_bg_currency_rate = 1
            else:
                if move.currency_id:
                    move.l10n_bg_currency_rate = get_rate(
                        from_currency=move.company_currency_id,
                        to_currency=move.currency_id,
                        company=move.company_id,
                        date=move.invoice_date or move.date or fields.Date.context_today(move),
                    )
                else:
                    move.l10n_bg_currency_rate = 1

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange('l10n_bg_type_vat')
    @api.depends('fiscal_position_id')
    def _onchange_type_vat(self):
        if self.l10n_bg_type_vat == '117_protocol':
            for line in self.line_ids:
                copied_vals = line.copy_data()[0]
                self.l10n_bg_protocol_line_ids += self.env['account.move.line'].new(copied_vals)
        elif self.l10n_bg_type_vat in ('in_customs', 'out_customs'):
            self._default_l10n_bg_currency_rate()
            # self.line_ids._compute_currency_rate()
            # self.line_ids._inverse_amount_currency()
        else:
            self.l10n_bg_protocol_line_ids = False

    @api.onchange("l10n_bg_currency_rate")
    def _onchange_l10n_bg_currency_rate(self):
        if self.l10n_bg_type_vat in ('in_customs', 'out_customs'):
            self.line_ids._compute_currency_rate()
            self.line_ids._inverse_amount_currency()

    @api.onchange('l10n_bg_customs_invoice_ids')
    def _onchange_customs_invoice_ids(self):
        if self.l10n_bg_customs_invoice_ids:
            for line in self.l10n_bg_customs_invoice_ids.mapped('line_ids'):
                copied_vals = line.copy_data()[0]
                self.l10n_bg_customs_line_ids += self.env['account.move.line'].new(copied_vals)
        else:
            self.l10n_bg_customs_invoice_ids = False

    @api.onchange('fiscal_position_id')
    def _onchange_fiscal_position_id(self):
        if self.fiscal_position_id:
            if self.is_purchase_document():
                self.l10n_bg_type_vat = self.fiscal_position_id.purchase_type_vat
                if self.is_vendor_invoice():
                    self.l10n_bg_doc_type = self.fiscal_position_id.purchase_doc_type
                elif self.is_vendor_refund():
                    self.l10n_bg_doc_type = self.fiscal_position_id.purchase_refund_doc_type
                elif self.is_vendor_debit_note():
                    self.l10n_bg_doc_type = self.fiscal_position_id.purchase_dn_doc_type
            elif self.is_sale_document():
                self.l10n_bg_type_vat = self.fiscal_position_id.sale_type_vat
                if self.is_customer_invoice():
                    self.l10n_bg_doc_type = self.fiscal_position_id.sale_doc_type
                elif self.is_customer_refund():
                    self.l10n_bg_doc_type = self.fiscal_position_id.sale_refund_doc_type
                elif self.is_customer_debit_note():
                    self.l10n_bg_doc_type = self.fiscal_position_id.sale_dn_doc_type

    # -------------------------------------------------------------------------
    # PAYMENT REFERENCE
    # -------------------------------------------------------------------------

    def _get_invoice_reference_odoo_invoice(self):
        self.ensure_one()
        if self.l10n_bg_type_vat != 'standard':
            return ''.join([i for i in self.name if i.isdigit()]).zfill(10)
        else:
            return super()._get_invoice_reference_odoo_invoice()

    def _get_invoice_reference_bg_invoice(self):
        self.ensure_one()
        if self.partner_id.l10n_bg_uic == '999999999999999':
            name = self.name
        elif (self.partner_id.vat.lower().lstrip().startswith('bg')
              or self.partner_id.l10n_bg_uic != '999999999999999'):
            name = ''.join([x for x in self.name if x.isdigit()]).zfill(10)
        else:
            name = self.name
        return name

    def _get_invoice_reference_bg_partner(self):
        self.ensure_one()
        if self.partner_id.l10n_bg_uic != '999999999999999':
            name = self.partner_id.vat.zfill(21) + self.ref
        else:
            name = (self.partner_id.l10n_bg_uic or self.partner_id.vat).zfill(21) + ''.join(
                [i for i in self.ref if i.isdigit()]).zfill(10)
        return name

    def _get_move_display_name(self, show_ref=False):
        self.ensure_one()
        name = super()._get_move_display_name(show_ref=show_ref)
        if self.l10n_bg_type_vat != 'standard':
            name += self.l10n_bg_name and "(%s)" % self.l10n_bg_name or ""
        return name

    def _protocol_vals(self):
        return {
            'move_id': self.id,
        }

    def _customs_vals(self, line):
        self.l10n_bg_customs_invoice_id = False
        return {
            'move_type': 'entry',
            'l10n_bg_type_vat': line.l10n_bg_type_vat,
            'invoice_line_ids': False,
            'l10n_bg_customs_invoice_id': line.id,
            'l10n_bg_customs_line_ids': [Command.set(line.line_ids.ids)],
            'l10n_bg_customs_date': line.invoice_date,
            'l10n_bg_customs_commercial_partner_id': line.commercial_partner_id.id,
            'l10n_bg_customs_partner_shipping_id': line.partner_shipping_id.id,
        }

    def _sanitize_vals(self, vals):
        vals = super()._sanitize_vals(vals)
        if 'line_ids' in vals and vals.get('l10n_bg_type_vat') == '117_protocol':
            protocol_lines = []
            line_ids = []
            if vals.get('l10n_bg_protocol_line_ids'):
                for command, protocol_id, protocol_line in vals['l10n_bg_protocol_line_ids']:
                    protocol_lines.append(protocol_id)
            for command, line_id, line_vals in vals['line_ids']:
                if command == Command.UPDATE and line_id and line_id not in protocol_lines:
                    line_ids.append(line_id)
            if line_ids:
                vals['l10n_bg_protocol_line_ids'] = [Command.set(line_ids)]
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        for line in moves.filtered(lambda r: r.state == 'posted'):
            if line.is_purchase_document(False) \
                    and line.l10n_bg_type_vat == 'in_customs' \
                    and line.line_ids:
                customs_entry_id = line.copy(self._customs_vals(line))
                line.l10n_bg_customs_invoice_id = customs_entry_id.id
            if line.is_purchase_document(False) \
                    and line.l10n_bg_type_vat == '117_protocol':
                protocol_id = self.env['account.move.bg.protocol'].create(self._protocol_vals())
                line.l10n_bg_protocol_invoice_id = protocol_id.id
        return moves

    def write(self, vals):
        res = super().write(vals)
        for line in self.filtered(lambda r: r.state == 'posted'):
            if line.is_invoice() and vals.get('l10n_bg_type_vat') in ('in_customs', 'out_customs'):
                old_l10n_bg_customs_invoice_id = self.env['account.move'].search([
                    ('id', '=', line.l10n_bg_customs_invoice_id.id),
                    ('move_type', '=', 'entry')
                ])
                if old_l10n_bg_customs_invoice_id:
                    old_l10n_bg_customs_invoice_id.unlink()
                customs_entry_id = line.copy(self._customs_vals(line))
                line.l10n_bg_customs_invoice_id = customs_entry_id.id
        return res

    def unlink(self):
        self.l10n_bg_customs_invoice_id.unlink()
        self.l10n_bg_protocol_invoice_id.unlink()
        return super().unlink()

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name and not filter(lambda r: r[2] == 'name', args):
            if operator in ('=', '!='):
                domain = ['|', ('name', operator, name), ('name_bg_second', operator, name)]
            else:
                domain = ['|', ('name', operator, name), ('name_bg_second', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    @api.model
    def get_vendor_invoice(self, include_receipts=False):
        return ['in_invoice'] + (include_receipts and ['in_receipt'] or [])

    @api.model
    def get_vendor_refund(self, include_receipts=False):
        return ['in_refund']

    @api.model
    def is_vendor_invoice(self, include_receipts=False):
        return self.move_type in self.get_vendor_invoice(include_receipts)

    @api.model
    def is_vendor_invoice(self, include_receipts=False):
        return self.move_type in self.get_vendor_refund(include_receipts)

    @api.model
    def is_vendor_refund(self, include_receipts=False):
        return self.move_type in self.get_vendor_refund(include_receipts)

    @api.model
    def is_vendor_debit_note(self, include_receipts=False):
        return len(self.debit_origin_id) == 1

    @api.model
    def get_customer_invoice(self, include_receipts=False):
        return ['out_invoice'] + (include_receipts and ['out_receipt'] or [])

    @api.model
    def get_customer_refund(self, include_receipts=False):
        return ['out_refund']

    @api.model
    def get_customer_debit_note(self, include_receipts=False):
        return ['out_debit_note']

    @api.model
    def is_customer_invoice(self, include_receipts=False):
        return self.move_type in self.get_customer_invoice(include_receipts)

    @api.model
    def is_customer_invoice(self, include_receipts=False):
        return self.move_type in self.get_customer_refund(include_receipts)

    @api.model
    def is_customer_refund(self, include_receipts=False):
        return self.move_type in self.get_customer_refund(include_receipts)

    @api.model
    def is_customer_debit_note(self, include_receipts=False):
        return self.move_type in self.get_customer_debit_note(include_receipts)

    # ------------------------------------
    #  ACTIONS
    # ------------------------------------
    def view_account_custom(self):
        self.ensure_one()
        result = self.env["ir.actions.act_window"]._for_xml_id(
            "account.action_move_in_invoice_type"
        )
        result["domain"] = [("id", "=", self.l10n_bg_customs_invoice_id.id)]
        return result
