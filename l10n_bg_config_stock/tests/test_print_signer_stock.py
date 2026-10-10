from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPrintSignerStock(TransactionCase):
    """stock.picking: издателят е изричният, иначе този, който печата."""

    def test_issuer_on_stock(self):
        Model = self.env["stock.picking"]
        self.assertIn("print_signer_id", Model._fields)
        self.assertTrue(hasattr(Model, "_l10n_bg_hide_marked"))
        printer = self.env["res.users"].create({"name": "Printing User", "login": "signer_stock_printer"})
        issuer = self.env["res.users"].create({"name": "Issuer User", "login": "signer_stock_issuer"})
        record = Model.new({})
        self.assertEqual(record.with_user(printer)._get_print_signer(), printer)
        record.print_signer_id = issuer
        self.assertEqual(record.with_user(printer)._get_print_signer(), issuer)
