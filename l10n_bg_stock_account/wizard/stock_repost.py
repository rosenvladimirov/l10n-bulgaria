"""Осчетоводяване на пропуснатите складови движения (ADR ussmed-stock-repost-2026/0001).

Модулът осчетоводява движението само при валидиране. Категория, на която
``l10n_bg_stock_auto_post`` е включен по-късно, или движения отпреди
настройката на сметките остават без статия — назад нищо не се осчетоводява.
Съветникът минава по готовите движения без статия за периода, по датата им,
и прави за всяко същата статия, каквато модулът би направил при валидиране —
на датата на движението, по една на пикинг. Статиите носят белег и могат да
се махнат наведнъж (сторно или изтриване).
"""
from collections import defaultdict
from datetime import datetime, time

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import format_amount


class AccountMove(models.Model):
    _inherit = "account.move"

    # белегът на статиите от съветника — за прегледа и за махането наведнъж
    l10n_bg_stock_reposted = fields.Boolean(
        string="Posted by the stock repost wizard", readonly=True, copy=False, index="btree_not_null",
    )


class L10nBgStockRepost(models.TransientModel):
    _name = "l10n.bg.stock.repost"
    _description = "Post Missing Stock Journal Entries"

    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related="company_id.currency_id")
    date_from = fields.Date(string="From", required=True)
    date_to = fields.Date(string="To", required=True)
    category_ids = fields.Many2many(
        "product.category", string="Product categories",
        help="Only the moves of products in these categories (and their children). Empty: all.",
    )
    preview = fields.Html(compute="_compute_preview", sanitize=False)

    # ------------------------------------------------------------------
    # Кои движения
    # ------------------------------------------------------------------
    def _period_domain(self):
        self.ensure_one()
        domain = [
            ("company_id", "=", self.company_id.id),
            ("state", "=", "done"),
            ("account_move_id", "=", False),
            ("date", ">=", datetime.combine(self.date_from, time.min)),
            ("date", "<=", datetime.combine(self.date_to, time.max)),
            ("product_id.is_storable", "=", True),
        ]
        if self.category_ids:
            domain.append(("product_id.categ_id", "child_of", self.category_ids.ids))
        return domain

    def _classify(self):
        """``(за статия, без стойност, без сметки, без правило)`` — движенията на периода.

        „За статия“ са тези, за които модулът прави статия и тя има редове;
        „без сметки“ — правилото казва „да“, но сметките на категорията липсват.
        """
        self.ensure_one()
        Move = self.env["stock.move"].with_company(self.company_id)
        moves = Move.search(self._period_domain(), order="date, id")
        to_post, zero, no_accounts, no_rule = [], [], [], []
        currency = self.company_id.currency_id
        for move in moves:
            if not move._should_create_account_move():
                if move.is_valued and currency.is_zero(move.value) and move.product_id.categ_id.l10n_bg_stock_auto_post:
                    zero.append(move.id)
                else:
                    no_rule.append(move.id)
            elif move._get_account_move_line_vals():
                to_post.append(move.id)
            else:
                no_accounts.append(move.id)
        return tuple(Move.browse(ids) for ids in (to_post, zero, no_accounts, no_rule))

    @api.depends("company_id", "date_from", "date_to", "category_ids")
    def _compute_preview(self):
        for wizard in self:
            if not (wizard.date_from and wizard.date_to) or wizard.date_from > wizard.date_to:
                wizard.preview = False
                continue
            wizard.preview = wizard._preview_html(*wizard._classify())

    def _preview_html(self, to_post, zero, no_accounts, no_rule):
        def money(value):
            return format_amount(self.env, value, self.currency_id)

        by_month = defaultdict(lambda: [0, 0.0])
        for move in to_post:
            row = by_month[move.date.strftime("%Y-%m")]
            row[0] += 1
            row[1] += abs(move.value)
        rows = Markup("").join(
            Markup("<tr><td>%s</td><td class='text-end'>%s</td><td class='text-end'>%s</td></tr>") % (month, n, money(value))
            for month, (n, value) in sorted(by_month.items())
        )
        summary = Markup(
            "<p>%s: <b>%s</b> · %s: %s · %s: %s · %s: %s</p>"
        ) % (
            _("To post"), len(to_post),
            _("Zero value (no entry)"), len(zero),
            _("Missing accounts"), len(no_accounts),
            _("Not posted by the rules (category without auto-post, internal…)"), len(no_rule),
        )
        head = Markup("<tr><th>%s</th><th class='text-end'>%s</th><th class='text-end'>%s</th></tr>") % (
            _("Month"), _("Moves"), _("Value"))
        missing = ""
        if no_accounts:
            names = ", ".join(sorted(set(no_accounts.mapped("product_id.categ_id.complete_name")))[:10])
            missing = Markup("<p class='text-warning'>%s %s</p>") % (_("Categories without accounts:"), names)
        return summary + missing + Markup("<table class='table table-sm'><thead>%s</thead><tbody>%s</tbody></table>") % (head, rows)

    # ------------------------------------------------------------------
    # Записът и махането
    # ------------------------------------------------------------------
    def _post_moves(self, moves):
        """Статиите на ``moves`` — по пикинг (или движение) и дата, на датата на движението."""
        groups = defaultdict(list)
        for move in moves.sorted(lambda m: (m.date, m.id)):
            groups[(move.picking_id.id or f"move-{move.id}", move.date.date())].append(move.id)
        created = []
        for (_key, day), ids in groups.items():
            created += moves.browse(ids).with_context(force_period_date=day)._create_account_move().ids
        created = self.env["account.move"].browse(created)
        created.l10n_bg_stock_reposted = True
        return created

    def action_post(self):
        self.ensure_one()
        to_post = self._classify()[0]
        if not to_post:
            raise UserError(_("There are no stock moves to post for this period."))
        created = self._post_moves(to_post)
        return {
            "type": "ir.actions.act_window",
            "name": _("Posted stock entries"),
            "res_model": "account.move",
            "domain": [("id", "in", created.ids)],
            "views": [(False, "list"), (False, "form")],
            "context": {"create": False},
        }

    def _reposted_entries(self):
        self.ensure_one()
        return self.env["account.move"].search([
            ("company_id", "=", self.company_id.id),
            ("l10n_bg_stock_reposted", "=", True),
            ("date", ">=", self.date_from),
            ("date", "<=", self.date_to),
            ("state", "!=", "cancel"),
        ])

    def action_remove(self):
        """Маха статиите на съветника за периода: движенията остават без статия
        (както преди), а статиите се изтриват — за проба и повторение."""
        self.ensure_one()
        entries = self._reposted_entries()
        if not entries:
            raise UserError(_("There are no entries of the wizard for this period."))
        # връзката на движенията (account_move_id) се нулира от изтриването (ondelete set null)
        entries.filtered(lambda move: move.state == "posted").button_draft()
        entries.with_context(force_delete=True).unlink()
        return {"type": "ir.actions.act_window_close"}
