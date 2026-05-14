#  Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class L10nBgAuditExtractor(models.AbstractModel):
    _name = "l10n.bg.audit.extractor"
    _description = "Bulgarian Reports Tag-Based Extractor"

    @api.model
    def extract(self, l10n_bg_applicability, date_from, date_to, company_id):
        """Extract all values for a given report category.

        Args:
            l10n_bg_applicability: str — gfo_balance / gfo_pl / gfo_cf /
                gfo_equity / god (the report this extraction is for)
            date_from: date — period start (used when basis == 'turnover')
            date_to: date — period end / cumulative cutoff
            company_id: int — res.company id

        Returns:
            list[dict] — one entry per tag in the category:
                {'tag_id': int, 'tag_name': str,
                 'l10n_bg_position': str, 'l10n_bg_extract_basis': str,
                 'value': float}
        """
        tags = self.env["account.account.tag"].search([
            ("l10n_bg_applicability", "=", l10n_bg_applicability),
            ("l10n_bg_position", "!=", False),
        ])
        return [
            {
                "tag_id": tag.id,
                "tag_name": tag.name,
                "l10n_bg_position": tag.l10n_bg_position,
                "l10n_bg_extract_basis": tag.l10n_bg_extract_basis,
                "value": self.extract_by_tag(tag.id, date_from, date_to, company_id),
            }
            for tag in tags
        ]

    @api.model
    def extract_by_tag(self, tag_id, date_from, date_to, company_id):
        """Return signed value for a single tag across a date window.

        Used as the per-row primitive by ``extract()``. Sign formula is
        driven by ``l10n_bg_position`` on the tag.
        """
        tag = self.env["account.account.tag"].browse(tag_id)
        if not tag.exists() or not tag.l10n_bg_position:
            return 0.0

        domain = [
            ("l10n_bg_account_tag_ids", "in", tag_id),
            ("parent_state", "=", "posted"),
            ("company_id", "=", company_id),
        ]
        if tag.l10n_bg_extract_basis == "balance":
            domain.append(("date", "<=", date_to))
        else:
            domain.append(("date", ">=", date_from))
            domain.append(("date", "<=", date_to))

        result = self.env["account.move.line"]._read_group(
            domain=domain,
            groupby=[],
            aggregates=["debit:sum", "credit:sum", "balance:sum"],
        )
        if not result:
            return 0.0
        debit, credit, balance = result[0]
        return self._compute_position_value(
            tag.l10n_bg_position, debit or 0.0, credit or 0.0, balance or 0.0
        )

    def _compute_position_value(self, position, debit, credit, balance):
        """Apply the position-specific sign formula."""
        if position == "asset":
            return balance
        if position == "liability_equity":
            return -balance
        if position == "revenue":
            return credit - debit
        if position == "expense":
            return debit - credit
        if position == "inflow":
            return credit - debit
        if position == "outflow":
            return debit - credit
        if position == "increase":
            return abs(balance)
        if position == "decrease":
            return -abs(balance)
        return 0.0

    @api.model
    def drill_down(self, tag_id, date_from, date_to, company_id):
        """Return the contributing aml recordset for audit drill-down."""
        tag = self.env["account.account.tag"].browse(tag_id)
        if not tag.exists():
            return self.env["account.move.line"]

        domain = [
            ("l10n_bg_account_tag_ids", "in", tag_id),
            ("parent_state", "=", "posted"),
            ("company_id", "=", company_id),
        ]
        if tag.l10n_bg_extract_basis == "balance":
            domain.append(("date", "<=", date_to))
        else:
            domain.append(("date", ">=", date_from))
            domain.append(("date", "<=", date_to))
        return self.env["account.move.line"].search(domain)
