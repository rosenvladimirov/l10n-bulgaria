# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class L10nBgAccountKidRule(models.Model):
    """Account-code classification rule driving the install-time filter.

    "One chart, many КИД": the full Bulgarian national chart of accounts
    is shipped by Odoo core ``l10n_bg`` and merged in
    ``account.chart.template._get_account_account``. This model classifies
    a *synthetic account-code prefix* into one of three buckets:

      * ``universal``          – needed by practically every КИД sector;
                                  always loaded (base installation).
      * ``sector_specific``    – tied via the many2many ``kid_ids`` to the
                                  КИД sectors that need it; loaded only
                                  when at least one of those sectors is in
                                  the company's selected set
                                  (``res.company.l10n_bg_kid_ids``).
      * ``framework_specific`` – outside the national chart entirely
                                  (banks/insurance → IFRS under БНБ/КФН;
                                  budget entities → separate budget chart);
                                  never loaded into the national chart.

    Design note — *default-keep*: an account whose code matches **no**
    rule is treated as universal and kept. Only the exceptions
    (sector-/framework-specific) need a rule, so a forgotten core account
    is never silently dropped. The matching is by code prefix
    (``code LIKE '<account_code>%'``), consistent with
    ``l10n.bg.account.industry.map``.

    This is the install-filter / classification concern. Reverse-derivation
    of a company's primary КИД from net sales revenue stays in the
    separate ``l10n.bg.account.industry.map`` (revenue_indicator) model.
    """

    _name = "l10n.bg.account.kid.rule"
    _description = "Account-code КИД classification rule"
    _order = "classification, account_code"
    _rec_name = "display_name"
    # Търсене по КОДА на сметката и по описанието. _rec_name е display_name,
    # което тук се преизчислява без да е декларирано като поле — тоест остава
    # наследеното от base computed non-stored и стандартният name_search гърми.
    # _rec_names_search пренасочва search-а към реалните колони.
    _rec_names_search = ["account_code", "note"]

    account_code = fields.Char(
        string="Account code",
        required=True,
        index=True,
        help="Synthetic account-code prefix, matched as code LIKE "
        "'<value>%' (e.g. 303 covers 303, 303.000, 303.100).",
    )
    classification = fields.Selection(
        selection=[
            ("universal", "Universal"),
            ("sector_specific", "Sector-specific"),
            ("framework_specific", "Framework-specific"),
        ],
        required=True,
        default="sector_specific",
        index=True,
    )
    kid_ids = fields.Many2many(
        "l10n.bg.kid",
        relation="l10n_bg_kid_account_rule_rel",
        column1="rule_id",
        column2="kid_id",
        string="КИД sectors",
        help="КИД sectors that require this account "
        "(only for sector-specific rules).",
    )
    note = fields.Char(
        translate=True,
        help="Accounting-standard rationale / source "
        "(СС 2 / СС 11 / СС 41 / ЗАДС …).",
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "account_code_uniq",
            "unique(account_code)",
            "An account-code prefix can have only one classification rule.",
        ),
    ]

    @api.depends("account_code", "classification")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.account_code} · {rec.classification}"

    @api.constrains("classification", "kid_ids")
    def _check_kid_ids(self):
        for rec in self:
            if rec.classification == "sector_specific" and not rec.kid_ids:
                raise ValidationError(
                    _(
                        "Sector-specific rule '%s' must list at least one "
                        "КИД sector."
                    )
                    % rec.account_code
                )
            if rec.classification != "sector_specific" and rec.kid_ids:
                raise ValidationError(
                    _(
                        "Only sector-specific rules may reference КИД "
                        "sectors (rule '%s')."
                    )
                    % rec.account_code
                )
