# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, models

from odoo.addons.l10n_bg_tax_admin.models.chart_template import _grouping


class ResCompany(models.Model):
    _inherit = "res.company"

    def get_unaffected_earnings_account(self):
        """Returns the unaffected earnings account for this company, creating one
        if none has yet been defined.
        """
        unaffected_earnings_type = "equity_unaffected"
        account = self.env["account.account"].search(
            [
                ("company_id", "=", self.id),
                ("account_type", "=", unaffected_earnings_type),
            ]
        )
        if account:
            return account[0]
        # Do not assume '999999' doesn't exist since the user might have created such an account
        # manually.
        code = 999999
        digits = self.chart_template_id.code_digits
        grouping = self.chart_template_id.grouping
        if grouping:
            code = _grouping(code, digits, grouping)

        while self.env["account.account"].search(
            [("code", "=", str(code)), ("company_id", "=", self.id)]
        ):
            code -= 1
        return self.env["account.account"].create(
            {
                "code": str(code),
                "name": _("Undistributed Profits/Losses"),
                "account_type": unaffected_earnings_type,
                "company_id": self.id,
            }
        )
