"""Сметката на насрещната виртуална локация в auto_post пътя.

Пази се:
  ① периодична категория с auto_post: изход към локация тип „inventory“ —
    Дт сметката на локацията / Кт склада; вход от нея — Дт склада / Кт
    сметката на локацията (както досега);
  ② насрещната сметка се взима от веригата на ядрото: модул под нас, който
    подменя насрещния ред на ядрото (напр. ``stock_lot_relabel`` — втората
    сметка на входа), важи и тук, макар auto_post пътят да строи редовете
    сам, без super.
"""
from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.stock_account.models.stock_move import StockMove as CoreStockMove


@tagged("post_install", "-at_install")
class TestCounterpartLocation(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.company.account_stock_journal_id = cls.company_data["default_journal_misc"]

        def account(code, account_type="asset_current"):
            return cls.env["account.account"].create({
                "name": f"Counterpart {code}", "code": code, "account_type": account_type,
                "company_ids": [Command.link(cls.company.id)],
            })

        cls.valuation = account("304902")
        cls.input = account("301902")
        cls.output = account("702902", "expense")
        cls.samples_acc = account("615902", "expense")
        cls.other_acc = account("498902")
        cls.categ = cls.env["product.category"].create({
            "name": "Counterpart goods",
            "property_valuation": "periodic",
            "property_cost_method": "fifo",
            "property_stock_valuation_account_id": cls.valuation.id,
            "l10n_bg_stock_input_account_id": cls.input.id,
            "l10n_bg_stock_output_account_id": cls.output.id,
            "l10n_bg_stock_auto_post": True,
        })
        cls.product = cls.env["product.product"].create({
            "name": "Counterpart product", "is_storable": True,
            "categ_id": cls.categ.id, "standard_price": 5.0,
        })
        cls.stock = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1).lot_stock_id
        cls.samples = cls.env["stock.location"].create({
            "name": "Counterpart samples", "usage": "inventory",
            "company_id": cls.company.id,
            "valuation_account_id": cls.samples_acc.id,
        })
        cls.supplier = cls.env.ref("stock.stock_location_suppliers")

    def _move(self, source, dest, qty):
        move = self.env["stock.move"].create({
            "product_id": self.product.id,
            "product_uom_qty": qty,
            "location_id": source.id,
            "location_dest_id": dest.id,
            "company_id": self.company.id,
            "origin": "COUNTERPART",
        })
        move._action_confirm()
        move._action_assign()
        move.quantity = qty
        move.picked = True
        move._action_done()
        return move

    def _dr_cr(self, move):
        lines = move.account_move_id.line_ids
        return (lines.filtered(lambda l: l.debit).account_id,
                lines.filtered(lambda l: l.credit).account_id)

    # ① ─────────────────────────────────────────────────────────────────
    def test_out_and_in_use_the_location_account(self):
        self._move(self.supplier, self.stock, 10.0)
        out = self._move(self.stock, self.samples, 3.0)
        self.assertEqual(self._dr_cr(out), (self.samples_acc, self.valuation))
        back = self._move(self.samples, self.stock, 1.0)
        self.assertEqual(self._dr_cr(back), (self.valuation, self.samples_acc))

    # ② ─────────────────────────────────────────────────────────────────
    def test_counterpart_follows_the_core_chain(self):
        """Подмяна в редовете на ядрото (като тази на ``stock_lot_relabel``)
        стига до auto_post статията — и на входа, и на изхода."""
        original = CoreStockMove._get_account_move_line_vals
        other = self.other_acc

        def substituted(move):
            vals = original(move)
            if move.location_id == self.samples or move.location_dest_id == self.samples:
                for line in vals:
                    if line["account_id"] == self.samples_acc.id:
                        line["account_id"] = other.id
            return vals

        self._move(self.supplier, self.stock, 10.0)
        with patch.object(CoreStockMove, "_get_account_move_line_vals", substituted):
            out = self._move(self.stock, self.samples, 3.0)
            back = self._move(self.samples, self.stock, 1.0)
        self.assertEqual(self._dr_cr(out), (other, self.valuation))
        self.assertEqual(self._dr_cr(back), (self.valuation, other))
