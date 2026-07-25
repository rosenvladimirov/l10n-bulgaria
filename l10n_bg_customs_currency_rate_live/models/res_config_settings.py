# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _update_currency_rate(self, currency_data, append=True):
        res = super()._update_currency_rate(currency_data, append=append)
        if len(currency_data['currency_rate']) > 2 and isinstance(currency_data['currency_rate'][2], dict):
            res.update(currency_data['currency_rate'][2])
        return res

    def _parse_bnb_data(self, available_currencies):
        res =  super()._parse_bnb_data(available_currencies)
        # fix for custom statistics currency rate
        url = 'https://customs.bg/wps/portal/agency/home/info-business/bank-information/customs-exchange-rates/customs-exchange-rates'
        html = requests.get(url).content
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', {'class': 'MsoNormalTable'})
        current_date = fields.Datetime.now().date()
        rows = []
        header = []
        for i, row in enumerate(table.find_all('tr')):
            td = [value.text.strip() for value in row.find_all('td')]
            if i == 0:
                header.append(td)
            elif i > 2:
                rows.append(td)
        date_start = header[0][0].split('от')[1].split('до')[0].strip()
        date_end = header[0][0].split('до')[1].strip()
        date_start = datetime.strptime(date_start, '%d.%m.%Y г.').date()
        date_end = datetime.strptime(date_end, '%d.%m.%Y г.').date()
        if date_start >= current_date <= date_end:
            for row in rows[0]:
                if res.get(row[1]):
                    res[row[1]] = res[row[1]] + ({'rate_vat': (1.0/float(row[3].replace(',', '.')))*float(row[2])},)
        return res
