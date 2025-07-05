from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PosOrder(models.Model):
    _inherit = 'pos.order'

    fiscal_receipt_number = fields.Char('Fiscal voucher', readonly=True)
    fiscal_receipt_datetime = fields.Datetime('Date and time of fiscal voucher', readonly=True)

    def _prepare_fiscal_receipt_data(self):
        """Подготвя данните за фискалния бон"""
        self.ensure_one()
        items = []

        for line in self.lines:
            tax_group = line.product_id.categ_id.get_fiscal_tax_group()
            item = {
                "text": line.product_id.name,
                "quantity": line.qty,
                "unitPrice": line.price_unit,
                "taxGroup": tax_group,
            }
            items.append(item)

        payments = []
        for payment in self.payment_ids:
            payment_type = "cash"  # По подразбиране
            if payment.payment_method_id.use_payment_terminal == 'card':
                payment_type = "card"

            payments.append({
                "amount": payment.amount,
                "paymentType": payment_type
            })

        return {
            "uniqueSale": True,
            "items": items,
            "payments": payments
        }

    def action_print_fiscal_receipt(self):
        """Печат на фискален бон"""
        self.ensure_one()
        if not self.config_id.fiscal_printer_id:
            raise ValidationError(_('No configured fiscal printer for this POS terminal'))

        receipt_data = self._prepare_fiscal_receipt_data()

        try:
            result = self.config_id.fiscal_printer_id.print_receipt(receipt_data)
            self.fiscal_receipt_number = result.get('receiptNumber')
            self.fiscal_receipt_datetime = fields.Datetime.now()
            self.message_post(body=_('Фискален бон отпечатан успешно'))
        except Exception as e:
            self.message_post(body=_('Грешка при печат на фискален бон: %s') % str(e))
            raise ValidationError(_('Грешка при печат на фискален бон: %s') % str(e))

    def action_pos_order_paid(self):
        res = super(PosOrder, self).action_pos_order_paid()
        if self.config_id.auto_fiscal_printing and self.config_id.fiscal_printer_id:
            self.action_print_fiscal_receipt()
        return res
