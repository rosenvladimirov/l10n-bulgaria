# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

class ResCompany(models.Model):
    _inherit = 'res.company'

    def _update_currency_rate(self, currency_data, append=True):
        # this fix is not very cleve, but basic conceptions are wrong,
        # need to use dictionary with field and value for rate and date,
        # not a tuple with date and rate
        rate_value = currency_data['rate_data'][0] / currency_data['rate_info'][0]

        if append:
            return {
                'currency_id': currency_data['currency_id'],
                'rate': rate_value,
                'name': currency_data['rate_data'][1],
                'company_id': currency_data['company_id'],
            }
        else:
            return {
                'rate': rate_value,
            }

    def _generate_currency_rates(self, parsed_data):
        """ Generate the currency rate entries for each of the companies, using the
        result of a parsing function, given as parameter, to get the rates data.

        This function ensures the currency rates of each company are computed,
        based on parsed_data, so that the currency of this company receives rate=1.
        This is done so because a lot of users find it convenient to have the
        exchange rate of their main currency equal to one in Odoo.
        """
        Currency = self.env['res.currency']
        CurrencyRate = self.env['res.currency.rate']

        for company in self:
            rate_info = parsed_data.get(company.currency_id.name, None)

            if not rate_info:
                msg = _("Your main currency (%s) is not supported by this exchange rate provider. Please choose another one.", company.currency_id.name)
                if self._context.get('suppress_errors'):
                    _logger.warning(msg)
                    continue
                else:
                    raise UserError(msg)

            for currency, rate_data in parsed_data.items():
                currency_object = Currency.search([('name', '=', currency)])
                if currency_object:  # if rate provider base currency is not active, it will be present in parsed_data
                    already_existing_rate = CurrencyRate.search([('currency_id', '=', currency_object.id), ('name', '=', rate_data[1]), ('company_id', '=', company.id)])
                    if already_existing_rate:
                        already_existing_rate.rate = self._update_currency_rate({
                            'rate_info': rate_info,
                            'rate_data': rate_data,
                        })
                    else:
                        CurrencyRate.create(self._update_currency_rate({
                            'currency_id': currency_object.id,
                            'rate_info': rate_info,
                            'rate_data': rate_data,
                            'company_id': company.id,
                        }))
