# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class L10nBgAccountIndustryMap(models.Model):
    """Typed mapping between a КИД activity and a chart-of-accounts code.

    A row states that synthetic account ``account_code`` (a *prefix*, e.g.
    ``701`` matches ``701``, ``701.000``, ``701.100`` …) is, for the given
    КИД activity:

      * ``mandatory``      – the activity cannot be run without it;
      * ``characteristic`` – typical / indicative of the activity;
      * ``forbidden``      – must not appear for that activity.

    ``revenue_indicator`` flags the net-sales-revenue accounts
    (701 / 702 / 703 / 704 …). These are the only rows used by the
    reverse-derivation of a company's primary КИД, following the НСИ
    methodology (main activity = the one with the highest relative share
    of net sales revenue).

    Loaded through the ``account.chart.template`` plugin pipeline; ``note``
    carries the accounting-standard rationale (СС 2 / СС 11 / СС 41 …).
    """

    _name = "l10n.bg.account.industry.map"
    _description = "КИД ↔ Account mapping"
    _order = "kid_id, account_code, relation_type"

    kid_id = fields.Many2one(
        "l10n.bg.kid",
        string="КИД activity",
        required=True,
        ondelete="cascade",
        index=True,
    )
    kid_version = fields.Selection(related="kid_id.kid_version", store=True)
    account_code = fields.Char(
        string="Account code",
        required=True,
        index=True,
        help="Synthetic account code prefix, matched as code LIKE '<value>%' "
        "(e.g. 701 covers 701, 701.000, 701.100).",
    )
    relation_type = fields.Selection(
        selection=[
            ("mandatory", "Mandatory"),
            ("characteristic", "Characteristic"),
            ("forbidden", "Forbidden"),
        ],
        required=True,
        default="characteristic",
        index=True,
    )
    revenue_indicator = fields.Boolean(
        string="Net-revenue indicator",
        help="Account participates in the НСИ reverse-derivation of the "
        "company's primary КИД (net sales revenue accounts only).",
    )
    note = fields.Char(
        translate=True,
        help="Accounting-standard rationale / source (СС 2, СС 11, СС 41 …).",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        index=True,
        help="Leave empty for the localization default; set it only for a "
        "company-specific override.",
    )

    _sql_constraints = [
        (
            "kid_account_company_uniq",
            "unique(kid_id, account_code, company_id)",
            "Duplicate КИД / account / company mapping.",
        ),
    ]

    @api.depends("kid_id.complete_name", "account_code", "relation_type")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = (
                f"{rec.kid_id.code} · {rec.account_code} · {rec.relation_type}"
            )

    def _resolve_accounts(self, company):
        """Return the ``account.account`` records of ``company`` whose code
        starts with this row's ``account_code`` prefix.

        ``account.account`` exposes the company link as ``company_ids``
        (Many2many, Odoo 17+) or ``company_id`` (older); resolve whichever
        is present so the model stays version-tolerant.
        """
        self.ensure_one()
        Account = self.env["account.account"]
        domain = [("code", "=like", f"{self.account_code}%")]
        if "company_ids" in Account._fields:
            domain.append(("company_ids", "in", company.id))
        elif "company_id" in Account._fields:
            domain.append(("company_id", "=", company.id))
        return Account.with_company(company).search(domain)
