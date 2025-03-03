#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResCurrencyRateProviderBGCUSTOMS(models.Model):
    _inherit = "res.currency.rate.provider"

    service = fields.Selection(
        selection_add=[("BG_CUSTOMS", "Customs Agency of Bulgaria")],
        ondelete={"BG_CUSTOMS": "set default"},
    )

    def _get_supported_currencies(self):
        self.ensure_one()
        if self.service != "BG_CUSTOMS":
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

        if self.service == "BG_CUSTOMS":
            if base_currency != "BGN":
                raise UserError(
                    _(
                        "Customs Agency is suitable only for companies"
                        " with BGN as base currency!"
                    )
                )
            _logger.info("Customs Agency of Bulgaria")
            data = {}
            supported_currencies = self._get_supported_currencies()
            url = "https://customs.bg/wps/portal/agency/home/info-business/bank-information/customs-exchange-rates/customs-exchange-rates"
            html = requests.get(url, timeout=120).content
            soup = BeautifulSoup(html, "html.parser")
            table = soup.find("table", {"class": "MsoNormalTable"})
            current_date = fields.Datetime.now().date()
            rows = []
            header = []
            for i, row in enumerate(table.find_all("tr")):
                td = [value.text.strip() for value in row.find_all("td")]
                if i == 0:
                    header.append(td)
                elif i > 2:
                    rows.append(td)
            date_start = header[0][0].split("от")[1].split("до")[0].strip()
            rate_date = current_date.strftime("%Y-%m-%d")
            date_end = header[0][0].split("до")[1].strip()
            date_start = datetime.strptime(date_start, "%d.%m.%Y г.").date()
            date_end = datetime.strptime(date_end, "%d.%m.%Y г.").date()
            curr_data = dict([[x[1], (x[3], x[2])] for x in rows])
            if date_start >= current_date <= date_end:
                for curr in currencies:
                    if curr not in supported_currencies:
                        continue

                    if not curr_data.get(curr):
                        continue

                    if not data.get(rate_date):
                        data[rate_date] = {}
                    rate = float(curr_data[curr][0].replace(",", "."))
                    ratio = float(curr_data[curr][1])
                    data[rate_date][curr] = {
                        "rate_currency": (1.0 / rate) * ratio,
                        "inverted": rate / ratio,
                        "direct": (1.0 / rate) * ratio,
                    }

                    _logger.debug(
                        f"Rate retrieved : 1 {base_currency} = "
                        f"{float(curr_data[curr][0].replace(',', '.'))} {curr}"
                    )
                return data
        return super()._obtain_rates(base_currency, currencies, date_from, date_to)
