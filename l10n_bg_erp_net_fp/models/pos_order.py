from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PosOrder(models.Model):
    _inherit = 'pos.order'

    # Полета за фискални данни (попълват се от frontend)
    l10n_bg_fiscal_receipt_datetime = fields.Datetime(
        string='Date/Time of fiscal receipt',
        readonly=True,
        help='The time of issuing the fiscal receipt'
    )
    l10n_bg_fiscal_receipt_number = fields.Char(
        string='Fiscal number',
        readonly=True,
        help='Fiscal receipt number from ErpNet.FP'
    )
    l10n_bg_fiscal_memory_number = fields.Char(
        string='Fiscal memory',
        readonly=True,
        help='Fiscal memory serial number'
    )
    l10n_bg_is_fiscalized = fields.Boolean(
        string='Is fiscalized?',
        readonly=True,
        help='Is the order fiscalized?'
    )
    l10n_bg_is_reversal = fields.Boolean(
        string='Is reversal?',
        readonly=True,
        help='Is the order reversal?'
    )
