from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPrintSignerSale(TransactionCase):
    """sale.order: издателят е изричният, иначе този, който печата."""

    def test_issuer_on_sale(self):
        Model = self.env["sale.order"]
        self.assertIn("print_signer_id", Model._fields)
        self.assertTrue(hasattr(Model, "_l10n_bg_hide_marked"))
        printer = self.env["res.users"].create({"name": "Printing User", "login": "signer_sale_printer"})
        issuer = self.env["res.users"].create({"name": "Issuer User", "login": "signer_sale_issuer"})
        record = Model.new({})
        self.assertEqual(record.with_user(printer)._get_print_signer(), printer)
        record.print_signer_id = issuer
        self.assertEqual(record.with_user(printer)._get_print_signer(), issuer)
