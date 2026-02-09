#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class AccountMoveBgCustoms(models.Model):
    _name = "account.move.bg.customs"
    _inherits = {"account.move": "l10n_bg_customs_move_id"}
    _inherit = ['mail.thread.main.attachment', 'mail.activity.mixin', 'sequence.mixin']
    _description = "VAT customs declaration for income invoices"
    _order = "l10n_bg_customs_date_creation desc, l10n_bg_customs_name desc, id desc"
    _mail_post_access = "read"
    _check_company_auto = True
    _sequence_field = "l10n_bg_customs_name"

    # Основни полета
    l10n_bg_customs_move_id = fields.Many2one(
        "account.move",
        string="Account invoice",
        ondelete="cascade",
        required=True,
        index=True,
    )
    l10n_bg_customs_invoice_ids = fields.Many2many(
        "account.move",
        "invoices_customs_vat_rel",
        "customs_id",
        "invoice_id",
        string="Used invoices for private vat",
        check_company=True,
        copy=False,
        readonly=True,
    )

    # Дати и номера
    l10n_bg_customs_date_creation = fields.Date(
        "Theatrical field with Created Date",
        required=True,
        default=fields.Date.today()
    )
    l10n_bg_customs_name = fields.Char(
        string="Customs Declaration Number",
        compute="_compute_l10n_bg_customs_name",
        inverse="_inverse_l10n_bg_customs_name",
        readonly=False,
        store=True,
        copy=False,
        tracking=True,
        index="trigram",
    )
    l10n_bg_customs_name_placeholder = fields.Char(
        compute='_compute_l10n_bg_customs_name_placeholder'
    )
    l10n_bg_customs_highest_name = fields.Char(
        compute='_compute_l10n_bg_customs_highest_name'
    )

    # Митнически номера
    declaration_number = fields.Char(
        string='Internal Declaration Number',
        tracking=True,
        help="Internal number of the customs declaration"
    )
    declaration_date = fields.Date(
        string='Declaration Date',
        tracking=True
    )

    lrn = fields.Char(
        string='LRN (Local Reference Number)',
        tracking=True,
        help="Local reference number generated before submission to customs"
    )

    mrn = fields.Char(
        string='MRN (Movement Reference Number)',
        size=18,
        tracking=True,
        help="Official customs number (18 characters, e.g. 25BG001234E123456)"
    )

    transit_declaration_number = fields.Char(
        string='Transit Declaration Number',
        tracking=True,
        help="Transit declaration number (if applicable)"
    )

    container_number = fields.Char(
        string='Container Number',
        tracking=True,
        help="Unique container identifier for container shipments"
    )

    # EORI номера
    partner_eori = fields.Char(
        string='Partner EORI',
        related='partner_id.l10n_bg_eori',
        readonly=True,
        help="EORI number of the partner"
    )

    company_eori = fields.Char(
        string='Company EORI',
        related='company_id.partner_id.l10n_bg_eori',
        readonly=True,
        help="EORI number of the company"
    )

    # Инкотермс
    incoterm_location = fields.Char(
        string='Incoterm Location',
        help="Place of delivery according to Incoterms"
    )

    # Държави
    country_of_origin_id = fields.Many2one(
        'res.country',
        string='Country of Origin',
        tracking=True,
        help="Country of origin of goods"
    )
    country_of_dispatch_id = fields.Many2one(
        'res.country',
        string='Country of Dispatch',
        tracking=True,
        help="Страна на изпращане"
    )

    # Опаковки
    package_type = fields.Many2one(
        'l10n.bg.customs.nomenclature',
        string='Package Type',
        domain=[('type', '=', 'packaging')],
        tracking=True,
        help="Type of packaging according to UN/ECE"
    )
    package_count = fields.Integer(
        string='Number of Packages',
        tracking=True,
        help="Number of packages"
    )
    package_description = fields.Text(
        string='Package Description',
        help="Description of the packaging"
    )

    # Митнически режим
    customs_procedure = fields.Many2one(
        'l10n.bg.customs.nomenclature',
        string='Customs Procedure',
        domain=[('type', '=', 'procedure')],
        tracking=True,
        help="Customs procedure according to UN/ECE"
    )

    # Митнически документи
    customs_documents = fields.Many2many(
        'l10n.bg.customs.nomenclature',
        'customs_declaration_documents_rel',
        'customs_id',
        'document_id',
        string='Customs Documents',
        domain=[('type', '=', 'document')],
        tracking=True,
        help="Related customs documents"
    )

    # Транспортна информация
    transport_mode = fields.Many2one(
        'l10n.bg.customs.nomenclature',
        string='Mode of Transport',
        domain=[('type', '=', 'transport')],
        tracking=True,
        help="Type of transport according to UNECE Rec.19"
    )

    # Отговорно лице
    responsible_id = fields.Many2one(
        'res.users',
        string='Responsible',
        default=lambda self: self.env.user,
        tracking=True
    )

    # Валута
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='company_id.currency_id'
    )
    l10n_bg_customs_currency_id = fields.Many2one(
        'res.currency',
        string="Customs Currency",
        related='company_id.currency_id'
    )

    # Обобщени полета
    total_customs_value = fields.Monetary(
        string='Total Customs Value',
        compute='_compute_customs_totals',
        store=True,
        currency_field='currency_id'
    )
    total_expenses = fields.Monetary(
        string='Total Additional Expenses',
        compute='_compute_customs_totals',
        store=True,
        currency_field='currency_id'
    )
    total_gross_weight = fields.Float(
        string='Total Gross Weight (kg)',
        compute='_compute_customs_totals',
        store=True
    )

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------

    @api.constrains('container_number')
    def _check_container_format(self):
        """Проверка на формата на контейнер номер"""
        for record in self:
            if record.container_number:
                # ISO 6346 формат: 4 букви (owner code) + 7 цифри
                if not re.match(r'^[A-Z]{4}[0-9]{7}$', record.container_number):
                    raise ValidationError(
                        _('Invalid Container Number format. Expected: 4 letters + 7 digits\n'
                          'Example: MSCU1234567')
                    )

    _sql_constraints = [
        ('mrn_unique', 'unique(mrn, company_id)',
         'MRN (Movement Reference Number) must be unique per company!'),
    ]

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends('invoice_line_ids', 'invoice_line_ids.l10n_bg_customs_value',
                 'invoice_line_ids.l10n_bg_is_customs_expense',
                 'invoice_line_ids.l10n_bg_weight_gross')
    def _compute_customs_totals(self):
        for move in self:
            lines = move.invoice_line_ids
            move.total_customs_value = sum(
                lines.filtered(lambda l: not l.l10n_bg_is_customs_expense).mapped('l10n_bg_customs_value')
            )
            move.total_expenses = sum(
                lines.filtered(lambda l: l.l10n_bg_is_customs_expense).mapped('price_total')
            )
            move.total_gross_weight = sum(lines.mapped('l10n_bg_weight_gross'))

    # COMPUTE METHODS за sequence
    @api.depends('l10n_bg_customs_move_id.posted_before', 'l10n_bg_customs_move_id.state',
                 'l10n_bg_customs_date_creation')
    def _compute_l10n_bg_customs_name(self):
        self = self.sorted(lambda m: (m.date, m.ref or '', m._origin.id))

        for record in self:
            if not record._origin or not record._origin.id:
                continue
            if record.l10n_bg_customs_move_id.state == 'cancel':
                continue

            move_has_l10n_bg_customs_name = record.l10n_bg_customs_name and record.l10n_bg_customs_name != '/'
            if not record.l10n_bg_customs_move_id.posted_before:
                record.l10n_bg_customs_name = False
                continue
            if (record.l10n_bg_customs_date_creation and not move_has_l10n_bg_customs_name
                and record.l10n_bg_customs_move_id.state != 'draft'):
                record._set_next_sequence()
        self._inverse_l10n_bg_customs_name()

    def _inverse_l10n_bg_customs_name(self):
        self._set_next_made_sequence_gap(False)

    @api.depends('date')
    def _compute_l10n_bg_customs_highest_name(self):
        for record in self:
            record.l10n_bg_customs_highest_name = record._get_last_sequence()

    @api.depends('l10n_bg_customs_move_id.l10n_bg_date', 'l10n_bg_customs_name',
                 'posted_before', 'sequence_number', 'sequence_prefix', 'state')
    def _compute_l10n_bg_customs_name_placeholder(self):
        for record in self:
            if (
                not record.l10n_bg_customs_name or record.l10n_bg_customs_name == '/') and not record._get_last_sequence():
                sequence_format_string, sequence_format_values = record._get_sequence_format_param(
                    record._get_starting_sequence())
                sequence_format_values['seq'] = sequence_format_values['seq'] + 1
                record.l10n_bg_customs_name_placeholder = sequence_format_string.format(**sequence_format_values)
            else:
                record.l10n_bg_customs_name_placeholder = False

    @api.onchange('mrn')
    def _onchange_mrn_format(self):
        """Автоматично форматиране на MRN към главни букви"""
        if self.mrn:
            self.mrn = self.mrn.upper().replace(' ', '').replace('-', '')

    @api.onchange('container_number')
    def _onchange_container_format(self):
        """Автоматично форматиране на Container Number"""
        if self.container_number:
            self.container_number = self.container_number.upper().replace(' ', '').replace('-', '')

    @api.onchange('lrn')
    def _onchange_lrn_format(self):
        """Автоматично форматиране на LRN към главни букви"""
        if self.lrn:
            self.lrn = self.lrn.upper().strip()

    @api.onchange('transit_declaration_number')
    def _onchange_transit_format(self):
        """Автоматично форматиране на Transit Declaration Number"""
        if self.transit_declaration_number:
            self.transit_declaration_number = self.transit_declaration_number.upper().strip()

    @api.onchange('declaration_number')
    def _onchange_declaration_number(self):
        """Синхронизиране на вътрешния номер с l10n_bg_name_value"""
        if self.l10n_bg_customs_move_id:
            self.l10n_bg_customs_move_id.l10n_bg_name_value = self.declaration_number or False

    @api.onchange('declaration_date')
    def _onchange_declaration_date(self):
        """Синхронизиране на датата на декларацията с l10n_bg_date"""
        if self.l10n_bg_customs_move_id:
            self.l10n_bg_customs_move_id.l10n_bg_date = self.declaration_date or False

    # SEQUENCE MIXIN методи
    def _get_last_sequence_domain(self, relaxed=False):
        self.ensure_one()
        where_string = "WHERE l10n_bg_customs_name != '/'"
        param = {}
        if not relaxed:
            param['anti_regex'] = self._make_regex_non_capturing(self._sequence_yearly_regex.split('(?P<seq>')[0]) + '$'
        return where_string, param

    def _get_starting_sequence(self):
        self.ensure_one()
        return "0" * 10

    def _get_last_sequence(self, relaxed=False, with_prefix=None):
        res = super()._get_last_sequence(relaxed=relaxed, with_prefix=with_prefix)
        padded_number = res.replace(with_prefix, '') if with_prefix else res
        res = with_prefix + padded_number[len(with_prefix):] if with_prefix else padded_number
        return res

    def _set_next_made_sequence_gap(self, made_gap: bool):
        """Update the field made_sequence_gap on the next moves of the current ones.

        Either:
        - we changed something related to the sequence on the current moves, so we need to set the
          sequence as broken on the next moves before updating (made_gap=True)
        - we are filling a gap, so we need to update the next move to remove the flag (made_gap=False)
        """
        next_customs = self.browse()
        named = self.filtered(lambda m: m.l10n_bg_customs_name and m.l10n_bg_customs_name != '/')
        for prefix, customs in named.grouped(lambda move: move.sequence_prefix).items():
            next_customs += self.env['account.move.bg.customs'].sudo().search([
                ('sequence_prefix', '=', prefix),
                ('sequence_number', 'in', [move.sequence_number + 1 for move in customs]),
            ])
        next_customs.made_sequence_gap = made_gap

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            if name_node := arch.xpath(
                """//field[@name="l10n_bg_customs_name"][@invisible="l10n_bg_customs_name == '/' and not posted_before and not quick_edit_mode"]"""):
                name_node[0].set('invisible',
                                 "not (l10n_bg_customs_name or l10n_bg_customs_name_placeholder or quick_edit_mode)")
            if draft_node := arch.xpath(
                """//span[@invisible="l10n_bg_customs_name == '/' and not posted_before and not quick_edit_mode"]"""):
                draft_node[0].set('invisible',
                                  "l10n_bg_customs_name or l10n_bg_customs_name_placeholder or quick_edit_mode")
        return arch, view

    # -------------------------------------------------------------------------
    # Actions buttons
    # -------------------------------------------------------------------------
    def action_post(self):
        res = self.l10n_bg_customs_move_id.action_post()
        if not res:
            # Инвалидизираме кеша
            self.invalidate_recordset()
            # Презареждаме записа от базата данни
            self.env.cache.invalidate()
            return {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return res

    def button_cancel(self):
        return self.l10n_bg_customs_move_id.button_cancel()

    def button_draft(self):
        return self.l10n_bg_customs_move_id.button_draft()

    def action_open_business_doc(self):
        self.ensure_one()
        return {
            'name': _("Vendor Bill"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'res_model': 'account.move',
            'res_id': self.l10n_bg_customs_move_id.id,
            'target': 'current',
        }
