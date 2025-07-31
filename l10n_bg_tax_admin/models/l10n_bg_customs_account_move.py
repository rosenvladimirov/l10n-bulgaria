#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models

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

    # Митнически данни
    declaration_number = fields.Char(
        string='Declaration Number',
        tracking=True
    )
    declaration_date = fields.Date(
        string='Declaration Date',
        tracking=True
    )

    # Инкотермс
    incoterm_location = fields.Char(
        string='Incoterm Location',
        help="Място на доставка според Инкотермс"
    )

    # Държави
    country_of_origin_id = fields.Many2one(
        'res.country',
        string='Country of Origin',
        tracking=True,
        help="Страна на произход на стоките"
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
        help="Вид на опаковката според UN/ECE"
    )
    package_count = fields.Integer(
        string='Number of Packages',
        tracking=True,
        help="Брой опаковки"
    )
    package_description = fields.Text(
        string='Package Description',
        help="Описание на опаковките"
    )

    # Митнически режим
    customs_procedure = fields.Many2one(
        'l10n.bg.customs.nomenclature',
        string='Customs Procedure',
        domain=[('type', '=', 'procedure')],
        tracking=True,
        help="Митнически режим"
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
        help="Свързани митнически документи"
    )

    # Транспортна информация
    transport_mode = fields.Many2one(
        'l10n.bg.customs.nomenclature',
        string='Mode of Transport',
        domain=[('type', '=', 'transport')],
        tracking=True,
        help="Вид на транспорта според UNECE Rec.19"
    )

    # Отговорно лице
    responsible_id = fields.Many2one(
        'res.users',
        string='Responsible',
        default=lambda self: self.env.user,
        tracking=True
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

    # Изчисляеми функции
    @api.depends('total_customs_value', 'total_expenses')
    def _compute_vat_amount(self):
        for record in self:
            taxable_amount = record.total_customs_value + record.total_expenses
            record.vat_amount = taxable_amount * 0.20  # 20% ДДС

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
                 'l10n_bg_customs_move_id.l10n_bg_customs_date')
    def _compute_l10n_bg_customs_name(self):
        self = self.sorted(lambda m: (m.date, m.ref or '', m._origin.id))

        for record in self:
            if record.l10n_bg_customs_move_id.state == 'cancel':
                continue

            move_has_l10n_bg_customs_name = record.l10n_bg_customs_name and record.l10n_bg_customs_name != '/'
            if not record.l10n_bg_customs_move_id.posted_before:
                record.l10n_bg_customs_name = False
                continue
            if (record.l10n_bg_customs_move_id.l10n_bg_customs_date and not move_has_l10n_bg_customs_name
                and record.l10n_bg_customs_move_id.state != 'draft'):
                record._set_next_sequence()
        self._inverse_l10n_bg_customs_name()

    def _inverse_l10n_bg_customs_name(self):
        self._set_next_made_sequence_gap(False)

    @api.depends('date')
    def _compute_l10n_bg_customs_highest_name(self):
        for record in self:
            record.l10n_bg_customs_highest_name = record._get_last_sequence()

    @api.depends('l10n_bg_customs_move_id.l10n_bg_customs_date', 'l10n_bg_customs_name',
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
        next_customs = self.browse()
        named = self.filtered(lambda m: m.l10n_bg_customs_name and m.l10n_bg_customs_name != '/')
        for prefix, privates in named.grouped(lambda move: move.sequence_prefix).items():
            next_customs += self.env['account.move'].sudo().search([
                ('sequence_prefix', '=', prefix),
                ('sequence_number', 'in', [move.sequence_number + 1 for move in next_customs]),
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
