#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class CurrencyRate(models.Model):
    _inherit = "res.currency.rate"

    rate_vat = fields.Float(
        group_operator="avg",
        help="The rate of the currency to the currency of rate 1",
        string="Technical Statistics Rate",
    )


class ResCurrency(models.Model):
    _inherit = "res.currency"

    def _get_vat_rates(self, company, date):
        if not self.ids:
            return {}
        self.env["res.currency.rate"].flush_model(
            ["rate", "currency_id", "company_id", "name"]
        )
        query = """SELECT c.id,
                          COALESCE((SELECT r.rate_vat FROM res_currency_rate r
                                  WHERE r.currency_id = c.id AND r.rate_vat IS NOT NULL AND r.name <= %s
                                    AND (r.company_id IS NULL OR r.company_id = %s)
                               ORDER BY r.company_id, r.name DESC
                                  LIMIT 1), 1.0) AS rate
                   FROM res_currency c
                   WHERE c.id IN %s"""
        self._cr.execute(query, (date, company.id, tuple(self.ids)))
        currency_rates = dict(self._cr.fetchall())
        return currency_rates

    def _get_rates(self, company, date):
        if self._context.get("statistic_rate", False):
            return self._get_vat_rates(company, date)
        else:
            return super()._get_rates(company, date)
