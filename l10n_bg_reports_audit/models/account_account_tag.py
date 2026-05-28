#  Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .l10n_bg_file_helper import get_l10n_bg_applicability


class AccountAccountTag(models.Model):
    _inherit = ["account.account.tag", "l10n.bg.config.mixin"]
    _name = "account.account.tag"

    l10n_bg_applicability = fields.Selection(
        selection="_get_l10n_bg_applicability", string="Use for"
    )
    l10n_bg_code = fields.Char(
        "Code", compute="_compute_l10n_bg_code", help="A technical field for tag code"
    )
    l10n_bg_tax_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="BG tax partner",
        help="Partner to set on tax lines when the BG tax tag is applied.",
    )
    applicability = fields.Selection(
        selection_add=[
            ("l10n_bg_partner", "BG-NSI Usage for Partners"),
            ("l10n_bg_product", "BG-NSI Usage for Products")
        ],
        ondelete={
        "l10n_bg_partner": "set default",
        "l10n_bg_product": "set default"
        },
    )

    l10n_bg_extract_basis = fields.Selection(
        [
            ("balance", "Balance (cumulative)"),
            ("turnover", "Turnover (period only)"),
        ],
        string="Extraction Basis",
        default="balance",
        help="balance — SUM from beginning to date_to (Balance sheet accounts).\n"
             "turnover — SUM in period [date_from, date_to] (P&L accounts).\n\n"
             "Default cases:\n"
             "  Assets / Liabilities / Equity → balance\n"
             "  Revenue / Expense → turnover\n"
             "  Cash flow → turnover\n"
             "  Equity movements → turnover",
    )
    l10n_bg_position = fields.Selection(
        [
            ("asset", "Asset (debit-normal)"),
            ("liability_equity", "Liability / Equity (credit-normal)"),
            ("revenue", "Revenue (credit - debit)"),
            ("expense", "Expense (debit - credit)"),
            ("inflow", "Cash inflow (credit on cash account)"),
            ("outflow", "Cash outflow (debit on cash account)"),
            ("increase", "Equity increase"),
            ("decrease", "Equity decrease"),
        ],
        string="Report Position",
        help="Semantic position of this tag inside the report row. "
             "Defines the signed extraction formula. UI validates against "
             "l10n_bg_applicability — not all positions are valid for every "
             "category.",
    )

    _VALID_POSITION_BY_L10N_BG_APPLICABILITY = {
        "gfo_balance": ("asset", "liability_equity"),
        "gfo_pl": ("revenue", "expense"),
        "gfo_cf": ("inflow", "outflow"),
        "gfo_equity": ("increase", "decrease"),
        # 'god' allows any position (NSI rows mix balance + flow)
        # 'dec92' allows any position (CIT return mixes balance lines for
        # owners' equity / impairments, revenue/expense lines for the P&L
        # source, and increase/decrease flags for permanent / temporary
        # adjustments under Art.23-26 ZKPO).
        # legacy VAT categories (declaration/purchase/sale/vies) do not use l10n_bg_position
    }

    def _get_l10n_bg_applicability(self):
        return get_l10n_bg_applicability(self)

    def _compute_l10n_bg_code(self):
        for record in self:
            record.l10n_bg_code = "".join(filter(str.isdigit, record.name.upper()))

    @api.constrains("l10n_bg_position", "l10n_bg_applicability")
    def _check_position_matches_l10n_bg_applicability(self):
        for tag in self:
            cat = tag.l10n_bg_applicability
            valid = self._VALID_POSITION_BY_L10N_BG_APPLICABILITY.get(cat)
            if valid is None or not tag.l10n_bg_position:
                continue
            if tag.l10n_bg_position not in valid:
                raise ValidationError(_(
                    "Tag '%(name)s' with l10n_bg_applicability '%(cat)s' cannot "
                    "have l10n_bg_position '%(pos)s'. Valid positions: %(valid)s.",
                    name=tag.name,
                    cat=cat,
                    pos=tag.l10n_bg_position,
                    valid=", ".join(valid),
                ))

    def action_bulk_edit(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bulk Edit Tags',
            'res_model': 'account.account.tag.bulk.edit.wizard',
            'view_mode': 'form',
            'target': 'new',
        }
