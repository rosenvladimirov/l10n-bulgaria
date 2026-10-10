# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import B2bPosCommon


@tagged("post_install", "-at_install")
class TestB2bOrder(B2bPosCommon):
    def _local_date(self, dt):
        return fields.Datetime.context_timestamp(self.env["pos.order"], dt).date()

    # Т-B2B-01: B2B купувач без „Invoice“ → фактура, бележка, без UserError
    def test_b2b01_sync_forces_invoice(self):
        self.open_new_session()
        data = self.create_ui_order_data(
            [(self.product1, 2)], customer=self.b2b_company, is_invoiced=False
        )
        order = self._sync(data)
        self.assertTrue(order.to_invoice)
        self.assertTrue(order.l10n_bg_is_b2b)
        self.assertTrue(order.account_move)
        self.assertEqual(order.account_move.state, "posted")
        self.assertTrue(
            any("Invoice forced" in (m.body or "") for m in order.message_ids),
            "the forced invoice must be noted in the chatter",
        )

    def test_b2b01_person_is_not_forced(self):
        self.open_new_session()
        data = self.create_ui_order_data([(self.product1, 1)], customer=self.person)
        order = self._sync(data)
        self.assertFalse(order.to_invoice)
        self.assertFalse(order.account_move)
        self.assertFalse(order.l10n_bg_is_b2b)

    def test_b2b01_wholesale_flag_marks_b2b_without_forcing(self):
        # „Wholesale“ с физическо лице: B2B признак, но сървърът не измисля
        # фактура — гардът на фронтенда иска „Invoice“ преди плащането.
        self.open_new_session()
        data = self.create_ui_order_data(
            [(self.product1, 1)], customer=self.person,
            pos_order_ui_args={"l10n_bg_wholesale": True},
        )
        order = self._sync(data)
        self.assertTrue(order.l10n_bg_is_b2b)
        self.assertFalse(order.account_move)

    def test_refund_of_receipt_is_not_forced_to_credit_note(self):
        # В14: връщане на продажба без фактура не получава автоматично КИ
        self.open_new_session()
        original = self._sync(self.create_ui_order_data(
            [(self.product1, 1)], customer=self.person))
        self.assertFalse(original.account_move)
        self.person.l10n_bg_force_invoice = True
        refund_data = self.create_ui_order_data(
            [(self.product1, -1)], customer=self.person,
            payments=[(self.cash_pm1, -10.0)],
        )
        refund_data["lines"][0][2]["refunded_orderline_id"] = original.lines[0].id
        refund = self._sync(refund_data)
        self.assertFalse(refund.to_invoice)
        self.assertFalse(refund.account_move)

    # Т-B2B-04: адрес за доставка на фактурата
    def test_b2b04_shipping_partner_on_invoice(self):
        # Адресът по подразбиране на ядрото (address_get) е друг — иначе
        # тестът не различава избора на касиера от поведението на ядрото.
        self.env["res.partner"].create({
            "name": "Default warehouse Sofia",
            "type": "delivery",
            "parent_id": self.b2b_company.id,
            "street": "9 Ring Road",
            "city": "Sofia",
            "country_id": self.bg.id,
        })
        delivery = self.env["res.partner"].create({
            "name": "Warehouse Plovdiv",
            "type": "other",
            "parent_id": self.b2b_company.id,
            "street": "5 Industrial Zone",
            "city": "Plovdiv",
            "country_id": self.bg.id,
        })
        self.open_new_session()
        with_address = self._sync(self.create_ui_order_data(
            [(self.product1, 1)], customer=self.b2b_company, is_invoiced=True,
            pos_order_ui_args={"l10n_bg_shipping_partner_id": delivery.id},
        ))
        without_address = self._sync(self.create_ui_order_data(
            [(self.product1, 1)], customer=self.b2b_company, is_invoiced=True,
        ))
        self.assertEqual(with_address.account_move.partner_shipping_id, delivery)
        # без избор — адресът на ядрото (address_get(['delivery']))
        self.assertEqual(
            without_address.account_move.partner_shipping_id.id,
            self.b2b_company.address_get(["delivery"])["delivery"],
        )

    # Т-B2B-05: референцията на клиента → ref на фактурата
    def test_b2b05_client_order_ref(self):
        self.open_new_session()
        order = self._sync(self.create_ui_order_data(
            [(self.product1, 1)], customer=self.b2b_company, is_invoiced=True,
            pos_order_ui_args={"client_order_ref": "PO-2026-117"},
        ))
        self.assertEqual(order.account_move.ref, "PO-2026-117")

    # Т-B2B-07: двете дати — офлайн поръчка от вчера, синхронизирана днес
    def test_b2b07_two_dates(self):
        self.open_new_session()
        yesterday = fields.Datetime.now() - timedelta(days=1)
        order = self._sync(self.create_ui_order_data(
            [(self.product1, 1)], customer=self.b2b_company, is_invoiced=True,
            pos_order_ui_args={"date_order": fields.Datetime.to_string(yesterday)},
        ))
        move = order.account_move
        today_local = self._local_date(fields.Datetime.now())
        self.assertEqual(move.invoice_date, today_local, "issue date = actual creation")
        self.assertEqual(move.delivery_date, self._local_date(yesterday), "tax event = order date")
        self.assertEqual(move.l10n_bg_deal_date, self._local_date(yesterday))

    def test_b2b07_retail_invoice_keeps_core_dates(self):
        # Не-B2B поръчка с фактура: датите остават на ядрото
        self.open_new_session()
        order = self._sync(self.create_ui_order_data(
            [(self.product1, 1)], customer=self.person, is_invoiced=True,
        ))
        self.assertFalse(order.l10n_bg_is_b2b)
        self.assertFalse(order.account_move.delivery_date)

    # Т-B2B-08: фактурираната B2B поръчка НЕ е в записа 81 на сесията
    def test_b2b08_invoiced_order_not_in_sales_report(self):
        session = self.open_new_session()
        self._sync(self.create_ui_order_data([(self.product1, 1)]))  # 10 без фактура
        b2b = self._sync(self.create_ui_order_data(
            [(self.product1, 2)], customer=self.b2b_company, is_invoiced=True))
        self.assertTrue(b2b.account_move)
        session.post_closing_cash_details(30)
        session.close_session_from_ui()
        move = session.move_id
        self.assertEqual(move.l10n_bg_document_type, "81")
        income = move.line_ids.filtered(
            lambda line: line.account_id.account_type == "income")
        self.assertAlmostEqual(sum(income.mapped("credit")) - sum(income.mapped("debit")), 10.0)

    # Т-B2B-10: идемпотентност — една поръчка → една фактура
    def test_b2b10_one_order_one_invoice(self):
        self.open_new_session()
        data = self.create_ui_order_data(
            [(self.product1, 1)], customer=self.b2b_company, is_invoiced=True)
        order = self._sync(data)
        self.assertEqual(self._invoice_count(order), 1)
        # повторен sync на същата поръчка
        self.env["pos.order"].sync_from_ui([data])
        # повторно генериране (timeout, паралелен опит) и бекенд „Invoice“
        order._generate_pos_order_invoice()
        order.action_pos_order_invoice()
        self.assertEqual(self._invoice_count(order), 1)

    # Т-B2B-14: _post пада при sync → поръчката остава платена, без UserError
    def test_b2b14_failed_invoice_does_not_break_sync(self):
        self.open_new_session()
        data = self.create_ui_order_data(
            [(self.product1, 1)], customer=self.b2b_company, is_invoiced=True)
        Move = type(self.env["account.move"])
        with patch.object(Move, "_post", side_effect=UserError("You cannot add/modify entries prior to and inclusive of the lock date.")):
            order = self._sync(data)
        self.assertEqual(order.state, "paid")
        self.assertFalse(order.account_move)
        self.assertEqual(self._invoice_count(order), 0)
        self.assertTrue(any("could not be created" in (m.body or "") for m in order.message_ids))
        no_invoice = self.env["pos.order"].search([
            ("l10n_bg_is_b2b", "=", True), ("account_move", "=", False),
            ("state", "in", ("paid", "done")),
        ])
        self.assertIn(order, no_invoice)
        # след оправяне фактурата се издава от бекенда — пак една
        order.action_pos_order_invoice()
        self.assertEqual(self._invoice_count(order), 1)

    # Режим Б е заключен в v1
    def test_fd_invoice_mode_is_locked(self):
        with self.assertRaises(ValidationError):
            self.config.l10n_bg_b2b_default_doc_mode = "fd_invoice"

    # §10.2: без журнал за фактури B2B каса не се записва и не се отваря
    def test_invoice_journal_required(self):
        with self.assertRaises(ValidationError):
            self.config.invoice_journal_id = False
        self.env.cr.execute(
            "UPDATE pos_config SET invoice_journal_id = NULL WHERE id = %s", [self.config.id])
        self.config.invalidate_recordset(["invoice_journal_id"])
        with self.assertRaises(UserError):
            self.config.open_ui()

    def test_mode_off_allows_no_invoice_journal(self):
        self.config.l10n_bg_b2b_mode = "off"
        self.config.invoice_journal_id = False
        self.assertFalse(self.config.invoice_journal_id)
