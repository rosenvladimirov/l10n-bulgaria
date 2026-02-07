#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account_reports.models.account_move_line import AccountMoveLine


def post_load():
    if getattr(AccountMoveLine, "_l10n_bg_tax_closing_patch", False):
        return

    original = AccountMoveLine._check_taxes_on_closing_entries

    def _check_taxes_on_closing_entries(self):
        if self.env.context.get("l10n_bg_skip_tax_closing_check"):
            return
        return original(self)

    AccountMoveLine._check_taxes_on_closing_entries = _check_taxes_on_closing_entries
    AccountMoveLine._l10n_bg_tax_closing_patch = True
