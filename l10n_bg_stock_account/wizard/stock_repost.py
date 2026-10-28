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
        table = Markup("<table class='table table-sm'><thead>%s</thead><tbody>%s</tbody></table>") % (head, rows)
        return summary + missing + table + self._preview_by_kind_html(to_post, money)

    # Пламена, 27.10.2026 (ТГ 174293, т. 3): в training за 2026 съветникът
    # предлагаше 11 771 движения — повечето инвентаризации от февруари — а от
    # сумата по месеци това не личеше. Счетоводителят трябва да види ВИДА и
    # документите преди запис.
    _PREVIEW_REFERENCES = 25

    def _move_kind(self, move):
        """Видът на движението за прегледа — по признаците на ядрото, не по типа операция."""
        if move.is_inventory:
            return "inventory"
        if move.scrap_id:
            return "scrap"
        if "production" in (move.location_id.usage, move.location_dest_id.usage):
            return "production"
        source_valued = move.location_id._should_be_valued()
        dest_valued = move.location_dest_id._should_be_valued()
        if dest_valued and not source_valued:
            return "receipt"
        if source_valued and not dest_valued:
            return "delivery"
        return "other"

    def _kind_labels(self):
        return {
            "receipt": _("Receipts"),
            "delivery": _("Deliveries"),
            "inventory": _("Inventory adjustments"),
            "scrap": _("Scrap"),
            "production": _("Production"),
            "other": _("Other"),
        }

    def _preview_by_kind_html(self, to_post, money):
        if not to_post:
            return Markup("")
        labels = self._kind_labels()
        # вид → референция → [брой, стойност, първа дата]
        kinds = defaultdict(lambda: defaultdict(lambda: [0, 0.0, None]))
        for move in to_post:
            # без пикинг/брак референцията е обща („Product Quantity Updated“
            # за всяка инвентаризация) — затова с продукта, за да личи какво
            if move.picking_id or move.scrap_id:
                key = move.picking_id.name or move.scrap_id.name
            else:
                key = "%s · %s" % (move.reference or _("Move %s", move.id), move.product_id.display_name)
            ref = kinds[self._move_kind(move)][key]
            ref[0] += 1
            ref[1] += abs(move.value)
            ref[2] = min(ref[2], move.date) if ref[2] else move.date
        head = Markup("<tr><th>%s</th><th class='text-end'>%s</th><th class='text-end'>%s</th>"
                      "<th class='text-end'>%s</th></tr>") % (
            _("Kind"), _("Documents"), _("Moves"), _("Value"))
        rows = Markup("").join(
            Markup("<tr><td>%s</td><td class='text-end'>%s</td><td class='text-end'>%s</td>"
                   "<td class='text-end'>%s</td></tr>") % (
                labels[kind], len(refs), sum(r[0] for r in refs.values()),
                money(sum(r[1] for r in refs.values())))
            for kind, refs in sorted(kinds.items(), key=lambda item: list(labels).index(item[0]))
        )
        details = Markup("")
        for kind in labels:
            refs = kinds.get(kind)
            if not refs:
                continue
            ordered = sorted(refs.items(), key=lambda item: (item[1][2], item[0]))
            shown = ordered[:self._PREVIEW_REFERENCES]
            items = Markup("").join(
                Markup("<tr><td>%s</td><td>%s</td><td class='text-end'>%s</td><td class='text-end'>%s</td></tr>") % (
                    name, date.strftime("%Y-%m-%d"), n, money(value))
                for name, (n, value, date) in shown
            )
            more = Markup("")
            if len(ordered) > len(shown):
                more = Markup("<p class='text-muted small'>%s</p>") % _(
                    "… and %(count)s more documents — use “Show the moves” for the full list.",
                    count=len(ordered) - len(shown))
            details += Markup(
                "<h6 class='mt-3'>%s</h6><table class='table table-sm'><thead><tr><th>%s</th><th>%s</th>"
                "<th class='text-end'>%s</th><th class='text-end'>%s</th></tr></thead><tbody>%s</tbody></table>%s"
            ) % (labels[kind], _("Reference"), _("Date"), _("Moves"), _("Value"), items, more)
        return (Markup("<h5 class='mt-3'>%s</h5><table class='table table-sm'><thead>%s</thead><tbody>%s</tbody></table>")
                % (_("By kind"), head, rows)) + details

    def action_view_moves(self):
        """Всички движения, които ще получат статия — за сверка преди запис."""
        self.ensure_one()
        to_post = self._classify()[0]
        return {
            "type": "ir.actions.act_window",
            "name": _("Stock moves to post"),
            "res_model": "stock.move",
            "domain": [("id", "in", to_post.ids)],
            "views": [(False, "list"), (False, "form")],
            "context": {"create": False},
        }

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
            # вече сторнираната статия е махната — второ сторно би я върнало
            ("reversal_move_ids", "=", False),
        ])

    def action_remove(self):
        """Маха статиите на съветника за периода: движенията остават без статия
        (както преди) и съветникът може да се пусне наново.

        Пламена, 27.10.2026 (ТГ 174293, т. 4): осчетоводената статия се
        връщаше в чернова и се триеше без следа — дори редактирана след
        осчетоводяването. Сега осчетоводената се СТОРНИРА на същата дата (и
        статията, и сторното остават с историята си); трие се само черновата,
        която никога не е била осчетоводена."""
        self.ensure_one()
        entries = self._reposted_entries()
        if not entries:
            raise UserError(_("There are no entries of the wizard for this period."))
        posted = entries.filtered(lambda move: move.state == "posted")
        drafts = entries - posted
        # връзката движение → статия се къса изрично: сторното не я пипа,
        # а без това движението не е „без статия“ за следващото пускане
        self.env["stock.move"].search([("account_move_id", "in", entries.ids)]).account_move_id = False
        if posted:
            reversals = posted._reverse_moves(
                default_values_list=[{
                    "date": move.date,
                    "ref": _("Reversal of %(entry)s (stock repost wizard)", entry=move.name),
                } for move in posted],
                cancel=True,
            )
            for move, reversal in zip(posted, reversals):
                # Markup около превода — иначе връзката излиза като текст с тагове
                move.message_post(body=Markup(_(
                    "Removed by the stock repost wizard: reversed by %(reversal)s."
                )) % {"reversal": reversal._get_html_link()})
        drafts.with_context(force_delete=True).unlink()
        return {"type": "ir.actions.act_window_close"}
