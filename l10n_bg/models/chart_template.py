# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields, _


class AccountTaxTemplate(models.Model):
    _inherit = 'account.tax.template'

    def _get_tax_vals(self, company, tax_template_to_tax):
        val = super(AccountTaxTemplate, self)._get_tax_vals(company, tax_template_to_tax)
        val.update(dict(tax_credit_payable=self.tax_credit_payable,
                        separate=self.separate,
                        contrapart_account_id=self.contrapart_account_id))
        return val


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    @api.multi
    def create_record_with_xmlid(self, company, template, model, vals):
        if model == 'account.fiscal.position':
            vals['type_docs'] = template.type_docs
        return super(AccountChartTemplate, self).create_record_with_xmlid(company, template, model, vals)


class AccountFiscalPositionTemplate(models.Model):
    _inherit = 'account.fiscal.position.template'

    type_docs = fields.Selection([('standart', 'Standart for invoices'),
                                  ('ticket', 'B2C Invoices'),
                                  ('customs', 'Customs declaration'),
                                  ('protocol', 'Swap incoming invoices with a protocol')], string="Types of docs",
                                 default='standart')
