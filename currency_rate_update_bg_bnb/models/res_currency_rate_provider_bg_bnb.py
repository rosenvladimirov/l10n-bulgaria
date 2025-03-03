#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
import logging

import requests
from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResCurrencyRateProviderBGBNB(models.Model):
    _inherit = "res.currency.rate.provider"

    service = fields.Selection(
        selection_add=[("BG_BNB", "National Bank of Bulgaria")],
        ondelete={"BG_BNB": "set default"},
    )

    def _get_supported_currencies(self):
        self.ensure_one()
        if self.service != "BG_BNB":
            return super()._get_supported_currencies()  # pragma: no cover
        return [
            "AUD",
            "BRL",
            "CAD",
            "CHF",
            "CNY",
            "CZK",
            "DKK",
            "EUR",
            "GBP",
            "BGN",
            "HKD",
            "HRK",
            "HUF",
            "IDR",
            "ILS",
            "INR",
            "JPY",
            "KRW",
            "LTL",
            "MXN",
            "MYR",
            "NOK",
            "NZD",
            "PHP",
            "PLN",
            "RON",
            "RUB",
            "SEK",
            "SGD",
            "THB",
            "TRY",
            "USD",
            "ZAR",
        ]

    @api.model
    def _obtain_rates(self, base_currency, currencies, date_from, date_to):
        self.ensure_one()

        def rate_retrieve(bnb_dom):
            res = {
                "EUR": {
                    "rate_currency": 1.95583,
                    "inverted": 1.95583,
                    "direct": 0.511292,
                }
            }
            # curr_rate = dom.xpath("//ROW/REVERSERATE")
            # direct_rate = dom.xpath("//ROW/RATE")
            # gold = dom.xpath("//ROW/GOLD")
            rows = []
            for curr_name in bnb_dom.xpath("//ROW"):
                rows.append(
                    {
                        "GOLD": -1,
                        "NAME_": None,
                        "CODE": None,
                        "RATIO": 1.0,
                        "REVERSERATE": 0.0,
                        "RATE": 0.0,
                        "EXTRAINFO": None,
                        "CURR_DATE": None,
                        "TITLE": None,
                        "F_STAR": None,
                    }
                )
                for el in curr_name.iter():
                    rows[-1][el.tag] = el.text
            for line in rows:
                if line["GOLD"] == 0:
                    continue
                if line["GOLD"] == "1" and line["F_STAR"] != 1:
                    res[line["CODE"]] = {
                        "rate_currency": float(line["REVERSERATE"])
                        * float(line["RATIO"]),
                        "inverted": float(line["RATE"]) / float(line["RATIO"]),
                        "direct": float(line["REVERSERATE"]) * float(line["RATIO"]),
                    }
            return res

        if self.service == "BG_BNB":
            if base_currency != "BGN":
                raise UserError(
                    _(
                        "Bulgarian Central Bank is suitable only for companies"
                        " with BGN as base currency!"
                    )
                )

            bnb_url = "https://www.bnb.bg/Statistics/StExternalSector/StExchangeRates/StERForeignCurrencies/index.htm"
            bnb_params = {"download": "xml"}
            supported_currencies = self._get_supported_currencies()
            data = {}
            _logger.info("Bulgarian National Bank")

            try:
                raw_file = requests.get(bnb_url, params=bnb_params, timeout=120)
            except OSError:
                raise UserError(_("Web Service does not exist (%s)!") % bnb_url)

            dom = etree.fromstring(raw_file.content)
            # 16.11.2023
            rate_date = dom.xpath("//ROW/TITLE")[0].text[-10:]
            rate_date = datetime.datetime.strptime(rate_date, "%d.%m.%Y")
            rate_date = rate_date.strftime("%Y-%m-%d")

            gold = dom.xpath("//ROW/GOLD")
            for item, curr_name in enumerate(dom.xpath("//ROW/CODE")):
                if gold[item].text == "1":
                    supported_currencies.append(curr_name.text)

            curr_data = rate_retrieve(dom)

            _logger.debug("Returned currency rate %s" % curr_data)

            for curr in currencies:
                if curr not in supported_currencies:
                    continue

                if not curr_data.get(curr):
                    continue

                if not data.get(rate_date):
                    data[rate_date] = {}
                data[rate_date][curr] = curr_data[curr]

                _logger.debug(
                    f"Rate retrieved : 1 {base_currency} = "
                    f"{curr_data[curr]['rate_currency']} {curr}"
                )
            return data

        return super()._obtain_rates(base_currency, currencies, date_from, date_to)
