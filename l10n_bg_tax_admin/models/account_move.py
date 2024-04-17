#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from functools import lru_cache

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    # ---------------
    # PROTOCOL FIELDS
    # ---------------

    l10n_bg_protocol_date = fields.Date("Technical Protocol date", copy=False, default=fields.Date.today())
    l10n_bg_protocol_invoice_id = fields.Many2one(
        'account.move.bg.protocol',
        'Protocol',
        states={'draft': [('readonly', True)]},
    )

    # ---------------
    # SALE REPORT FIELDS
    # ---------------

    l10n_bg_report_sale_date = fields.Date("Technical Report sale date", copy=False, default=fields.Date.today())
    l10n_bg_report_sale_id = fields.Many2one(
        'account.move.bg.protocol',
        'Report Sale',
        states={'draft': [('readonly', True)]},
    )

    # --------------
    # CUSTOMS FIELDS
    # --------------

    l10n_bg_customs_type = fields.Selection(selection=[
        ('customs', _('Customs record')),
        ('invoices', _('Invoice record'))
    ], string='Customs type')
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
                                                 string='Partner in Customs',
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
                move.l10n_bg_currency_rate = 1.0
            else:
                if move.currency_id:
                    move.l10n_bg_currency_rate = get_rate(
                        from_currency=move.company_currency_id,
                        to_currency=move.currency_id,
                        company=move.company_id,
                        date=move.invoice_date or move.date or fields.Date.context_today(move),
                    )
                else:
                    move.l10n_bg_currency_rate = 1.0

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange("l10n_bg_currency_rate")
    def _onchange_l10n_bg_currency_rate(self):
        if self.l10n_bg_type_vat in ('in_customs', 'out_customs'):
            self.line_ids._compute_currency_rate()
            self.line_ids._inverse_amount_currency()

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
        if self.company_id.vat.lower().lstrip().startswith('bg'):
            base_name = [x for x in self.name.split('/')[-1] if x.isdigit()]
            decade = str(self.journal_id.decade)
            base_name = [decade] + ['0'] * (10 - len(base_name) - len(decade)) + base_name
            name = ''.join(base_name)
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

    def _customs_vals(self, map_id, partner_id):
        partner_id = partner_id or self.partner_id
        base_lines = self.invoice_line_ids.filtered(lambda r: r.display_type == 'product')
        amount_currency_total = debit = credit = 0.0
        factor_percent = map_id.factor_percent == 0.0 and 100.0 or map_id.factor_percent
        for line in base_lines:
            amount_currency_total += line.amount_currency
            debit += line.debit
            credit += line.credit
        debit *= factor_percent/100
        credit *= factor_percent/100
        amount_currency_total *= factor_percent/100
        aml_vals_list = []
        # Create partner lines
        partner_account_id = self.env['account.account']._get_most_frequent_account_for_partner(
            company_id=self.company_id.id,
            partner_id=partner_id.id,
            move_type=self.move_type,
        )
        if debit != 0:
            aml_vals_list.append(Command.create({
                'account_id': map_id.account_id and map_id.account_id.id or partner_account_id,
                'partner_id': partner_id.id,
                'currency_id': self.currency_id.id,
                'debit': debit > 0 or 0.0,
                'credit': debit < 0 or 0.0,
                'amount_currency': amount_currency_total,
                'balance': amount_currency_total,
                'display_type': 'product',
            }))
        if credit != 0:
            aml_vals_list.append(Command.create({
                'account_id': map_id.account_id and map_id.account_id.id or partner_account_id,
                'partner_id': partner_id.id,
                'currency_id': self.currency_id.id,
                'debit': credit < 0.0 or 0.0,
                'credit': credit > 0.0 or 0.0,
                'amount_currency': amount_currency_total,
                'balance': amount_currency_total,
                'display_type': 'product',
            }))
        return {
            'move_type': 'entry',
            'partner_id': partner_id.id,
            'l10n_bg_type_vat': 'standard',
            'l10n_bg_customs_type': 'customs',
            'fiscal_position_id': map_id.position_dest_id.id,
            'l10n_bg_customs_invoice_id': self.id,
            'l10n_bg_customs_date': self.invoice_date,
            'l10n_bg_customs_commercial_partner_id': self.commercial_partner_id.id,
            'l10n_bg_customs_partner_shipping_id': self.partner_shipping_id.id,
            'line_ids': [Command.clear()] + aml_vals_list,
            'invoice_line_ids': [Command.clear()],
            'l10n_bg_customs_invoice_ids': [Command.set(self.ids)]
        }

    def _post(self, soft=True):
        nra_id = self.env.ref('l10n_bg_tax_admin.nra', raise_if_not_found=False)
        to_post = super()._post(soft=soft)
        for move in to_post:
            map_id = move.fiscal_position_id.map_type(move)
            # _logger.info(f"MAP {map_id.l10n_bg_type_vat}:{map_id.new_account_entry} - {line}")
            if map_id:
                move.write({
                    'l10n_bg_type_vat': map_id.l10n_bg_type_vat,
                    'l10n_bg_doc_type': map_id.l10n_bg_doc_type,
                    'l10n_bg_narration': map_id.l10n_bg_narration,
                    # 'l10n_bg_force_new_entry': map_id.new_account_entry,
                })
            if map_id.new_account_entry and map_id.l10n_bg_type_vat in ('in_customs', 'out_customs'):
                self.env['account.move'].search([
                    ('id', '=', move.l10n_bg_customs_invoice_id.id),
                    ('move_type', '=', 'entry')
                ]).unlink()
                if map_id and not map_id.position_dest_id:
                    raise UserError(_('Missing configuration for replacing fiscal position for export/import customs'))
                move._default_l10n_bg_currency_rate()
                customs_entry_id = move.copy(move._customs_vals(map_id, nra_id))
                move.l10n_bg_customs_type = 'invoices'
                move.l10n_bg_customs_invoice_id = customs_entry_id.id
            if move.is_purchase_document(False) \
                and move.l10n_bg_type_vat == '117_protocol' \
                and not move.l10n_bg_protocol_invoice_id:
                protocol_id = self.env['account.move.bg.protocol']. \
                    create(self.env['account.move.bg.protocol']._protocol_vals(move))
                move.l10n_bg_protocol_invoice_id = protocol_id.id
            if move.is_sale_document(True) \
                and move.l10n_bg_type_vat == '119_report' \
                and not move.l10n_bg_report_sale_id:
                report_sale_id = self.env['account.move.bg.report.sale']. \
                    create(self.env['account.move.bg.report.sale']._report_vals(move))
                move.l10n_bg_report_sale_id = report_sale_id.id
            if move.l10n_bg_customs_type and not (map_id.new_account_entry
                                                  and map_id.l10n_bg_type_vat in ('in_customs', 'out_customs')):
                move.l10n_bg_customs_type = False
        return to_post

    def button_draft(self):
        # _logger.info(f"STATE #: {self.state}")
        for line in self.filtered(lambda r: r.state == 'posted'):
            if line.l10n_bg_customs_invoice_id:
                self.env['account.move'].search([
                    ('id', '=', line.l10n_bg_customs_invoice_id.id),
                    ('move_type', '=', 'entry')
                ]).unlink()

            if line.l10n_bg_protocol_invoice_id:
                self.env['account.move.bg.protocol'].search([
                    ('id', '=', line.l10n_bg_protocol_invoice_id.id),
                ]).unlink()

            if line.l10n_bg_report_sale_id:
                self.env['account.move.bg.report.sale'].search([
                    ('id', '=', line.l10n_bg_report_sale_id.id),
                ]).unlink()
        super().button_draft()

    def button_cancel(self):
        for line in self.filtered(lambda r: r.state != 'posted'):
            if self.l10n_bg_customs_invoice_id:
                self.env['account.move'].search([
                    ('id', '=', line.l10n_bg_customs_invoice_id.id),
                    ('move_type', '=', 'entry')
                ]).unlink()

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
    def get_vendor_customs(self, include_receipts=False):
        return self.get_vendor_invoice(include_receipts=include_receipts), ['in_customs']

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
    def is_vendor_customs(self, include_receipts=False):
        move_type, l10n_bg_type_vat = self.get_vendor_customs(include_receipts=include_receipts)
        if self.move_type in move_type and self.l10n_bg_type_vat in l10n_bg_type_vat:
            return True
        return False

    @api.model
    def get_customer_invoice(self, include_receipts=False):
        return ['out_invoice'] + (include_receipts and ['out_receipt'] or [])

    @api.model
    def get_customer_refund(self, include_receipts=False):
        return ['out_refund']

    @api.model
    def get_customer_customs(self, include_receipts=False):
        return self.get_customer_invoice(include_receipts=include_receipts), ['out_customs']

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

    @api.model
    def is_customer_customs(self, include_receipts=False):
        move_type, l10n_bg_type_vat = self.get_customer_customs(include_receipts=include_receipts)
        if self.move_type in move_type and self.l10n_bg_type_vat in l10n_bg_type_vat:
            return True
        return False

    # ------------------------------------
    #  ACTIONS
    # ------------------------------------
    def view_account_custom(self):
        self.ensure_one()
        result = self.env.ref("account.action_move_in_invoice_type")
        result = result.read()[0]
        result['res_id'] = self.l10n_bg_customs_invoice_id.id
        result['view_mode'] = 'form'
        result["domain"] = [("id", "=", self.l10n_bg_customs_invoice_id.id)]
        return result

    def view_account_protocol(self):
        self.ensure_one()
        if self.l10n_bg_protocol_invoice_id:
            result = self.env.ref("l10n_bg_tax_admin.action_protocol_account_move")
            result = result.read()[0]
            result['context'] = {
                'default_account_move_id': self.id,
                'date_creation': self.invoice_date,
            }
            result["domain"] = [("id", "=", self.l10n_bg_protocol_invoice_id.id)]
            return result
