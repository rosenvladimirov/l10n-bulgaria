#  Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Regression: extract() и extract_bulk() четат ЕДНА И СЪЩА релация.

Пази срещу връщане на бъга, при който bulk SQL-ът сочеше core таблицата
на tax_tag_ids (account_account_tag_account_move_line_rel) вместо
материализираната l10n_bg_aml_account_tag_rel — dec92/НСИ числата
тогава се разминават мълчаливо от ORM пътя.
"""
from datetime import date

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestExtractBulkParity(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.tag = cls.env["account.account.tag"].create({
            "name": "99999 — Parity Test Tag",
            "applicability": "accounts",
            "l10n_bg_applicability": "god",
            "l10n_bg_position": "asset",
            "l10n_bg_extract_basis": "balance",
        })
        cls.account = cls.env["account.account"].with_company(cls.company).create({
            "name": "Parity Test Account",
            "code": "999901",
            "account_type": "asset_current",
            "tag_ids": [(4, cls.tag.id)],
        })

    def test_extract_bulk_matches_orm_extract(self):
        """Двата пътя дават идентични стойности за една и съща статия."""
        move = self.env["account.move"].create({
            "move_type": "entry",
            "date": date(2026, 6, 15),
            "journal_id": self.company_data["default_journal_misc"].id,
            "line_ids": [
                (0, 0, {"account_id": self.account.id, "debit": 730.0, "credit": 0.0}),
                (0, 0, {
                    "account_id": self.company_data["default_account_revenue"].id,
                    "debit": 0.0, "credit": 730.0,
                }),
            ],
        })
        move.action_post()
        # материализацията на account_tag_ids става при post
        self.assertIn(self.tag, move.line_ids[0].account_tag_ids)

        extractor = self.env["l10n.bg.audit.extractor"]
        args = ("god", date(2026, 6, 1), date(2026, 6, 30), self.company.id)
        orm = {r["tag_id"]: r["value"] for r in extractor.extract(*args)}
        bulk = {r["tag_id"]: r["value"] for r in extractor.extract_bulk(*args)}

        self.assertEqual(orm, bulk, "extract() and extract_bulk() must agree")
        self.assertEqual(bulk.get(self.tag.id), 730.0)
