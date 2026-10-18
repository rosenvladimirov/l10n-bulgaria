"""Съветникът „Осчетоводи пропуснатите движения“ (ADR ussmed-stock-repost-2026/0001)."""
from datetime import date, datetime

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestStockRepost(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.company.account_stock_journal_id = cls.company_data["default_journal_misc"]

        def account(code, account_type):
            return cls.env["account.account"].create({
                "name": f"Repost {code}", "code": code, "account_type": account_type,
                "company_ids": [Command.link(cls.company.id)],
            })

        cls.valuation = account("304901", "asset_current")
        cls.input = account("301901", "asset_current")
        cls.output = account("702901", "expense")
        # периодична оценка, сметките са настроени, но auto_post още е изключен — както в НЕУРО
        cls.categ = cls.env["product.category"].create({
            "name": "Repost goods",
            "property_valuation": "periodic",
            "property_cost_method": "fifo",
            "property_stock_valuation_account_id": cls.valuation.id,
            "l10n_bg_stock_input_account_id": cls.input.id,
            "l10n_bg_stock_output_account_id": cls.output.id,
        })
        cls.product = cls.env["product.product"].create({
            "name": "Repost product", "is_storable": True, "categ_id": cls.categ.id, "standard_price": 5.0,
        })
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.company.id)], limit=1)
        cls.stock = cls.warehouse.lot_stock_id
        cls.supplier = cls.env.ref("stock.stock_location_suppliers")
        cls.customer = cls.env.ref("stock.stock_location_customers")

    def _move(self, source, dest, qty, when, price=None, product=None):
        move = self.env["stock.move"].create({
            "product_id": (product or self.product).id,
            "product_uom_qty": qty,
            "location_id": source.id,
            "location_dest_id": dest.id,
            "company_id": self.company.id,
            **({"price_unit": price} if price is not None else {}),
        })
        move._action_confirm()
        move._action_assign()
        move.quantity = qty
        move.picked = True
        move._action_done()
        move.date = datetime.combine(when, datetime.min.time()).replace(hour=10)
        return move

    def _wizard(self, **values):
        return self.env["l10n.bg.stock.repost"].create({
            "company_id": self.company.id, "date_from": "2024-03-01", "date_to": "2024-03-31", **values,
        })

    def _march(self):
        receipt = self._move(self.supplier, self.stock, 10, date(2024, 3, 10), price=5.0)
        delivery = self._move(self.stock, self.customer, 4, date(2024, 3, 20))
        return receipt, delivery

    def test_moves_without_entry_get_the_entry_on_their_date(self):
        receipt, delivery = self._march()
        self.assertFalse((receipt | delivery).account_move_id, "auto_post is off: no entry at validation")
        self.assertEqual((receipt.value, delivery.value), (50.0, 20.0))
        self.categ.l10n_bg_stock_auto_post = True
        wizard = self._wizard()
        to_post, zero, no_accounts, _no_rule = wizard._classify()
        self.assertEqual(to_post, receipt | delivery)
        self.assertFalse(zero | no_accounts)
        self.assertIn("2024-03", wizard.preview)
        action = wizard.action_post()
        entries = self.env["account.move"].browse(action["domain"][0][2])
        self.assertEqual(len(entries), 2)
        self.assertTrue(all(entries.mapped("l10n_bg_stock_reposted")))
        self.assertEqual(receipt.account_move_id.date, date(2024, 3, 10))
        self.assertEqual(delivery.account_move_id.date, date(2024, 3, 20))
        self.assertEqual(receipt.account_move_id.state, "posted")

        def lines(move):
            return sorted((line.account_id.code, line.debit, line.credit) for line in move.account_move_id.line_ids)

        self.assertEqual(lines(receipt), [("301901", 0.0, 50.0), ("304901", 50.0, 0.0)])
        self.assertEqual(lines(delivery), [("304901", 0.0, 20.0), ("702901", 20.0, 0.0)])
        # повторното пускане не прави нищо
        with self.assertRaises(UserError):
            self._wizard().action_post()

    def test_zero_value_and_missing_accounts_are_reported_not_posted(self):
        no_output = self.env["product.category"].create({
            "name": "Repost without output", "property_valuation": "periodic", "property_cost_method": "fifo",
            "property_stock_valuation_account_id": self.valuation.id,
            "l10n_bg_stock_input_account_id": self.input.id,
        })
        # изрично без изходна сметка (иначе идва подразбиращата се от настройките)
        no_output.l10n_bg_stock_output_account_id = False
        other = self.env["product.product"].create({
            "name": "No output", "is_storable": True, "categ_id": no_output.id, "standard_price": 7.0})
        # без поръчка стойността идва от себестойността — 0 ⇒ движение без стойност
        unpriced = self.env["product.product"].create({
            "name": "Unpriced", "is_storable": True, "categ_id": self.categ.id, "standard_price": 0.0})
        free = self._move(self.supplier, self.stock, 3, date(2024, 3, 5), product=unpriced)
        self._move(self.supplier, self.stock, 2, date(2024, 3, 6), product=other)
        out_other = self._move(self.stock, self.customer, 1, date(2024, 3, 7), product=other)
        (self.categ | no_output).l10n_bg_stock_auto_post = True
        to_post, zero, no_accounts, _rest = self._wizard()._classify()
        self.assertIn(free, zero)
        self.assertIn(out_other, no_accounts)
        self.assertNotIn(out_other, to_post)

    def test_the_period_and_the_categories_limit_the_moves(self):
        receipt, delivery = self._march()
        april = self._move(self.supplier, self.stock, 1, date(2024, 4, 2), price=5.0)
        self.categ.l10n_bg_stock_auto_post = True
        to_post = self._wizard()._classify()[0]
        self.assertEqual(to_post, receipt | delivery)
        self.assertNotIn(april, to_post)
        other_categ = self.env["product.category"].create({"name": "Other"})
        self.assertFalse(self._wizard(category_ids=[Command.set(other_categ.ids)])._classify()[0])

    def test_remove_takes_the_wizard_entries_back(self):
        receipt, delivery = self._march()
        self.categ.l10n_bg_stock_auto_post = True
        entries = self.env["account.move"].browse(self._wizard().action_post()["domain"][0][2])
        self._wizard().action_remove()
        self.assertFalse(entries.exists())
        self.assertFalse((receipt | delivery).account_move_id)
        self.assertEqual(self._wizard()._classify()[0], receipt | delivery)
