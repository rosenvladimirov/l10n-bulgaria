# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Туровете на продажбата на едро: касата в браузъра, проверките — тук."""
from odoo import fields
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged("post_install", "-at_install")
class TestB2bTour(TestPointOfSaleHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        bg = env.ref("base.bg")
        company = cls.main_pos_config.company_id
        company.country_id = bg
        company.account_fiscal_country_id = bg
        cls.pos_user.group_ids += env.ref("l10n_bg_pos_b2b.group_pos_b2b")
        # ЕТ: B2B купувач, но НЕ is_company — ядрото не отмята „Invoice“
        cls.sole_trader = env["res.partner"].create({
            "name": "ET Petrov Trade",
            "l10n_bg_uic": "831826092",
            "l10n_bg_uic_type": "bg_uic",
            "street": "3 Shipka Str",
            "city": "Sofia",
            "country_id": bg.id,
        })
        cls.foreign_buyer = env["res.partner"].create({
            "name": "Deutsche Kunde GmbH",
            "is_company": True,
            "street": "Hauptstr. 1",
            "city": "Berlin",
            "country_id": env.ref("base.de").id,
        })

    def _orders(self):
        return self.env["pos.order"].search(
            [("config_id", "=", self.main_pos_config.id)], order="id")

    def _assert_one_invoice(self, order):
        self.assertTrue(order.to_invoice)
        self.assertEqual(len(order.account_move), 1)
        self.assertEqual(order.account_move.state, "posted")
        self.assertEqual(
            self.env["account.move"].search_count([
                ("move_type", "=", "out_invoice"),
                ("partner_id.commercial_partner_id", "=", order.partner_id.commercial_partner_id.id),
            ]), 1)

    # TOUR-W1 (котвата §23, TOUR-1 без ФУ): Wholesale → ЕТ → брой → една фактура
    def test_tour_wholesale_invoice(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour("l10n_bg_pos_b2b_wholesale_invoice")
        order = self._orders()[-1:]
        self.assertEqual(order.partner_id, self.sole_trader)
        self.assertTrue(order.l10n_bg_wholesale)
        self.assertTrue(order.l10n_bg_is_b2b)
        self._assert_one_invoice(order)
        move = order.account_move
        local = fields.Datetime.context_timestamp(order.with_user(self.pos_user), order.date_order).date()
        self.assertEqual(move.delivery_date, local)
        self.assertFalse(any("Invoice forced" in (m.body or "") for m in order.message_ids),
                         "the front end must mark the invoice itself, not the server")

    # TOUR-W5: Retail + B2B купувач → фактура и пак само една
    def test_tour_retail_b2b_buyer_invoiced(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour("l10n_bg_pos_b2b_retail_b2b_buyer_invoiced")
        order = self._orders()[-1:]
        self.assertEqual(order.partner_id, self.sole_trader)
        self.assertFalse(order.l10n_bg_wholesale)
        self.assertTrue(order.l10n_bg_is_b2b)
        self._assert_one_invoice(order)

    # TOUR-W9: чужд купувач — стоп преди плащането, нищо платено
    def test_tour_foreign_buyer_blocked(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour("l10n_bg_pos_b2b_foreign_buyer_blocked")
        paid = self._orders().filtered(lambda o: o.state in ("paid", "done"))
        self.assertFalse(paid)
