# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import models
from .mt940 import MT940Parser as Parser

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    """Add parsing of mt940 files to bank statement import."""
    _inherit = 'account.bank.statement.import'

    def _parse_file(self, data_file):
        """Parse a MT940 IBAN UNICREDIT file."""
        parser = Parser()
        try:
            _logger.debug("Try parsing with MT940 IBAN UNIGREDIT (%s)." % parser)
            return parser.parse(data_file)
        except ValueError:
            # Returning super will call next candidate:
            _logger.debug("Statement file was not a MT940 IBAN UNICREDIT file.",
                          exc_info=True)
            return super(AccountBankStatementImport, self)._parse_file(
                data_file)
