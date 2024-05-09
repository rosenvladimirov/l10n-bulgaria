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
        readonly=True,
        states={'draft': [('readonly', False)]},
    )

    # ---------------
    # SALE REPORT FIELDS
    # ---------------

    l10n_bg_report_sale_date = fields.Date("Technical Report sale date", copy=False, default=fields.Date.today())
    l10n_bg_report_sale_id = fields.Many2one(
        'account.move.bg.protocol',
        'Report Sale',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )

    # --------------------------
    # Private credit reverse VAT
    # --------------------------
    l10n_bg_private_vat_date = fields.Date("Technical Self signed private VAT date", copy=False, default=fields.Date.today())
    l10n_bg_private_vat_id = fields.Many2one(
        'account.move.bg.protocol',
        'Self signed Private VAT',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    l10n_bg_private_vat_invoice_ids = fields.Many2many('account.move',
                                                   'private_vat_invoices_rel',
                                                   'invoice_id',
                                                   'customs_id',
                                                   string='Used invoices for private vat',
                                                   check_company=True,
                                                   copy=False,
                                                   readonly=True,
                                                   states={'draft': [('readonly', False)]},
                                                   )

    # --------------
    # CUSTOMS FIELDS
    # --------------

    l10n_bg_customs_date = fields.Date("Customs date", copy=False)
    l10n_bg_customs_invoice_id = fields.Many2one('account.move',
                                                 string='Base invoice',
                                                 check_company=True,
                                                 copy=False,
                                                 readonly=True,
                                                 states={'draft': [('readonly', False)]},
                                                 )
    l10n_bg_customs_id = fields.Many2one(
        'account.move.bg.customs',
        'Customs',
        readonly=True,
        states = {'draft': [('readonly', False)]},
    )
    l10n_bg_customs_date_custom_id = fields.Date("Customs date", related='l10n_bg_customs_invoice_id.l10n_bg_customs_date')
    l10n_bg_name_custom_id = fields.Char("Customs number", related='l10n_bg_customs_invoice_id.l10n_bg_name')
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
    l10n_bg_currency_rate = fields.Float('Statistics currency rate',
                                         default=lambda self: self._default_l10n_bg_currency_rate(),
                                         digits='Currency rate',
                                         help="Statistics currency rate for customs in Bulgaria.",
                                         )
    tax_totals_signed = fields.Binary(
        string="Invoice Totals in Currency",
        compute='_compute_tax_totals_signed',
        exportable=False,
    )

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
            if move.l10n_bg_type_vat == 'in_customs':
                if move.currency_id:
                    l10n_bg_currency_rate = get_rate(
                        from_currency=move.company_currency_id,
                        to_currency=move.currency_id,
                        company=move.company_id,
                        date=move.invoice_date or move.date or fields.Date.context_today(move),
                    )
                    move.l10n_bg_currency_rate = l10n_bg_currency_rate or 1.0
                else:
                    move.l10n_bg_currency_rate = 1.0

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

    @api.depends_context('lang')
    @api.depends(
        'invoice_line_ids.currency_rate',
        'invoice_line_ids.tax_base_amount',
        'invoice_line_ids.tax_line_id',
        'invoice_line_ids.price_total',
        'invoice_line_ids.price_subtotal',
        'invoice_payment_term_id',
        'partner_id',
        'currency_id',
    )
    def _compute_tax_totals_signed(self):
        for move in self:
            if move.is_invoice(include_receipts=True):
                base_lines = move.invoice_line_ids.filtered(lambda line: line.display_type == 'product')
                base_line_values_list = [line._convert_to_tax_base_line_dict() for line in base_lines]
                sign = move.direction_sign
                if move.id:
                    # The invoice is stored so we can add the early payment discount lines directly to reduce the
                    # tax amount without touching the untaxed amount.
                    base_line_values_list += [
                        {
                            **line._convert_to_tax_base_line_dict(),
                            'handle_price_include': False,
                            'quantity': 1.0,
                            'price_unit': sign * line.amount_currency,
                        }
                        for line in move.line_ids.filtered(lambda line: line.display_type == 'epd')
                    ]

                kwargs = {
                    'base_lines': base_line_values_list,
                    'currency': move.currency_id or move.journal_id.currency_id or move.company_id.currency_id,
                }

                if move.id:
                    kwargs['tax_lines'] = [
                        line._convert_to_tax_line_dict()
                        for line in move.line_ids.filtered(lambda line: line.display_type == 'tax')
                    ]
                else:
                    # In case the invoice isn't yet stored, the early payment discount lines are not there. Then,
                    # we need to simulate them.
                    epd_aggregated_values = {}
                    for base_line in base_lines:
                        if not base_line.epd_needed:
                            continue
                        for grouping_dict, values in base_line.epd_needed.items():
                            epd_values = epd_aggregated_values.setdefault(grouping_dict, {'price_subtotal': 0.0})
                            epd_values['price_subtotal'] += values['price_subtotal']

                    for grouping_dict, values in epd_aggregated_values.items():
                        taxes = None
                        if grouping_dict.get('tax_ids'):
                            taxes = self.env['account.tax'].browse(grouping_dict['tax_ids'][0][2])

                        kwargs['base_lines'].append(self.env['account.tax']._convert_to_tax_base_line_dict(
                            None,
                            partner=move.partner_id,
                            currency=move.currency_id,
                            taxes=taxes,
                            price_unit=values['price_subtotal'],
                            quantity=1.0,
                            account=self.env['account.account'].browse(grouping_dict['account_id']),
                            analytic_distribution=values.get('analytic_distribution'),
                            price_subtotal=values['price_subtotal'],
                            is_refund=move.move_type in ('out_refund', 'in_refund'),
                            handle_price_include=False,
                            extra_context={'_extra_grouping_key_': 'epd'},
                        ))
                move.tax_totals_signed = self.env['account.tax']._prepare_tax_totals_signed(**kwargs)
            else:
                move.tax_totals_signed = None

    def _new_entry_vals(self, fiscal_position_id):
        return {
            'move_type': 'entry',
            'date': self.date,
            'fiscal_position_id': fiscal_position_id.id,
            'line_ids': [Command.clear()],
            'invoice_line_ids': [Command.clear()],
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
                })
            if map_id.new_account_entry:
                if map_id and not map_id.position_dest_id:
                    raise UserError(_('Missing configuration for replacing fiscal position for export/import customs'))
                new_entry_id = move.copy(move._new_entry_vals(map_id.position_dest_id))
                map_id = new_entry_id.fiscal_position_id.map_type(new_entry_id)
                if map_id:
                    new_entry_id.write({
                        'l10n_bg_type_vat': map_id.l10n_bg_type_vat,
                        'l10n_bg_doc_type': map_id.l10n_bg_doc_type,
                        'l10n_bg_narration': map_id.l10n_bg_narration,
                    })
                if new_entry_id.l10n_bg_type_vat == 'in_customs':
                    self.env['account.move'].search([
                        ('id', '=', move.l10n_bg_customs_invoice_id.id),
                        ('move_type', '=', 'entry')
                    ]).unlink()
                    move.write({
                        'l10n_bg_customs_invoice_id': new_entry_id.id,
                        'l10n_bg_type_vat': 'standard',
                    })
                    customs_id = self.env['account.move.bg.customs']. \
                        create(self.env['account.move.bg.customs']._customs_vals(new_entry_id))
                    new_entry_id.write({
                        'partner_id': nra_id.id,
                        'partner_shipping_id': move.partner_shipping_id.id,
                        'l10n_bg_customs_id': customs_id.id,
                        'l10n_bg_customs_invoice_id': move.id,
                        'l10n_bg_customs_date': move.invoice_date,
                        'l10n_bg_customs_commercial_partner_id': move.commercial_partner_id.id,
                        'l10n_bg_customs_partner_shipping_id': move.partner_shipping_id.id,
                        'invoice_line_ids': customs_id._customs_aml(move, new_entry_id, map_id),
                        'l10n_bg_customs_invoice_ids': [Command.set(move.ids)]
                    })
                    new_entry_id._default_l10n_bg_currency_rate()
                elif new_entry_id.l10n_bg_type_vat == '117_protocol' and move.is_purchase_document():
                    l10n_bg_private_vat_id = self.env['account.move.bg.protocol']. \
                        create(self.env['account.move.bg.protocol']._protocol_vals(move))
                    move.l10n_bg_private_vat_id = l10n_bg_private_vat_id
                    new_entry_id.write({
                        'partner_id': move.partner_id.id,
                        'date': move.invoice_date or move.date,
                        'l10n_bg_private_vat_invoice_ids': [Command.set(move.ids)]
                    })

            if move.is_purchase_document(False) \
                and move.l10n_bg_type_vat == '117_protocol' \
                and not move.l10n_bg_protocol_invoice_id:
                protocol_id = self.env['account.move.bg.protocol']. \
                    create(self.env['account.move.bg.protocol']._protocol_vals(move))
                move.l10n_bg_protocol_invoice_id = protocol_id.id
                protocol_id._compute_protocol_name()
            if move.is_sale_document(True) \
                and move.l10n_bg_type_vat == '119_report' \
                and not move.l10n_bg_report_sale_id:
                report_sale_id = self.env['account.move.bg.report.sale']. \
                    create(self.env['account.move.bg.report.sale']._report_vals(move))
                move.l10n_bg_report_sale_id = report_sale_id.id
        return to_post

    def button_draft(self):
        # _logger.info(f"STATE #: {self.state}")
        for line in self.filtered(lambda r: r.state == 'posted'):
            if line.l10n_bg_customs_invoice_id:
                self.env['account.move.bg.customs'].search([
                    ('move_id', '=', line.l10n_bg_customs_id.id),
                ]).unlink()
                customs_move_id = self.env['account.move'].search([
                    ('id', '=', line.l10n_bg_customs_invoice_id.id),
                    ('move_type', '=', 'entry')
                ])
                if customs_move_id.state == 'posted':
                    customs_move_id.button_draft()
                customs_move_id.unlink()

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
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange("l10n_bg_currency_rate")
    def _onchange_l10n_bg_currency_rate(self):
        if self.l10n_bg_type_vat == 'in_customs':
            self.line_ids._compute_currency_rate()
            self.line_ids._inverse_amount_currency()

    @api.onchange('l10n_bg_customs_invoice_ids')
    def _onchange_l10n_bg_customs_invoice_ids(self):
        if self.l10n_bg_customs_invoice_ids - self.l10n_bg_customs_invoice_id:
            map_id = self.l10n_bg_customs_invoice_id.fiscal_position_id.map_type(self.l10n_bg_customs_invoice_id)
            for invoice_id in (self.l10n_bg_customs_invoice_ids - self.l10n_bg_customs_invoice_id):
                if self.invoice_line_ids.filtered(lambda r: r.l10n_bg_customs_invoice_id == invoice_id):
                    continue
                self.invoice_line_ids = self.l10n_bg_customs_id._customs_aml(invoice_id, self, map_id)
            for line in self.line_ids:
                if line.l10n_bg_customs_invoice_id.id not in self.l10n_bg_customs_invoice_ids.ids:
                    line.unlink()

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
        result.update({
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.l10n_bg_customs_invoice_id.id,
            'domain': [('id', '=', self.l10n_bg_customs_invoice_id.id)],
        })
        return result

    def view_account_protocol(self):
        self.ensure_one()
        if self.l10n_bg_protocol_invoice_id:
            result = self.env.ref("l10n_bg_tax_admin.action_protocol_account_move")
            result = result.read()[0]
            result.update({
                'context': {
                    'default_account_move_id': self.id,
                    'date_creation': self.invoice_date,
                },
                'view_type': 'form',
                'view_mode': 'form',
                'res_id': self.l10n_bg_protocol_invoice_id.id,
                'domain': [('id', '=', self.l10n_bg_protocol_invoice_id.id)],
            })
            return result
