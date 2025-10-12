#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class L10nBgVatRatioHistory(models.Model):
    _inherit = "l10n.bg.vat.ratio.history"

    def action_compute_from_declarations(self):
        """Override to add Odoo 18 notification support."""
        try:
            result = super().action_compute_from_declarations()

            # Prepare notification
            notification = self._prepare_notification(result)

            # Send notification via bus (Odoo 18 style)
            notification_type = notification["type"]
            if notification_type not in ['success', 'warning', 'danger']:
                notification_type = 'info'

            self.env['bus.bus']._sendone(
                self.env.user.partner_id,
                'simple_notification',
                {
                    'type': notification_type,
                    'title': _("VAT Ratio Calculation (Art. 73)"),
                    'message': notification["message"],
                    'sticky': notification["sticky"],
                }
            )

        except Exception as e:
            self.env['bus.bus']._sendone(
                self.env.user.partner_id,
                'simple_notification',
                {
                    'type': 'danger',
                    'title': _("Error"),
                    'message': _("Error computing VAT ratio: %s") % str(e),
                    'sticky': True,
                }
            )
            raise

    def action_calculate_annual_adjustment(self):
        """Override to add Odoo 18 notification support."""
        result = super().action_calculate_annual_adjustment()

        # Send notification via bus (Odoo 18 style)
        self.env['bus.bus']._sendone(
            self.env.user.partner_id,
            'simple_notification',
            {
                'type': 'info',
                'title': _("Information"),
                'message': result["message"],
                'sticky': True,
            }
        )
