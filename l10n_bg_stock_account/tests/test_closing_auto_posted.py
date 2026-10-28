"""Приключването при periodic не осчетоводява auto_post движенията втори път.

Пада, ако:
  ① движение, осчетоводено веднага от auto_post (изход към виртуална локация
    със сметка), влезе и в рекласификацията по локации при приключване —
    разходът би станал двоен (Дт 615 два пъти);
  ② филтърът изключи и неосчетоводените движения (periodic без auto_post) —
    те трябва да се рекласифицират както в ядрото;
  ③ балансирането на склада при приключване не изравни складовата сметка
    точно до стойността на наличността.
"""
from odoo import Command
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestClosingAutoPosted(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.company.account_stock_journal_id = cls.company_data["default_journal_misc"]

        def account(code, account_type="asset_current"):
            return cls.env["account.account"].create({
                "name": f"Closing {code}", "code": code, "account_type": account_type,
                "company_ids": [Command.link(cls.company.id)],
            })

        cls.valuation = account("304903")
        cls.input = account("301903")
        cls.output = account("702903", "expense")
        cls.samples_acc = account("615903", "expense")
        common = {
            "property_valuation": "periodic",
            "property_cost_method": "standard",
            "property_stock_valuation_account_id": cls.valuation.id,
            "l10n_bg_stock_input_account_id": cls.input.id,
            "l10n_bg_stock_output_account_id": cls.output.id,
        }
        cls.categ_auto = cls.env["product.category"].create(
            {"name": "Closing auto", "l10n_bg_stock_auto_post": True, **common})
        cls.categ_plain = cls.env["product.category"].create(
            {"name": "Closing plain", "l10n_bg_stock_auto_post": False, **common})
        cls.product_auto = cls.env["product.product"].create({
            "name": "Closing auto product", "is_storable": True,
            "categ_id": cls.categ_auto.id, "standard_price": 5.0,
        })
        cls.product_plain = cls.env["product.product"].create({
            "name": "Closing plain product", "is_storable": True,
            "categ_id": cls.categ_plain.id, "standard_price": 7.0,
        })
        cls.stock = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1).lot_stock_id
        cls.samples = cls.env["stock.location"].create({
            "name": "Closing samples", "usage": "inventory",
            "company_id": cls.company.id,
            "valuation_account_id": cls.samples_acc.id,
        })
        cls.supplier = cls.env.ref("stock.stock_location_suppliers")

    def _move(self, product, source, dest, qty):
        move = self.env["stock.move"].create({
            "product_id": product.id,
            "product_uom_qty": qty,
            "location_id": source.id,
            "location_dest_id": dest.id,
            "company_id": self.company.id,
            "origin": "CLOSING",
        })
        move._action_confirm()
        move._action_assign()
        move.quantity = qty
        move.picked = True
        move._action_done()
        return move

    @staticmethod
    def _net(vals_list, account):
        return sum(v["debit"] - v["credit"] for v in vals_list if v["account_id"] == account.id)

    def test_closing_skips_auto_posted_moves(self):
        self._move(self.product_auto, self.supplier, self.stock, 10.0)
        self._move(self.product_plain, self.supplier, self.stock, 10.0)
        out_auto = self._move(self.product_auto, self.stock, self.samples, 3.0)
        out_plain = self._move(self.product_plain, self.stock, self.samples, 2.0)
        # предпоставка: auto_post движението е осчетоводено веднага, другото — не
        self.assertTrue(out_auto.account_move_id)
        self.assertFalse(out_plain.account_move_id)

        # ① + ② рекласификацията хваща само неосчетоводеното: 2 × 7 = 14, не 14 + 15
        reclass = self.company._get_location_valuation_vals()
        self.assertAlmostEqual(self._net(reclass, self.samples_acc), 14.0)
        self.assertAlmostEqual(self._net(reclass, self.valuation), -14.0)

        # ③ приключването изравнява склада до наличността: 7×5 + 8×7 = 91;
        # счетоводно преди него: +50 (вход auto) −15 (изход auto) = 35 → +56
        closing = self.company._action_close_stock_valuation()
        self.assertAlmostEqual(self._net(closing, self.samples_acc), 14.0)
        self.assertAlmostEqual(self._net(closing, self.valuation), 56.0)
