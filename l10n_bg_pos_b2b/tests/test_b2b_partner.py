# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo.tests import tagged

from .common import B2bPosCommon


@tagged("post_install", "-at_install")
class TestB2bPartner(B2bPosCommon):
    # Т-B2B-02: признакът за B2B купувач — по един тест на случай, за да се
    # вижда кой точно пада при мутация.
    def test_b2b02_company_is_buyer(self):
        self.assertTrue(self.b2b_company.l10n_bg_is_b2b_buyer)

    def test_b2b02_sole_trader_is_buyer(self):
        # ЕТ: не е is_company, но има ЕИК
        sole_trader = self.env["res.partner"].create({
            "name": "ET Petrov",
            "l10n_bg_uic": "831826092",
            "l10n_bg_uic_type": "bg_uic",
        })
        self.assertTrue(sole_trader.l10n_bg_is_b2b_buyer)

    def test_b2b02_person_is_not_buyer(self):
        self.assertFalse(self.person.l10n_bg_is_b2b_buyer)

    def test_b2b02_non_vat_legal_entity_is_buyer(self):
        # данъчно незадължено ЮЛ (сдружение): фактура пак е задължителна
        entity = self.env["res.partner"].create({
            "name": "Sports Club Association",
            "is_company": True,
        })
        self.assertTrue(entity.l10n_bg_is_b2b_buyer)

    def test_b2b02_contact_follows_company(self):
        contact = self.env["res.partner"].create({
            "name": "Maria (buyer)",
            "parent_id": self.b2b_company.id,
        })
        self.assertTrue(contact.l10n_bg_is_b2b_buyer)

    def test_b2b02_force_invoice_flag(self):
        self.person.l10n_bg_force_invoice = True
        self.assertTrue(self.person.l10n_bg_is_b2b_buyer)

    def test_b2b02_random_customer_is_not_buyer(self):
        random_customer = self.env.ref("l10n_bg_config.partner_random_customer")
        self.assertFalse(random_customer.l10n_bg_is_b2b_buyer)

    # Т-B2B-03: липсите по чл. 114
    def test_b2b03_missing_uic_and_address(self):
        partner = self.env["res.partner"].create({
            "name": "Incomplete Ltd",
            "is_company": True,
        })
        self.assertEqual(partner._l10n_bg_check_invoice_data(), ["address", "uic"])
        self.assertEqual(partner.l10n_bg_invoice_missing, "address,uic")

    def test_b2b03_complete_partner_has_no_missing(self):
        self.assertEqual(self.b2b_company._l10n_bg_check_invoice_data(), [])

    # Т-B2B-16: ВОД / износ / чужд купувач → бекенд
    def test_b2b16_foreign_country_goes_to_backoffice(self):
        foreign = self.env["res.partner"].create({
            "name": "Deutsche Kunde GmbH",
            "is_company": True,
            "street": "Hauptstr. 1",
            "city": "Berlin",
            "country_id": self.de.id,
        })
        self.assertEqual(foreign._l10n_bg_b2b_document_route(), "backoffice")

    def test_b2b16_foreign_fiscal_position_goes_to_backoffice(self):
        intra_eu = self.env["account.fiscal.position"].create({
            "name": "Intra-EU test",
            "country_group_id": self.env["res.country.group"].create({
                "name": "EU without BG (test)",
                "country_ids": [(6, 0, self.de.ids)],
            }).id,
        })
        self.b2b_company.property_account_position_id = intra_eu
        self.assertEqual(self.b2b_company._l10n_bg_b2b_document_route(), "backoffice")

    def test_b2b16_domestic_buyer_stays_in_pos(self):
        self.assertEqual(self.b2b_company._l10n_bg_b2b_document_route(), "pos")
        self.assertEqual(self.b2b_company.l10n_bg_b2b_route, "pos")

    # Т-B2B-06: кредитната формула (сървърната част)
    def test_b2b06_credit_formula(self):
        self.env.company.account_use_credit_limit = True
        self.person.credit_limit = 500.0
        self.init_invoice("out_invoice", partner=self.person, amounts=[100.0], post=True)
        self.open_new_session()
        order = self.create_ui_order_data(
            [(self.product1, 3)], customer=self.person,
            payments=[(self.pay_later_pm, 30.0)],
        )
        self._sync(order)
        self.person.invalidate_recordset()
        self.assertEqual(self.person.l10n_bg_pos_credit_limit, 500.0)
        self.assertAlmostEqual(self.person.l10n_bg_pos_total_due, 100.0)
        self.assertAlmostEqual(self.person.l10n_bg_pos_orders_amount_due, 30.0)

    def test_b2b06_no_limit_without_company_setting(self):
        self.env.company.account_use_credit_limit = False
        self.person.credit_limit = 500.0
        self.person.invalidate_recordset()
        self.assertEqual(self.person.l10n_bg_pos_credit_limit, 0.0)

    # Зареждане в касата: новите полета са в списъка
    def test_pos_load_fields(self):
        fields_list = self.env["res.partner"]._load_pos_data_fields(self.config)
        for name in ("l10n_bg_uic", "l10n_bg_is_b2b_buyer", "l10n_bg_invoice_missing",
                     "l10n_bg_b2b_route", "l10n_bg_pos_total_due"):
            self.assertIn(name, fields_list)

    # Т-B2B-13: мултифирма — B2B купувач на друга фирма не се зарежда
    def test_b2b13_partner_loading_by_company(self):
        other_company = self.env["res.company"].create({"name": "Other BG Co"})
        foreign_b2b = self.env["res.partner"].create({
            "name": "Other company buyer",
            "is_company": True,
            "company_id": other_company.id,
        })
        loaded = {row[0] for row in self.config.get_limited_partners_loading()}
        self.assertIn(self.b2b_company.id, loaded)
        self.assertNotIn(foreign_b2b.id, loaded)
