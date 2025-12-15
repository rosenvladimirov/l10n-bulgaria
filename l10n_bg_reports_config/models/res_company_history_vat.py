#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class L10nBgVatRatioHistory(models.Model):
    _inherit = "l10n.bg.vat.ratio.history"

    def _prepare_notification(self, result):
        """Prepare a notification message based on a computation result."""
        if result["is_computed"]:
            message = _(
                "VAT ratio computed from declarations: %.2f%%\n"
                "Numerator: %.2f %s\n"
                "Denominator: %.2f %s"
            ) % (
                          result["vat_ratio"],
                          result["numerator_total"],
                          self.currency_id.symbol,
                          result["denominator_total"],
                          self.currency_id.symbol,
                      )
            if result["is_provisional"]:
                message += "\n" + _("(Provisional - will be adjusted at year end)")

            return {
                "type": "success",
                "message": message,
                "sticky": False,
            }
        else:
            if "copied from last known coefficient" in result.get("notes", ""):
                message = result["notes"]
                notification_type = "warning"
            else:
                message = _(
                    "No VAT declaration data found for this period.\n"
                    "No previous coefficient found either.\n"
                    "Please enter values manually."
                )
                notification_type = "warning"

            return {
                "type": notification_type,
                "message": message,
                "sticky": True,
            }

    def action_compute_from_declarations(self):
        """Action to compute a ratio from VAT declarations with Odoo 18 notifications."""
        self.ensure_one()
        month = int(self.month) if self.month else None

        try:
            result = self.compute_ratio_from_vat_declarations(self.year, month, self.company_id)

            # Update record
            write_vals = {
                key: result[key]
                for key in result
                if key in self._fields
            }
            write_vals["notes"] = result.get("notes") or self.notes or ""
            self.write(write_vals)

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
        """Calculate annual adjustment with Odoo 18 notification support."""
        self.ensure_one()

        if self.month:
            self.env['bus.bus']._sendone(
                self.env.user.partner_id,
                'simple_notification',
                {
                    'type': 'danger',
                    'title': _("Error"),
                    'message': _("Annual adjustment can only be calculated for annual coefficients (without month)."),
                    'sticky': True,
                }
            )
            return

        # Get all monthly ratios for the year
        monthly_ratios = self.search([
            ("year", "=", self.year),
            ("month", "!=", False),
            ("company_id", "=", self.company_id.id),
            ("active", "=", True),
        ])

        if not monthly_ratios:
            self.env['bus.bus']._sendone(
                self.env.user.partner_id,
                'simple_notification',
                {
                    'type': 'danger',
                    'title': _("Error"),
                    'message': _("No monthly ratios found for year %s. Cannot calculate adjustment.") % self.year,
                    'sticky': True,
                }
            )
            return

        # Send notification via bus (Odoo 18 style)
        self.env['bus.bus']._sendone(
            self.env.user.partner_id,
            'simple_notification',
            {
                'type': 'info',
                'title': _("Information"),
                'message': _(
                    "Annual adjustment calculation requires tracking of partial VAT credits. "
                    "This should be implemented in the VAT return module."
                ),
                'sticky': True,
            }
        )
