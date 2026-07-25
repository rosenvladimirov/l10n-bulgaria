import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['account.bg.calc.purchases.line'].init()
    env['account.bg.calc.sales.line'].init()
