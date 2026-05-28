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
            ("account_tag_ids", "in", tag_id),
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
            ("account_tag_ids", "in", tag_id),
            ("parent_state", "=", "posted"),
            ("company_id", "=", company_id),
        ]
        if tag.l10n_bg_extract_basis == "balance":
            domain.append(("date", "<=", date_to))
        else:
            domain.append(("date", ">=", date_from))
            domain.append(("date", "<=", date_to))
        return self.env["account.move.line"].search(domain)

    # ------------------------------------------------------------------
    # Bulk SQL extractor — оптимизирана за многоредови справки (ГДД, НСИ)
    # ------------------------------------------------------------------
    @api.model
    def extract_bulk(self, l10n_bg_applicability, date_from, date_to, company_id):
        """Single-SQL extraction of all tags in a category.

        Equivalent to ``extract()`` but uses one SQL pass per extraction
        basis instead of N per-tag round-trips. Required for declarations
        with hundreds of rows (Art.92 CIT return, NSI annexes) where the
        per-tag loop is too slow.

        Returns the same list[dict] shape as ``extract()`` so callers
        can switch freely.
        """
        tags = self.env["account.account.tag"].search([
            ("l10n_bg_applicability", "=", l10n_bg_applicability),
            ("l10n_bg_position", "!=", False),
        ])
        if not tags:
            return []

        # Split tags by extraction basis — balance tags get a different
        # date window than turnover tags, so we run two SQL passes.
        balance_tags = tags.filtered(lambda t: t.l10n_bg_extract_basis == "balance")
        turnover_tags = tags - balance_tags

        sums = {}  # tag_id → (debit, credit, balance)

        if balance_tags:
            self.env.cr.execute(
                """
                SELECT t.id, COALESCE(SUM(aml.debit), 0.0),
                       COALESCE(SUM(aml.credit), 0.0),
                       COALESCE(SUM(aml.balance), 0.0)
                FROM account_account_tag t
                JOIN account_account_tag_account_move_line_rel rel
                       ON rel.account_account_tag_id = t.id
                JOIN account_move_line aml ON aml.id = rel.account_move_line_id
                WHERE t.id = ANY(%s)
                  AND aml.parent_state = 'posted'
                  AND aml.company_id = %s
                  AND aml.date <= %s
                GROUP BY t.id
                """,
                (balance_tags.ids, company_id, date_to),
            )
            for row in self.env.cr.fetchall():
                sums[row[0]] = (row[1], row[2], row[3])

        if turnover_tags:
            self.env.cr.execute(
                """
                SELECT t.id, COALESCE(SUM(aml.debit), 0.0),
                       COALESCE(SUM(aml.credit), 0.0),
                       COALESCE(SUM(aml.balance), 0.0)
                FROM account_account_tag t
                JOIN account_account_tag_account_move_line_rel rel
                       ON rel.account_account_tag_id = t.id
                JOIN account_move_line aml ON aml.id = rel.account_move_line_id
                WHERE t.id = ANY(%s)
                  AND aml.parent_state = 'posted'
                  AND aml.company_id = %s
                  AND aml.date BETWEEN %s AND %s
                GROUP BY t.id
                """,
                (turnover_tags.ids, company_id, date_from, date_to),
            )
            for row in self.env.cr.fetchall():
                sums[row[0]] = (row[1], row[2], row[3])

        return [
            {
                "tag_id": tag.id,
                "tag_name": tag.name,
                "l10n_bg_position": tag.l10n_bg_position,
                "l10n_bg_extract_basis": tag.l10n_bg_extract_basis,
                "value": self._compute_position_value(
                    tag.l10n_bg_position,
                    *sums.get(tag.id, (0.0, 0.0, 0.0)),
                ),
            }
            for tag in tags
        ]

    # ------------------------------------------------------------------
    # Period comparison — current vs previous (за CIT и НСИ)
    # ------------------------------------------------------------------
    @api.model
    def extract_with_comparison(
        self, l10n_bg_applicability, year, company_id, use_bulk=True
    ):
        """Extract values for ``year`` and ``year-1`` in one call.

        Returns a dict keyed by tag_id with both current and previous-year
        values plus the delta. Used by declarations that need PY columns
        (Art.92 CIT return, NSI annexes).
        """
        from datetime import date as _date

        date_from_cur = _date(year, 1, 1)
        date_to_cur = _date(year, 12, 31)
        date_from_prev = _date(year - 1, 1, 1)
        date_to_prev = _date(year - 1, 12, 31)

        impl = self.extract_bulk if use_bulk else self.extract
        current = {r["tag_id"]: r for r in impl(
            l10n_bg_applicability, date_from_cur, date_to_cur, company_id
        )}
        previous = {r["tag_id"]: r for r in impl(
            l10n_bg_applicability, date_from_prev, date_to_prev, company_id
        )}

        result = {}
        for tag_id, cur_row in current.items():
            prev_row = previous.get(tag_id) or {"value": 0.0}
            result[tag_id] = {
                "tag_id": tag_id,
                "tag_name": cur_row["tag_name"],
                "l10n_bg_position": cur_row["l10n_bg_position"],
                "l10n_bg_extract_basis": cur_row["l10n_bg_extract_basis"],
                "current_year": cur_row["value"],
                "previous_year": prev_row["value"],
                "delta": cur_row["value"] - prev_row["value"],
            }
        return result
