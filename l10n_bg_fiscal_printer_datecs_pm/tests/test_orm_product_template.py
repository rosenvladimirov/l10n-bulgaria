"""
Odoo-side tests for product.template extension.

Ignored by pytest (filename matches `test_orm_*` glob in pyproject.toml).
Run via: `odoo-bin -d <db> --test-enable -i l10n_bg_fiscal_printer_datecs_pm`.
"""

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "l10n_bg_fp_datecs")
class TestProductTemplatePlu(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Reset PLU sequence to a known value so tests are deterministic.
        cls.seq = cls.env.ref(
            "l10n_bg_fiscal_printer_datecs_pm.seq_l10n_bg_fp_datecs_plu"
        )
        cls.seq.number_next_actual = 5000

    def test_auto_assign_plu_on_create(self):
        prod = self.env["product.template"].create(
            {
                "name": "Хляб ръжен",
                "list_price": 1.50,
                "available_in_pos": True,
            }
        )
        self.assertEqual(prod.l10n_bg_fp_datecs_plu_number, 5000)
        self.assertEqual(prod.l10n_bg_fp_datecs_vat_group, "А")
        self.assertEqual(prod.l10n_bg_fp_datecs_measurement_unit, "0")

    def test_manual_override_keeps_value_on_create(self):
        prod = self.env["product.template"].create(
            {
                "name": "Сирене",
                "list_price": 12.00,
                "available_in_pos": True,
                "l10n_bg_fp_datecs_plu_number": 42,
            }
        )
        self.assertEqual(prod.l10n_bg_fp_datecs_plu_number, 42)
        # Sequence not consumed
        self.assertEqual(self.seq.number_next_actual, 5000)

    def test_assign_plu_to_existing_product_via_helper(self):
        prod = self.env["product.template"].create(
            {"name": "Стар продукт", "list_price": 1.0}
        )
        prod.write({"l10n_bg_fp_datecs_plu_number": 0})  # simulate pre-module
        prod._l10n_bg_fp_datecs_assign_plu_number()
        self.assertGreater(prod.l10n_bg_fp_datecs_plu_number, 0)
