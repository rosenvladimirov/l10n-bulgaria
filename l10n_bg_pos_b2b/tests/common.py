# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


class B2bPosCommon(TestPoSCommon):
    """Общата постановка: фирма в България, B2B купувачи с пълни данни."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bg = cls.env.ref("base.bg")
        cls.de = cls.env.ref("base.de")
        company = cls.env.company
        company.country_id = cls.bg
        company.account_fiscal_country_id = cls.bg
        Partner = cls.env["res.partner"]
        cls.b2b_company = Partner.create({
            "name": "BG Buyer Ltd",
            "is_company": True,
            "vat": "BG175074752",
            "l10n_bg_uic": "175074752",
            "l10n_bg_uic_type": "bg_uic",
            "street": "1 Vitosha Blvd",
            "city": "Sofia",
            "country_id": cls.bg.id,
            "property_account_receivable_id": cls.c1_receivable.id,
        })
        cls.person = Partner.create({
            "name": "Ivan Ivanov",
            "street": "2 Rakovski Str",
            "city": "Sofia",
            "country_id": cls.bg.id,
        })

    def setUp(self):
        super().setUp()
        self.config = self.basic_config
        self.product1 = self.create_product("Product 1", self.categ_basic, 10.0, 5)

    def _sync(self, order_data):
        """Синхронизира поръчката като касата и връща записа."""
        result = self.env["pos.order"].sync_from_ui([order_data])
        return self.env["pos.order"].browse(result["pos.order"][0]["id"])

    def _invoice_count(self, order):
        # Не по pos_order_ids: това е обратното на pos.order.account_move и
        # втора фактура би ПРЕВЪРЗАЛА поръчката към себе си — броят пак е 1.
        # Броят се фактурите към купувача (всеки тест е в своя транзакция).
        return self.env["account.move"].search_count([
            ("move_type", "in", ("out_invoice", "out_refund")),
            ("partner_id.commercial_partner_id", "=", order.partner_id.commercial_partner_id.id),
        ])
