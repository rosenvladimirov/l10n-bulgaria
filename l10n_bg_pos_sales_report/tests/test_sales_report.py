# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@tagged("post_install", "-at_install")
class TestPosSalesReport(TestPoSCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.country_id = cls.env.ref("base.bg")
        cls.random_customer = cls.env.ref("l10n_bg_config.partner_random_customer")

    def setUp(self):
        super().setUp()
        self.config = self.basic_config
        self.product1 = self.create_product("Product 1", self.categ_basic, 10.0, 5)

    def test_random_customer_has_15_nines(self):
        # НАП приема само 15 деветки; 12 бяха върнати
        self.assertEqual(self.random_customer.l10n_bg_uic, "9" * 15)
        self.assertFalse(self.random_customer.is_company)

    def _close_session_with_cash_order(self):
        session = self.open_new_session()
        order = self.create_ui_order_data([(self.product1, 2)], payments=[(self.cash_pm1, 20)])
        self.env["pos.order"].sync_from_ui([order])
        session.post_closing_cash_details(20)
        session.close_session_from_ui()
        return session

    def test_session_move_is_sales_report(self):
        session = self._close_session_with_cash_order()
        move = session.move_id
        self.assertTrue(move)
        self.assertEqual(move.partner_id, self.random_customer)
        self.assertEqual(move.l10n_bg_document_type, "81")
        sale_lines = move.line_ids.filtered(lambda line: line.credit and line.account_id.account_type == "income")
        self.assertTrue(sale_lines)
        self.assertEqual(sale_lines.partner_id, self.random_customer)

    def test_session_move_outside_bg_untouched(self):
        self.env.company.country_id = self.env.ref("base.be")
        session = self._close_session_with_cash_order()
        self.assertNotEqual(session.move_id.partner_id, self.random_customer)
        self.assertNotEqual(session.move_id.l10n_bg_document_type, "81")

    def test_create_only_on_pos_journal_entries(self):
        journal = self.config.journal_id
        other = self.company_data["default_journal_misc"]
        customer = self.env["res.partner"].create({"name": "Real customer"})
        Move = self.env["account.move"].with_context(l10n_bg_pos_sales_report_journal=journal.id)
        own = Move.create({"journal_id": journal.id})
        foreign = Move.create({"journal_id": other.id})
        explicit = Move.create({"journal_id": journal.id, "partner_id": customer.id})
        self.assertEqual(own.partner_id, self.random_customer)
        self.assertEqual(own.l10n_bg_document_type, "81")
        self.assertFalse(foreign.partner_id)
        self.assertNotEqual(foreign.l10n_bg_document_type, "81")
        # изричен партньор не се подменя
        self.assertEqual(explicit.partner_id, customer)
