# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math
from . import num2words_bg

from odoo import models, api, tools, fields, _

import logging

_logger = logging.getLogger(__name__)


class Currency(models.Model):
    _inherit = "res.currency"

    # rate_buy = fields.Float(compute='_compute_current_rate_extra', string='Current Buy Rate', digits=(12, 6),
    #                    help='The rate of the currency to the currency of rate 1.')
    # rate_sell = fields.Float(compute='_compute_current_rate_extra', string='Current Sell Rate', digits=(12, 6),
    #                    help='The rate of the currency to the currency of rate 1.')
    # rate_statistics = fields.Float(compute='_compute_current_rate_extra', string='Current Statistics Rate', digits=(12, 6),
    #                    help='The rate of the currency to the currency of rate 1.')

    # @api.multi
    # def _compute_current_rate_extra(self):
    #    date = self._context.get('date') or fields.Date.today()
    #    company_id = self._context.get('company_id') or self.env['res.users']._get_company().id
    #    # the subquery selects the last rate before 'date' for the given currency/company
    #    query = """SELECT c.id, (SELECT r.rate_buy, r.rate_sell, r.rate_statistics FROM res_currency_rate r
    #                              WHERE r.currency_id = c.id AND r.name <= %s
    #                                AND (r.company_id IS NULL OR r.company_id = %s)
    #                           ORDER BY r.company_id, r.name DESC
    #                              LIMIT 1) AS rate
    #               FROM res_currency c
    #               WHERE c.id IN %s"""
    #    self._cr.execute(query, (date, company_id, tuple(self.ids)))
    #    currency_rates = dict(self._cr.fetchall())
    #    for currency in self:
    #        currency.rate_buy = currency_rates.get(currency.id)[0] or 1.0
    #        currency.rate_sell = currency_rates.get(currency.id)[1] or 1.0
    #        currency.rate_statistics = currency_rates.get(currency.id)[2] or 1.0

    def _amount_to_text(self, amount):
        return self.decimal_places

    @api.multi
    def amount_to_text(self, amount):
        lang_code = self.env.context.get('lang') or self.env.user.lang
        lang = self.env['res.lang'].search([('code', '=', lang_code)])
        #_logger.info("AMAUNT %s" % lang_code)
        if lang.code != 'bg_BG':
            return super(Currency, self).amount_to_text(amount)

        self.ensure_one()
        decimal_places = self._amount_to_text()
        fractional_value, integer_value = math.modf(amount)
        fractional_amount = round(abs(fractional_value), decimal_places) * (math.pow(10, decimal_places))
        amount_words = tools.ustr('{amt_value}').format(
            amt_value=num2words_bg._num2words(integer_value,
                                              currency_label=self.currency_unit_label)
        )
        if not self.is_zero(fractional_value):
            amount_words = tools.ustr('{amt_value}').format(
                amt_value=num2words_bg._num2words(int(fractional_amount), big_val=amount_words,
                                                  currency_label=self.currency_subunit_label)
            )
        return amount_words

# class CurrencyRate(models.Model):
#    _inherit = "res.currency.rate"

#    rate_buy = fields.Float(digits=(12, 6), help='The Buy rate of the currency to the currency of rate 1')
#    rate_sell = fields.Float(digits=(12, 6), help='The Sale rate of the currency to the currency of rate 1')
#    rate_statistics = fields.Float(digits=(12, 6), help='The Statistics rate of the currency to the currency of rate 1')
