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
        help='Номер на фискалния бон от ErpNet.FP'
    )
    l10n_bg_fiscal_memory_number = fields.Char(
        string='Фискална памет',
        readonly=True,
        help='Сериен номер на фискалната памет'
    )

    @api.model
    def _order_fields(self, ui_order):
        """Добавяне на фискални полета при синхронизация от POS"""
        order_fields = super()._order_fields(ui_order)

        # Добавяме фискалните данни ако са налични от frontend
        if ui_order.get('l10n_bg_fiscal_receipt_number'):
            order_fields['l10n_bg_fiscal_receipt_number'] = ui_order['l10n_bg_fiscal_receipt_number']

        if ui_order.get('l10n_bg_fiscal_memory_number'):
            order_fields['l10n_bg_fiscal_memory_number'] = ui_order['l10n_bg_fiscal_memory_number']

        if ui_order.get('l10n_bg_fiscal_receipt_datetime'):
            order_fields['l10n_bg_fiscal_receipt_datetime'] = ui_order['l10n_bg_fiscal_receipt_datetime']

        return order_fields

    def _export_for_ui(self, order):
        """Експорт на фискални данни към POS frontend"""
        result = super()._export_for_ui(order)
        result.update({
            'l10n_bg_fiscal_receipt_number': order.l10n_bg_fiscal_receipt_number,
            'l10n_bg_fiscal_memory_number': order.l10n_bg_fiscal_memory_number,
            'l10n_bg_fiscal_receipt_datetime': order.l10n_bg_fiscal_receipt_datetime,
        })
        return result
