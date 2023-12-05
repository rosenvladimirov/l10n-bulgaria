# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
import logging
from odoo import api, fields, models, tools

_logger = logging.getLogger(__name__)


class AccountBGVatLine(models.Model):
    """ Base model for new Bulgarian VAT reports. The idea is that this lines have all the necessary data and which any
    changes in odoo, this ones will be taken for this cube and then no changes will be nedeed in the reports that use
    this lines. A line is created for each accountring entry that is affected by VAT tax.

    Basically which it does is covert the accounting entries into columns depending of the information of the taxes and
    add some other fields """

    _name = 'account.bg.vat.line'
    _description = 'VAT line for Analysis in Bulgarian Localization'
    _auto = False
    _order = 'date asc, move_name asc, id asc'

    DEFAULT_VALUE = 0.00

    date = fields.Date(readonly=True, string='Дата на документа')
    accounting_period = fields.Date(readonly=True, string='[02-01] Данъчен период',
                                    compute='_formatting_period')  # NOT WORK/ No default
    partner_name = fields.Char(readonly=True)
    partner_vat = fields.Char(readonly=True, string='Идентификационен номер на контрагента2',
                              compute='_compute_partner_vat', store=True)
    company_vat = fields.Char(related='company_id.vat', readonly=True, string='ИН по ЗДДС1',
                              compute='_compute_company_vat')
    product_id = fields.Text(string='Вид на стоката/услугата', compute='_compute_product_id', readonly=True)
    document_sequence = fields.Integer(
        string='Пореден номер на документа в дневника',
        readonly=True,
        default=0, )
    move_name = fields.Char(readonly=True)
    move_type = fields.Selection(selection=[
        ('entry', 'Journal Entry'),
        ('out_invoice', 'Customer Invoice'),
        ('out_refund', 'Customer Credit Note'),
        ('in_invoice', 'Vendor Bill'),
        ('in_refund', 'Vendor Credit Note'),
        ('out_receipt', 'Sales Receipt'),
        ('in_receipt', 'Purchase Receipt'),
    ], string='Вид на документа', compute='_compute_move_type', store=True, readonly=True)
    base_20 = fields.Monetary(readonly=True, string='[02-11] ДО-за облагане с 20%', compute='_compute_tag_11',
                              currency_field='company_currency_id')
    vat_20 = fields.Monetary(readonly=True, string='[02-21] ДДС-20%', compute='_compute_vat_values',
                             currency_field='company_currency_id')
    base_9 = fields.Monetary(readonly=True, string='[02-13] ДО-за облагане с 9%', compute='_compute_vat_values',
                             currency_field='company_currency_id')
    vat_9 = fields.Monetary(readonly=True, string='[02-24] ДДС-туристически услуги 9%', compute='_compute_vat_values',
                            currency_field='company_currency_id')
    base_0 = fields.Monetary(readonly=True, currency_field='company_currency_id')
    vat_0 = fields.Monetary(readonly=True, currency_field='company_currency_id')
    not_taxed = fields.Monetary(readonly=True, string='Not taxed/ex',
                                help='Not Taxed / Exempt.\All lines that have VAT 0, Exempt, Not Taxed'' or Not Applicable',
                                currency_field='company_currency_id')
    other_taxes = fields.Monetary(readonly=True, string='Общ размер на ДО3 за облагане с ДДС',
                                  help='All the taxes tat ar not VAT taxes or iibb perceptions and that'' are realted to documents that have VAT',
                                  currency_field='company_currency_id')
    total = fields.Monetary(readonly=True, string='Всичко начислен ДДС', currency_field='company_currency_id')
    state = fields.Selection([('draft', 'Unposted'), ('posted', 'Posted')], 'Status', readonly=True)
    journal_id = fields.Many2one('account.journal', readonly=True, string='Journal', auto_join=True)
    partner_id = fields.Many2one('res.partner', string='Име на контрагента', readonly=True, auto_join=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True, auto_join=True)
    company_currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)
    move_id = fields.Many2one('account.move', string='Номер на документа', auto_join=True)
    branch = fields.Monetary(readonly=True, string='Клон', default=0.00, currency_field='company_currency_id')

    ################ ONLY FOR SALE
    account_tag_11 = fields.Monetary(readonly=True, string='[02-11] ДО-за облагане с 20%', compute='_compute_tags',
                                     currency_field='company_currency_id')
    account_tag_21 = fields.Monetary(readonly=True, string='[02-21] ДДС-20%', compute='_compute_tags',
                                     currency_field='company_currency_id')
    account_tag_12 = fields.Monetary(readonly=True, string='[02-12] ДО-ВОП', default=0.00,
                                     currency_field='company_currency_id')  # TODO
    account_tag_26 = fields.Monetary(readonly=True, string='[02-26] ДО-чл.82, ал.2-5', default=0.00,
                                     currency_field='company_currency_id')  # TODO
    account_tag_22 = fields.Monetary(readonly=True, string='[02-22] ДДС-ДОП и чл.82,ал.2-5', default=0.00,
                                     currency_field='company_currency_id')  # TODO
    account_tag_23 = fields.Monetary(readonly=True, string='[02-23] ДДС-лични нужди', default=0.00,
                                     currency_field='company_currency_id')  # TODO
    account_tag_14 = fields.Monetary(readonly=True, string='[02-14] ДО-износ 0%', compute='_compute_tags', default=0.00,
                                     currency_field='company_currency_id')  # TODO
    account_tag_15 = fields.Monetary(readonly=True, string='[02-15] ДО-ВОД на стоки 0%', compute='_compute_tags',
                                     default=0.00, currency_field='company_currency_id')  # TODO
    account_tag_16 = fields.Monetary(readonly=True, string='[02-16] ДО-0% по чл.140,ал,1 и чл.173',
                                     compute='_compute_tags', default=0.00,
                                     currency_field='company_currency_id')  # TODO
    account_tag_17 = fields.Monetary(readonly=True, string='[02-17] ДО-по чл.21 на територията на ЕС',
                                     compute='_compute_tags', default=0.00,
                                     currency_field='company_currency_id')  # TODO
    account_tag_18 = fields.Monetary(readonly=True, string='[02-18] ДО-по чл.69,ал.2 на територията на ЕС',
                                     compute='_compute_tags', default=0.00,
                                     currency_field='company_currency_id')  # TODO
    account_tag_19 = fields.Monetary(readonly=True, string='[02-19] ДО-осводени и ВОП', default=0.00,
                                     compute='_compute_tags', currency_field='company_currency_id')  # TODO
    account_tag_24 = fields.Monetary(readonly=True, string='[02-24] ДДС-туристически услуги 9%', default=0.00,
                                     compute='_compute_tags', currency_field='company_currency_id')  # TODO
    account_tag_25 = fields.Monetary(readonly=True, string='[02-25] ДО-тристранни операции', default=0.00,
                                     currency_field='company_currency_id')  # TODO

    ################## ONLY FOR PURCHASE
    account_tag_30 = fields.Monetary(readonly=True, string='[03-30] ДО-без данъчен кредит', compute='_compute_tag_30',
                                     default=0.00, currency_field='company_currency_id')  # TODO
    account_tag_31 = fields.Monetary(readonly=True, string='[03-31] ДО-пълен данъчен кредит', compute='_compute_tag_31',
                                     currency_field='company_currency_id')  # TODO
    account_tag_41 = fields.Monetary(readonly=True, string='[03-41] ДДС-пълен данъчен кредит',
                                     compute='_compute_tag_41', currency_field='company_currency_id')  # TODO
    account_tag_32 = fields.Monetary(readonly=True, string='[03-32] ДО-частичен данъчен кредит',
                                     compute='_compute_tag_32', default=0.00,
                                     currency_field='company_currency_id')  # TODO
    account_tag_42 = fields.Monetary(readonly=True, string='[03-42] ДДС-частичен данъчен кредит',
                                     compute='_compute_tag_42', default=0.00,
                                     currency_field='company_currency_id')  # TODO
    account_tag_43 = fields.Monetary(readonly=True, string='[03-43] Годишна корекция-чл.73,ал.8', default=0.00,
                                     currency_field='company_currency_id')  # TODO
    account_tag_45 = fields.Monetary(readonly=True, string='[03-45] ДО-чл.163а', default=0.00,
                                     currency_field='company_currency_id')  # TODO

    def open_journal_entry(self):
        self.ensure_one()
        return self.move_id.get_formview_action()

    def init(self):
        cr = self._cr
        tools.drop_view_if_exists(cr, self._table)
        # we use tax_ids for base amount instead of tax_base_amount for two reasons:
        # * zero taxes do not create any aml line so we can't get base for them with tax_base_amount
        # * we use same method as in odoo tax report to avoid any possible discrepancy with the computed tax_base_amount
        query, params = self._bg_vat_line_build_query()
        sql = f"""CREATE or REPLACE VIEW account_bg_vat_line as ({query})"""
        cr.execute(sql, params)

    @api.model
    def _bg_vat_line_build_query(self, tables='account_move_line', where_clause='', where_params=None,
                                 column_group_key='', tax_types=('sale', 'purchase')):
        """Returns the SQL Select query fetching account_move_lines info in order to build the pivot view for the VAT summary.
        This method is also meant to be used outside this model, which is the reason why it gives the opportunity to
        provide a few parameters, for which the defaults are used in this model.

        The query is used to build the VAT book report"""
        if where_params is None:
            where_params = []

        query = f"""
                SELECT
                    %s AS column_group_key,
                    account_move.id,
                    account_move.date,
                    rp.name AS partner_name,
                    rp.vat AS partner_vat,
                    COALESCE(nt.type_tax_use, bt.type_tax_use) AS tax_type,
                    account_move.id AS move_id,
                    account_move.move_type AS move_type,
                    account_move.partner_id,
                    account_move.journal_id,
                    account_move.name AS move_name,
                    account_move.state,
                    account_move.company_id,
                    account_move_line.product_id AS product_id,
                    (
                        SELECT COUNT(*)
                        FROM account_move am
                        WHERE
                            am.company_id = account_move.company_id
                            AND am.move_type = account_move.move_type
                            AND am.date <= account_move.date
                    ) AS document_sequence,
                    SUM(CASE WHEN btg.l10n_bg_vat_code in ('0', '1', '2') THEN account_move_line.balance ELSE 0 END) AS taxed,
                    SUM(CASE WHEN btg.l10n_bg_vat_code = '2' THEN account_move_line.balance ELSE 0 END) AS base_20,
                    SUM(CASE WHEN ntg.l10n_bg_vat_code = '2' THEN account_move_line.balance ELSE 0 END) AS vat_20,
                    SUM(CASE WHEN btg.l10n_bg_vat_code = '1' THEN account_move_line.balance ELSE 0 END) AS base_9,
                    SUM(CASE WHEN ntg.l10n_bg_vat_code = '1' THEN account_move_line.balance ELSE 0 END) AS vat_9,
                    SUM(CASE WHEN btg.l10n_bg_vat_code = '0' THEN account_move_line.balance ELSE 0 END) AS base_0,
                    SUM(CASE WHEN ntg.l10n_bg_vat_code = '0' THEN account_move_line.balance ELSE 0 END) AS vat_0,
                    SUM(CASE WHEN btg.l10n_bg_vat_code in ('0', '1', '2') THEN account_move_line.balance ELSE 0 END) AS not_taxed,
                    SUM(CASE WHEN ntg.l10n_bg_vat_code is NULL THEN account_move.amount_untaxed ELSE 0 END) AS other_taxes,
                    SUM(account_move_line.balance) AS total,
                    {self.accounting_period} AS accounting_period,
                    0.00 AS branch,
                    0.00 AS account_tag_11,
                    0.00 AS account_tag_12,
                    0.00 AS account_tag_21,
                    0.00 AS account_tag_26,
                    0.00 AS account_tag_22,
                    0.00 AS account_tag_23,
                    0.00 AS account_tag_14,
                    0.00 AS account_tag_15,
                    0.00 AS account_tag_16,
                    0.00 AS account_tag_17,
                    0.00 AS account_tag_18,
                    0.00 AS account_tag_19,
                    0.00 AS account_tag_24,
                    0.00 AS account_tag_25,
                    0.00 AS account_tag_30,
                    0.00 AS account_tag_31,
                    0.00 AS account_tag_41,
                    0.00 AS account_tag_32,
                    0.00 AS account_tag_42,
                    0.00 AS account_tag_43,
                    0.00 AS account_tag_45
                FROM
                    {tables}
                    JOIN
                        account_move ON account_move_line.move_id = account_move.id
                    LEFT JOIN
                        -- nt = net tax
                        account_tax AS nt ON account_move_line.tax_line_id = nt.id
                    LEFT JOIN
                        account_move_line_account_tax_rel AS amltr ON account_move_line.id = amltr.account_move_line_id
                    LEFT JOIN
                        -- bt = base tax
                        account_tax AS bt ON amltr.account_tax_id = bt.id
                    LEFT JOIN
                        account_tax_group AS btg ON btg.id = bt.tax_group_id
                    LEFT JOIN
                        account_tax_group AS ntg ON ntg.id = nt.tax_group_id
                    LEFT JOIN
                        res_partner AS rp ON rp.id = account_move.commercial_partner_id
                WHERE
                    (account_move_line.tax_line_id is not NULL OR btg.l10n_bg_vat_code is not NULL)
                    AND (nt.type_tax_use in %s OR bt.type_tax_use in %s)
                    {where_clause}
                GROUP BY
                    account_move.id, account_move_line.product_id, rp.id, COALESCE(nt.type_tax_use, bt.type_tax_use)
                ORDER BY
                    account_move.date, account_move.name"""
        return query, [column_group_key, tax_types, tax_types, *where_params]

    #################################### COMPUTE FIELDS

    def _compute_tag_41(self):
        account_tag_41_ids = [38, 39]
        for record in self:
            record.account_tag_41 = 0.0
            for tax_line in record.move_id.line_ids:
                # line = record.move_id.line_ids.filtered(lambda t: t.tax_tag_ids.id in account_tag_41_id)
                for tax_line_id in tax_line:
                    if tax_line_id.id in account_tag_41_ids:
                        record.account_tag_41 += tax_line.balance
            self._check_balance_value(record.account_tag_41)

    def _compute_tag_31(self):
        account_tag_31_id = [34, 35]
        for record in self:
            line = record.move_id.line_ids.filtered(lambda t: t.tax_tag_ids.id in account_tag_31_id)
            record.account_tag_31 = sum(l.balance for l in line)

            self._check_balance_value(record.account_tag_31)

    def _compute_tag_42(self):
        account_tag_42_id = [40, 42]
        for record in self:
            line = record.move_id.line_ids.filtered(lambda t: t.tax_tag_ids.id in account_tag_42_id)
            record.account_tag_42 = sum(l.balance for l in line)

            self._check_balance_value(record.account_tag_42)

    def _compute_tag_32(self):
        account_tag_32_id = [36, 37]
        for record in self:
            line = record.move_id.line_ids.filtered(lambda t: t.tax_tag_ids.id in account_tag_32_id)
            record.account_tag_32 = sum(l.balance for l in line)

            self._check_balance_value(record.account_tag_32)

    def _compute_tag_30(self):
        account_tag_30_id = [32, 33]
        for record in self:
            line = record.move_id.line_ids.filtered(lambda t: t.tax_tag_ids.id in account_tag_30_id)
            record.account_tag_30 = sum(l.balance for l in line)

            self._check_balance_value(record.account_tag_30)

    def _check_balance_value(self, value):
        if not value:
            value = self.DEFAULT_VALUE

    # Compute the values for multiple account tags by calling _compute_tag for each tag with its field name and tag IDs.
    def _compute_tags(self):
        self._compute_tag('account_tag_11', [4, 5])
        self._compute_tag('account_tag_21', [24, 25])
        self._compute_tag('account_tag_14', [12, 13])
        self._compute_tag('account_tag_15', [14, 15])
        self._compute_tag('account_tag_16', [16, 17])
        self._compute_tag('account_tag_17', [18, 19])
        self._compute_tag('account_tag_18', [20, 21])
        self._compute_tag('account_tag_19', [23, 22])
        self._compute_tag('account_tag_23', [28, 29])
        self._compute_tag('account_tag_24', [30, 31])

    # Compute the total balance for a specific account tag by iterating through records, filtering relevant lines, and setting the balance to the corresponding field name.
    def _compute_tag(self, field_name, tag_ids):
        for record in self:
            # Filter lines based on tag IDs.
            lines = record.move_id.line_ids.filtered(lambda t: t.tax_tag_ids.id in tag_ids)
            # Calculate the total balance for these lines.
            total_balance = sum(line.balance for line in lines)
            # Set the total balance as an attribute of the record with the specified field name.
            setattr(record, field_name, total_balance)
            # Ensure that the balance value is valid and handle cases where it's missing or zero.
            self._check_balance_values(field_name, total_balance)

    # Check the balance value and set it to 0.00 if it's not present (e.g., None or 0).
    def _check_balance_values(self, field_name, value):
        # If the value is missing or zero, set it to 0.00.
        if not value:
            setattr(self, field_name, 0.00)

    @api.depends('partner_id.vat')
    def _compute_partner_vat(self):
        # Returns the partner's VAT from the related partner
        for record in self:
            record.partner_vat = record.partner_id.vat

    @api.depends('product_id')
    def _compute_product_id(self):
        # Returns the product name
        for record in self:
            if record.move_type in ['out_invoice', 'out_refund']:
                record.product_id = 'Продажба на стоки и услуги'
            elif record.move_type in ['in_invoice', 'in_refund']:
                record.product_id = 'Покупка на стоки и услуги'

    @api.depends('move_id.line_ids')
    def _compute_vat_values(self):
        """
        Compute VAT-related fields based on invoice lines and taxes.

        This method is a decorator for Odoo's computed field mechanism. It calculates
        VAT-related fields such as 'base_20', 'vat_20', 'base_9', and 'vat_9' based on the
        invoice lines and associated tax groups. It iterates through the invoice lines and
        calculates these fields depending on the tax group of each line. If a tax group is identified
        as 'VAT 20%', it sets the 'base_20' and 'vat_20' fields accordingly. If a tax group is identified
        as 'VAT 9%', it sets the 'base_9' and 'vat_9' fields accordingly.

        :param max_len: The maximum length for formatted monetary fields (default is 15 characters).
        :type max_len: int
        """
        vat_id_20 = 2
        vat_id_9 = 3
        for record in self:
            # Initialize the flags as False
            record.base_20 = False
            record.vat_20 = False
            record.base_9 = False
            record.vat_9 = False

            # Iterate through the invoice lines
            for tax_line in record.move_id.line_ids.filtered(lambda line: line.tax_ids):
                for tax in tax_line.tax_ids:
                    if tax.tax_group_id.id == vat_id_20:
                        # Set VAT 20% values
                        record.base_20 = record.other_taxes
                        record.vat_20 = record.total
                    elif tax.tax_group_id.id == vat_id_9:
                        # Set VAT 9% values
                        record.base_9 = record.other_taxes
                        record.vat_9 = record.total

    @api.constrains('accounting_period')
    def _formatting_period(self):
        # Returns formatting date
        for record in self:
            record.accounting_period = record.date.strftime('%Y-%m-%d')

    # def _compute_tag_11(self):
    #     account_tag_11_id = [4, 5]         
    #     for record in self:

    #         line =  record.move_id.line_ids.filtered(lambda t: t.tax_tag_ids.id in account_tag_11_id)
    #         record.account_tag_11 = sum(l.balance for l in line)

    #         self._check_balance_value(record.account_tag_11)

    # def _compute_tag_21(self):
    #     account_tag_21_id = [24, 25]         
    #     for record in self:

    #         line =  record.move_id.line_ids.filtered(lambda t: t.tax_tag_ids.id in account_tag_21_id)
    #         record.account_tag_21 = sum(l.balance for l in line)

    #         self._check_balance_value(record.account_tag_21)

    # def _compute_tag_13(self):
    #     account_tag_id_13 = [10, 11]         
    #     for record in self:

    #         line =  record.move_id.line_ids.filtered(lambda t: t.tax_tag_ids.id in account_tag_id_13)
    #         record.account_tag_13 = sum(l.balance for l in line)

    #         self._check_balance_value(record.account_tag_13)

    # def _compute_tag_14(self):
    #     account_tag_id_14 = [12, 13]         
    #     for record in self:

    #         line =  record.move_id.line_ids.filtered(lambda t: t.tax_tag_ids.id in account_tag_id_14)
    #         record.account_tag_14 = sum(l.balance for l in line)

    #         self._check_balance_value(record.account_tag_14)

    # def _compute_tag_15(self):
    #     account_tag_15_id = [14, 15]    
    #     for record in self:

    #         line =  record.move_id.line_ids.filtered(lambda t: t.tax_tag_ids.id in account_tag_15_id)
    #         record.account_tag_15 = sum(l.balance for l in line)

    #         self._check_balance_value(record.account_tag_15)

    # def _compute_tag_16(self):
    #     account_tag_16_id = [16, 17]         
    #     for record in self:

    #         line =  record.move_id.line_ids.filtered(lambda t: t.tax_tag_ids.id in account_tag_16_id)
    #         record.account_tag_16 = sum(l.balance for l in line)

    #         self._check_balance_value(record.account_tag_16)

    # def _compute_tag_17(self):
    #     account_tag_17_id = [18, 19]         
    #     for record in self:

    #         line =  record.move_id.line_ids.filtered(lambda t: t.tax_tag_ids.id in account_tag_17_id)
    #         record.account_tag_17 = sum(l.balance for l in line)

    #         self._check_balance_value(record.account_tag_17)

    # def _compute_tag_18(self):
    #     account_tag_18_id = [20, 21]         
    #     for record in self:

    #         line =  record.move_id.line_ids.filtered(lambda t: t.tax_tag_ids.id in account_tag_18_id)
    #         record.account_tag_18 = sum(l.balance for l in line)

    #         self._check_balance_value(record.account_tag_18)

    # def _compute_tag_19(self):
    #     account_tag_19_id = [23, 22]         
    #     for record in self:

    #         line =  record.move_id.line_ids.filtered(lambda t: t.tax_tag_ids.id in account_tag_19_id)
    #         record.account_tag_19 = sum(l.balance for l in line)

    #         self._check_balance_value(record.account_tag_19)

    # def _compute_tag_23(self):
    #     account_tag_23_id = [28, 29]         
    #     for record in self:

    #         line =  record.move_id.line_ids.filtered(lambda t: t.tax_tag_ids.id in account_tag_23_id)
    #         record.account_tag_23 = sum(l.balance for l in line)

    #         self._check_balance_value(record.account_tag_23)

    # def _compute_tag_24(self):
    #     account_tag_id_24 = [30, 31]         
    #     for record in self:

    #         line =  record.move_id.line_ids.filtered(lambda t: t.tax_tag_ids.id in account_tag_id_24)
    #         record.account_tag_24 = sum(l.balance for l in line)

    #         self._check_balance_value(record.account_tag_24)
