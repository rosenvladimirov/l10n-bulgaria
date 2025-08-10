from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PosOrder(models.Model):
    _inherit = 'pos.order'

    fiscal_receipt_number = fields.Char(string='Fiscal Receipt Number', readonly=True)
    fiscal_receipt_datetime = fields.Datetime(string='Fiscal Receipt Date/Time', readonly=True)

    def action_print_fiscal_receipt(self):
        """Print fiscal receipt"""
        self.ensure_one()
        if not self.config_id.fiscal_printer_id:
            raise ValidationError(_('No configured fiscal printer for this POS terminal'))

        receipt_data = self._prepare_fiscal_receipt_data()

        try:
            result = self.config_id.fiscal_printer_id.print_receipt(receipt_data)
            self.fiscal_receipt_number = result.get('receiptNumber')
            self.fiscal_receipt_datetime = fields.Datetime.now()
            self.message_post(body=_('Fiscal receipt printed successfully'))
        except Exception as e:
            self.message_post(body=_('Error printing fiscal receipt: %s') % str(e))
            raise ValidationError(_('Error printing fiscal receipt: %s') % str(e))

    def _prepare_fiscal_receipt_data(self):
        """Prepare data for fiscal receipt"""
        self.ensure_one()
        items = []

        for line in self.lines:
            tax_group = line.product_id.categ_id.get_fiscal_tax_group() if hasattr(line.product_id.categ_id, 'get_fiscal_tax_group') else 'A'
            item = {
                "text": line.product_id.name,
                "quantity": line.qty,
                "unitPrice": line.price_unit,
                "taxGroup": tax_group,
            }
            items.append(item)

        payments = []
        for payment in self.payment_ids:
            payment_type = "cash"  # Default
            if hasattr(payment.payment_method_id, 'use_payment_terminal') and payment.payment_method_id.use_payment_terminal == 'card':
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
