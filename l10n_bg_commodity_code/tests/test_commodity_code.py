# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
"""Тестове на модела за кодовете по КН (HS6 → КН8 → TARIC10)."""
from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged

from ..hooks import migrate_legacy_codes
from ..wizards.l10n_bg_cn_suggest import code_from_name


@tagged("post_install", "-at_install")
class TestCommodityCode(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Template = cls.env["product.template"]
        cls.Product = cls.env["product.product"]
        cls.CnCode = cls.env["l10n.bg.cn.code"]
        # година без справочник в базата — за проверките „само формат“
        cls.year_empty = 2099
        # година със справочник — за проверките „съществува в КН“
        cls.year_loaded = 2098
        cls.CnCode.create([
            {"code": "48171000", "year": cls.year_loaded, "name": "Envelopes"},
            {"code": "39201024", "year": cls.year_loaded, "name": "Film",
             "supplementary_unit": "m2"},
        ])
        cls.attribute = cls.env["product.attribute"].create({
            "name": "Size (commodity test)",
            "create_variant": "always",
            "value_ids": [(0, 0, {"name": "A4"}), (0, 0, {"name": "A5"})],
        })

    def _goods(self, **vals):
        return self.Product.create({"name": "Goods", "type": "consu", **vals})

    def _two_variant_template(self):
        return self.Template.create({
            "name": "Envelope (variants)",
            "type": "consu",
            "attribute_line_ids": [(0, 0, {
                "attribute_id": self.attribute.id,
                "value_ids": [(6, 0, self.attribute.value_ids.ids)],
            })],
        })

    # ------------------------------------------------------------------
    def test_01_levels_from_taric10(self):
        product = self._goods(l10n_bg_commodity_code="4817100000")
        self.assertEqual(product.l10n_bg_cn8, "48171000")
        self.assertEqual(product.l10n_bg_hs6, "481710")
        self.assertEqual(product.l10n_bg_taric10, "4817100000")

    def test_02_levels_from_cn8_no_padding(self):
        product = self._goods(l10n_bg_commodity_code="48171000")
        self.assertEqual(product.l10n_bg_cn8, "48171000")
        self.assertEqual(product.l10n_bg_hs6, "481710")
        # TARIC10 никога не се измисля като КН8 + „00“
        self.assertFalse(product.l10n_bg_taric10)

    def test_03_constraint_and_normalization(self):
        product = self._goods(l10n_bg_commodity_code="4817 10 00")
        self.assertEqual(product.l10n_bg_commodity_code, "48171000")
        for bad in ("481710", "4817100", "481710000", "48171000AB", "48-17-10-00"):
            with self.assertRaises(ValidationError, msg=bad), self.cr.savepoint():
                product.write({"l10n_bg_commodity_code": bad})
                product.flush_recordset()

    def test_04_saft_code(self):
        service = self.Product.create({"name": "Service", "type": "service"})
        self.assertEqual(
            service._l10n_bg_saft_commodity_code(date(self.year_loaded, 5, 1)),
            "00000000",
        )
        missing = self._goods()
        self.assertEqual(missing._l10n_bg_saft_commodity_code(date(self.year_loaded, 5, 1)), "0")
        known = self._goods(l10n_bg_commodity_code="4817100000")
        self.assertEqual(
            known._l10n_bg_saft_commodity_code(date(self.year_loaded, 5, 1)), "48171000"
        )
        unknown = self._goods(l10n_bg_commodity_code="96121090")
        # година със справочник: кодът го няма → „0“ и причина
        self.assertEqual(unknown._l10n_bg_saft_commodity_code(date(self.year_loaded, 5, 1)), "0")
        self.assertTrue(unknown._l10n_bg_commodity_issues(date(self.year_loaded, 5, 1)))
        # година без справочник: форматът решава
        self.assertEqual(
            unknown._l10n_bg_saft_commodity_code(date(self.year_empty, 5, 1)), "96121090"
        )
        self.assertFalse(unknown._l10n_bg_commodity_issues(date(self.year_empty, 5, 1)))
        self.assertTrue(missing._l10n_bg_commodity_issues(date(self.year_empty, 5, 1)))
        self.assertFalse(service._l10n_bg_commodity_issues(date(self.year_empty, 5, 1)))

    def test_05_state_and_search(self):
        missing = self._goods(name="Goods without code (state)")
        ok = self._goods(name="Goods with code (state)", l10n_bg_commodity_code="48171000")
        ctx = {"date": date(self.year_loaded, 1, 1)}
        self.assertEqual(missing.with_context(**ctx).l10n_bg_commodity_state, "missing")
        self.assertEqual(ok.with_context(**ctx).l10n_bg_commodity_state, "ok")
        found = self.Product.with_context(**ctx).search(
            [("l10n_bg_commodity_state", "=", "missing"), ("id", "in", (missing | ok).ids)]
        )
        self.assertEqual(found, missing)
        not_in = self._goods(l10n_bg_commodity_code="96121090")
        self.assertEqual(
            not_in.with_context(**ctx).l10n_bg_commodity_state, "not_in_nomenclature"
        )
        invalid = self.Product.with_context(**ctx).search([
            ("l10n_bg_commodity_state", "in", ("invalid_format", "not_in_nomenclature")),
            ("id", "in", (missing | ok | not_in).ids),
        ])
        self.assertEqual(invalid, not_in)

    def test_06_hs_code_single_variant(self):
        template = self.Template.create({
            "name": "Single", "type": "consu", "l10n_bg_commodity_code": "8537109199",
        })
        variant = template.product_variant_ids
        self.assertEqual(variant.l10n_bg_commodity_code, "8537109199")
        # hs_code на шаблона носи КН8, не TARIC10
        self.assertEqual(template.hs_code, "85371091")
        variant.l10n_bg_commodity_code = "48171000"
        self.assertEqual(template.hs_code, "48171000")
        self.assertEqual(template.l10n_bg_commodity_code, "48171000")
        variant.l10n_bg_commodity_code = False
        self.assertFalse(template.hs_code)

    def test_07_hs_code_variants_same_and_different(self):
        template = self._two_variant_template()
        v1, v2 = template.product_variant_ids
        # запис на шаблона пише във ВСИЧКИ варианти
        template.l10n_bg_commodity_code = "48171000"
        self.assertEqual(v1.l10n_bg_commodity_code, "48171000")
        self.assertEqual(v2.l10n_bg_commodity_code, "48171000")
        self.assertEqual(template.hs_code, "48171000")
        # различен КН8 между вариантите е позволен → hs_code празно
        v2.l10n_bg_commodity_code = "39201024"
        self.assertFalse(template.hs_code)
        self.assertFalse(template.l10n_bg_commodity_code)
        # празното на шаблона (кръгов експорт/импорт) не трие различните кодове
        template.write({"l10n_bg_commodity_code": False})
        self.assertEqual(v1.l10n_bg_commodity_code, "48171000")
        self.assertEqual(v2.l10n_bg_commodity_code, "39201024")
        # еднакъв КН8 с различен TARIC10 → общият КН8 остава
        v1.l10n_bg_commodity_code = "3920102490"
        self.assertEqual(template.hs_code, "39201024")

    def test_08_legacy_hs_code_write_fills_only_empty_variants(self):
        template = self._two_variant_template()
        v1, v2 = template.product_variant_ids
        v1.l10n_bg_commodity_code = "39201024"
        template.write({"hs_code": "4817.10.00"})
        self.assertEqual(v1.l10n_bg_commodity_code, "39201024")  # не се презаписва
        self.assertEqual(v2.l10n_bg_commodity_code, "48171000")
        # невалиден заварен код не стига до вариантите
        other = self.Template.create({"name": "Legacy HS6", "type": "consu", "hs_code": "481710"})
        self.assertFalse(other.product_variant_ids.l10n_bg_commodity_code)
        self.assertEqual(other.hs_code, "481710")

    def test_09_migration_hook(self):
        template = self.Template.create({"name": "Legacy", "type": "consu"})
        variant = template.product_variant_ids
        self.env.flush_all()
        # заварено състояние: кодът е само в hs_code на шаблона
        self.env.cr.execute(
            "UPDATE product_template SET hs_code = %s WHERE id = %s",
            ("8537 1091 99", template.id),
        )
        self.env.invalidate_all()
        migrate_legacy_codes(self.env)
        self.assertEqual(variant.l10n_bg_commodity_code, "8537109199")
        self.assertEqual(template.hs_code, "85371091")

    def test_10_suggest_from_name(self):
        self.assertEqual(code_from_name("48171000_Плик C4"), "48171000")
        self.assertEqual(code_from_name("4817100000_Плик"), "4817100000")
        self.assertFalse(code_from_name("Плик 48171000"))
        self.assertFalse(code_from_name("3800123456789_баркод"))
        empty = self._goods(name="48171000_Плик C4")
        conflict = self._goods(name="39201024_Фолио", l10n_bg_commodity_code="39206100")
        wizard = self.env["l10n.bg.cn.suggest.wizard"].with_context(
            active_model="product.product", active_ids=(empty | conflict).ids,
        ).create({})
        lines = {line.product_id: line for line in wizard.line_ids}
        self.assertTrue(lines[empty].apply)
        self.assertFalse(lines[conflict].apply)
        self.assertTrue(lines[conflict].differs)
        # нищо не е записано преди „Приложи“
        self.assertFalse(empty.l10n_bg_commodity_code)
        wizard.action_apply()
        self.assertEqual(empty.l10n_bg_commodity_code, "48171000")
        self.assertEqual(conflict.l10n_bg_commodity_code, "39206100")

    def test_11_import_parser(self):
        Import = self.env["l10n.bg.cn.code.import"]
        rows = [
            ["Комбинирана номенклатура 2026", None, None],
            ["Код по КН", "Описание", "Допълнителна мярка"],
            ["48", "Хартия и картон", None],
            ["4817", "Пликове", None],
            ["4817 10 00", "Пликове", "-"],
            [4011000, "Пневматични гуми", "p/st"],  # изядена водеща нула
            ["4810190020", "TARIC подразделение", None],
        ]
        parsed, skipped = Import._parse_rows(rows)
        self.assertEqual(parsed["48171000"], ("Пликове", ""))
        self.assertEqual(parsed["04011000"], ("Пневматични гуми", "p/st"))
        self.assertNotIn("48101900", parsed)
        self.assertEqual(skipped, 3)
        # без заглавен ред
        parsed, _skipped = Import._parse_rows([["39201024", "Фолио", "m2"]])
        self.assertEqual(parsed["39201024"], ("Фолио", "m2"))

    def test_12_migration_conflict_taric_vs_hs(self):
        """taric_code и hs_code с различен КН8 → нищо не се пише, конфликтът се отчита."""
        ok_tmpl = self.Template.create({"name": "Legacy TARIC ok", "type": "consu"})
        bad_tmpl = self.Template.create({"name": "Legacy TARIC conflict", "type": "consu"})
        self.env.flush_all()
        # колоната taric_code на стария l10n_bg_tariff_code (DDL се връща с теста)
        self.env.cr.execute(
            "ALTER TABLE product_template ADD COLUMN IF NOT EXISTS taric_code varchar")
        self.env.cr.execute(
            "UPDATE product_template SET taric_code = %s, hs_code = %s WHERE id = %s",
            ("4810190020", "48101900", ok_tmpl.id))
        self.env.cr.execute(
            "UPDATE product_template SET taric_code = %s, hs_code = %s WHERE id = %s",
            ("4810190020", "48171000", bad_tmpl.id))
        self.env.invalidate_all()
        migrate_legacy_codes(self.env)
        self.assertEqual(ok_tmpl.product_variant_ids.l10n_bg_commodity_code, "4810190020")
        self.assertFalse(bad_tmpl.product_variant_ids.l10n_bg_commodity_code)
        self.assertIn(
            (bad_tmpl.id, "4810190020", "48171000"), migrate_legacy_codes.conflicts)
        self.assertNotIn(ok_tmpl.id, [c[0] for c in migrate_legacy_codes.conflicts])
        self.assertTrue(any(
            "not migrated" in (m.body or "") for m in bad_tmpl.message_ids))

    def test_13_new_variant_inherits_common_code(self):
        template = self._two_variant_template()
        template.l10n_bg_commodity_code = "48171000"
        new_value = self.env["product.attribute.value"].create({
            "name": "A3", "attribute_id": self.attribute.id,
        })
        template.attribute_line_ids.write({"value_ids": [(4, new_value.id)]})
        self.assertEqual(len(template.product_variant_ids), 3)
        self.assertEqual(
            set(template.product_variant_ids.mapped("l10n_bg_commodity_code")), {"48171000"})
        self.assertEqual(template.hs_code, "48171000")
        # различни кодове при събратята → новият вариант остава без код
        template.product_variant_ids[0].l10n_bg_commodity_code = "39201024"
        other_value = self.env["product.attribute.value"].create({
            "name": "B5", "attribute_id": self.attribute.id,
        })
        template.attribute_line_ids.write({"value_ids": [(4, other_value.id)]})
        newest = template.product_variant_ids.filtered(
            lambda v: other_value in v.product_template_attribute_value_ids.product_attribute_value_id)
        self.assertFalse(newest.l10n_bg_commodity_code)

    def test_14_import_text_seven_digits(self):
        parsed, _skipped = self.env["l10n.bg.cn.code.import"]._parse_rows(
            [["CN8", "Description"], ["1012100", "Horses"]])
        self.assertEqual(parsed["01012100"], ("Horses", ""))
