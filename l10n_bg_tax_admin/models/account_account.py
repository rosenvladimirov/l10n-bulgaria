from odoo import _, api, models
from odoo.exceptions import UserError

from odoo.addons.l10n_bg_tax_admin.models.chart_template import _grouping


class AccountAccount(models.Model):
    _inherit = "account.account"

    @api.model
    def _search_new_account_code(self, company, digits, prefix, grouping="[]"):
        prefix = str(prefix or "")
        max_digits = digits - len(prefix)
        for num in range(1, int("".ljust(max_digits, "9"))):
            new_code = prefix + str(num).ljust(max_digits, "0")
            new_code = _grouping(new_code, digits, grouping)
            rec = self.search(
                [("code", "=", new_code), ("company_id", "=", company.id)], limit=1
            )
            if not rec:
                return new_code
        raise UserError(_("Cannot generate an unused account code."))
