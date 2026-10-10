# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged("post_install", "-at_install")
class TestB2bQuotationTour(TestPointOfSaleHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        bg = env.ref("base.bg")
        company = cls.main_pos_config.company_id
        company.country_id = bg
        company.account_fiscal_country_id = bg
        cls.pos_user.group_ids += env.ref("l10n_bg_pos_b2b.group_pos_b2b")
        cls.pos_user.group_ids += env.ref("sales_team.group_sale_salesman")
        cls.sole_trader = env["res.partner"].create({
            "name": "ET Petrov Trade",
            "l10n_bg_uic": "831826092",
            "l10n_bg_uic_type": "bg_uic",
            "street": "3 Shipka Str",
            "city": "Sofia",
            "country_id": bg.id,
        })

    # Т-SO-1: „Save as quotation“ → чернова SO с номер; офертата се отваря в
    # десния екран и се затваря
    def test_tour_save_and_print_quotation(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour("l10n_bg_pos_b2b_sale_quotation")
        order = self.env["sale.order"].search([("partner_id", "=", self.sole_trader.id)])
        self.assertEqual(len(order), 1)
        self.assertEqual(order.state, "draft")
        self.assertEqual(order.order_line.product_id.name, "Desk Pad")
