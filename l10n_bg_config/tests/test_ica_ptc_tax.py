"""ВОП с частичен данъчен кредит и дебитното известие.

Данъкът ``l10n_bg_purchase_vat_20_ptc_ica`` е този на ядрото ``l10n_bg``:
основа в кл. 12 и 32, начислен ДДС в кл. 22, кредит в кл. 42 (ППЗДДС,
Приложение № 13 към чл. 116, ал. 1; ЗДДС чл. 84, чл. 69, ал. 1, т. 3, чл. 73).
Без клиринг през 430. Миграцията връща към него групата от старите версии.
Дебитното известие (ЗДДС чл. 115, ал. 3) е вид документ 02.
"""
from collections import defaultdict

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged

from odoo.addons.l10n_bg_config.hooks import (
    ICA_PTC_OLD_CHILDREN,
    ICA_PTC_TAX,
    fix_ica_ptc_group,
)


@tagged("post_install", "-at_install", "l10n_bg")
class TestIcaPtcTax(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country("bg")
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.chart = cls.env["account.chart.template"].with_company(cls.company)
        cls.tax_ptc = cls.chart.ref("l10n_bg_purchase_vat_20_ptc")
        cls.tax_ptc_ica = cls.chart.ref(ICA_PTC_TAX)
        cls.fp_in_eu = cls.chart.ref("fiscal_position_template_in_eu")
        cls.account_430 = cls.chart.ref("l10n_bg_430")
        cls.eu_supplier = cls.env["res.partner"].create({
            "name": "EU Supplier B2B",
            "is_company": True,
            "country_id": cls.env.ref("base.be").id,
            "vat": "BE0477472701",
        })
        cls.goods = cls.env["product.product"].create({
            "name": "Goods with partial tax credit",
            "supplier_taxes_id": [Command.set(cls.tax_ptc.ids)],
        })

    # ------------------------------------------------------------------
    # помощни
    # ------------------------------------------------------------------
    def _bill(self, price=100.0):
        bill = self.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": self.eu_supplier.id,
            "invoice_date": "2026-10-01",
            "ref": "EU-1",
            "invoice_line_ids": [Command.create({
                "product_id": self.goods.id, "quantity": 1, "price_unit": price,
            })],
        })
        bill.action_post()
        return bill

    @staticmethod
    def _tag_balances(move):
        """Салдото по таг, както го сумира двигателят tax_tags във v19."""
        res = defaultdict(float)
        for line in move.line_ids:
            for tag in line.tax_tag_ids:
                res[tag.name] += line.balance
        return {name: round(amount, 2) for name, amount in res.items()}

    @staticmethod
    def _repartition(tax):
        return sorted(
            (line.document_type, line.repartition_type, line.factor_percent,
             tuple(sorted(line.tag_ids.mapped("name"))), line.account_id.code or "")
            for line in tax.repartition_line_ids
        )

    def _make_old_group(self):
        """Пресъздава данъка така, както го правеше 19.0.8.16.0: група с две деца."""
        tags = self.env["account.chart.template"]._get_tag_mapper(self.env.ref("base.bg").id)
        acc_4531 = self.chart.ref("l10n_bg_4531")
        acc_4532 = self.chart.ref("l10n_bg_4532")

        def lines(base_tag, tax_tag, tax_account, clearing_factor):
            res = []
            for doc in ("invoice", "refund"):
                res += [
                    Command.create({"document_type": doc, "repartition_type": "base",
                                    "factor_percent": 100, "tag_ids": [Command.set(tags(base_tag))]}),
                    Command.create({"document_type": doc, "repartition_type": "tax",
                                    "factor_percent": -clearing_factor, "tag_ids": [Command.set(tags(tax_tag))],
                                    "account_id": tax_account.id}),
                    Command.create({"document_type": doc, "repartition_type": "tax",
                                    "factor_percent": clearing_factor, "account_id": self.account_430.id}),
                ]
            return res

        Tax = self.env["account.tax"]
        sale_ica = Tax.create({
            "name": "20% receivable (ICA) old", "amount": 20.0, "type_tax_use": "none",
            "tax_group_id": self.tax_ptc_ica.tax_group_id.id, "company_id": self.company.id,
            "repartition_line_ids": lines("12_1", "21", acc_4532, 100),
        })
        purchase_ica = Tax.create({
            "name": "20% Payable (ICA) old", "amount": 20.0, "type_tax_use": "none",
            "tax_group_id": self.tax_ptc_ica.tax_group_id.id, "company_id": self.company.id,
            "repartition_line_ids": lines("32", "42", acc_4531, -100),
        })
        for tax, xmlid in zip(sale_ica | purchase_ica, ICA_PTC_OLD_CHILDREN):
            self.env["ir.model.data"].create({
                "module": "account", "name": f"{self.company.id}_{xmlid}",
                "model": "account.tax", "res_id": tax.id, "noupdate": True,
            })
        group = self.tax_ptc_ica
        # старата група носеше подразбиращите се редове на разпределение, без тагове
        default_lines = [
            Command.create({"document_type": doc, "repartition_type": rtype, "factor_percent": 100})
            for doc in ("invoice", "refund") for rtype in ("base", "tax")
        ]
        group.write({
            "amount_type": "group",
            "children_tax_ids": [Command.set((sale_ica | purchase_ica).ids)],
            "repartition_line_ids": [Command.clear()] + default_lines,
        })
        group.with_context(lang="en_US").description = "20% Payable Tax Credit – Intra-Community Acquisition"
        # грешният български превод от старото CSV
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE account_tax SET description = description || jsonb_build_object('bg_BG', %s::text)"
            " WHERE id = %s", ("0% ДДС - ВОП", group.id))
        group.invalidate_recordset(["description"])
        return group, sale_ica | purchase_ica

    def _description_langs(self, tax):
        self.env.flush_all()
        self.env.cr.execute("SELECT description FROM account_tax WHERE id = %s", (tax.id,))
        return set(self.env.cr.fetchone()[0] or {})

    # ------------------------------------------------------------------
    # тестове
    # ------------------------------------------------------------------
    def test_template_tax_is_core_tax(self):
        # шаблонът вече не презаписва данъка: процент, без деца, разпределението на ядрото
        tax = self.tax_ptc_ica
        self.assertEqual(tax.amount_type, "percent")
        self.assertEqual(tax.amount, 20.0)
        self.assertFalse(tax.children_tax_ids)
        self.assertEqual(tax.fiscal_position_ids, self.fp_in_eu)
        self.assertEqual(tax.original_tax_ids, self.tax_ptc)
        expected = []
        for doc in ("invoice", "refund"):
            expected += [
                (doc, "base", 100.0, ("12_1", "32"), ""),
                (doc, "tax", 100.0, ("42",), "453100"),
                (doc, "tax", -100.0, ("22",), "453200"),
            ]
        got = [(d, r, f, t, a.replace(".", "")) for d, r, f, t, a in self._repartition(tax)]
        self.assertEqual(got, sorted(expected))
        for xmlid in ICA_PTC_OLD_CHILDREN:
            self.assertFalse(self.chart.ref(xmlid, raise_if_not_found=False))

    def test_eu_bill_goes_to_cell_22_without_430(self):
        bill = self._bill(100.0)
        self.assertEqual(bill.fiscal_position_id, self.fp_in_eu)
        self.assertEqual(bill.invoice_line_ids.tax_ids, self.tax_ptc_ica)
        self.assertEqual(self._tag_balances(bill), {"12_1": 100.0, "32": 100.0, "42": 20.0, "22": -20.0})
        self.assertFalse(bill.line_ids.filtered(lambda l: l.account_id == self.account_430))
        self.assertEqual(bill.amount_total, 100.0)

    def test_eu_bill_refund_mirrors_invoice(self):
        bill = self._bill(100.0)
        wizard = self.env["account.move.reversal"].with_context(
            active_model="account.move", active_ids=bill.ids,
        ).create({"journal_id": bill.journal_id.id, "date": "2026-10-02"})
        refund = self.env["account.move"].browse(wizard.refund_moves()["res_id"])
        refund.action_post()
        self.assertEqual(self._tag_balances(refund), {"12_1": -100.0, "32": -100.0, "42": -20.0, "22": 20.0})
        self.assertFalse(refund.line_ids.filtered(lambda l: l.account_id == self.account_430))

    def test_migration_restores_old_group(self):
        group, children = self._make_old_group()
        self.assertEqual(group.amount_type, "group")
        self.assertIn("bg_BG", self._description_langs(group))

        fixed = fix_ica_ptc_group(self.env, self.company)

        self.assertEqual(fixed, group)
        self.assertEqual(group.amount_type, "percent")
        self.assertEqual(group.amount, 20.0)
        self.assertFalse(group.children_tax_ids)
        lines = self._repartition(group)
        self.assertEqual(len(lines), 6)
        self.assertIn(("invoice", "tax", -100.0, ("22",), self.chart.ref("l10n_bg_4532").code), lines)
        self.assertFalse([l for l in lines if l[3] == ("21",) or l[4] == self.account_430.code])
        # децата се архивират, не се трият
        self.assertTrue(children.exists())
        self.assertFalse(any(children.mapped("active")))
        self.assertEqual(
            group.with_context(lang="en_US").description,
            "<div>20% Partial Tax Credit – Intra-Community Acquisition</div>",
        )
        self.assertEqual(self._description_langs(group), {"en_US"})
        # след миграцията фактурата отива в кл. 22
        bill = self._bill(50.0)
        self.assertEqual(self._tag_balances(bill), {"12_1": 50.0, "32": 50.0, "42": 10.0, "22": -10.0})
        # повторното пускане не прави нищо
        self.assertFalse(fix_ica_ptc_group(self.env, self.company))

    def test_migration_keeps_posted_lines(self):
        group, children = self._make_old_group()
        old_bill = self._bill(100.0)
        old_snapshot = [(l.account_id.id, l.balance, l.tax_tag_ids.ids, l.tax_line_id.id) for l in old_bill.line_ids]
        self.assertIn("21", self._tag_balances(old_bill))

        fix_ica_ptc_group(self.env, self.company)

        self.assertEqual(
            [(l.account_id.id, l.balance, l.tax_tag_ids.ids, l.tax_line_id.id) for l in old_bill.line_ids],
            old_snapshot,
        )
        self.assertEqual(old_bill.state, "posted")

    def test_debit_note_has_origin_and_type_02(self):
        bill = self._bill(100.0)
        wizard = self.env["account.debit.note"].with_context(
            active_model="account.move", active_ids=bill.ids,
        ).create({"reason": "Price increase", "copy_lines": True})
        action = wizard.create_debit()
        debit = self.env["account.move"].browse(action["res_id"])
        self.assertEqual(debit.debit_origin_id, bill)
        self.assertEqual(debit.l10n_bg_document_type, "02")
        self.assertEqual(bill.l10n_bg_document_type, "01")
