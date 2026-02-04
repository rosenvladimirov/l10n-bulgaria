import re
import logging
import enum

from odoo import _, api, models

_logger = logging.getLogger(__name__)

class ProCreditCustomerReference(object):
    pattern = r"""(ПОЛУЧАТЕЛ:|СМЕТКА:|BIC:|КУРС:)"""
    split_data = None
    bank_swift_id = "PRCBBGSF"

    def __init__(self, tag_data):
        split_data = re.split(self.pattern, tag_data)
        self.split_data = [x.strip() for x in split_data if x != ""]

    def get_version(self):
        return self.bank_swift_id

    def get_data(self):
        return dict(zip(self.split_data[::2], self.split_data[1::2]))
