from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPrintSigner(TransactionCase):
    """Подписващият на документа: изричният на документа, иначе този, който печата."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.issuer = cls.env["res.users"].create({"name": "Issuer User", "login": "print_signer_issuer"})
        cls.printer = cls.env["res.users"].create({"name": "Printing User", "login": "print_signer_printer"})
        cls.move = cls.env["account.move"].create({"move_type": "entry"})

    def test_default_is_the_person_printing(self):
        self.assertEqual(self.move.with_user(self.printer)._get_print_signer(), self.printer)

    def test_explicit_issuer_wins_over_printing_user(self):
        self.move.print_signer_id = self.issuer
        self.assertEqual(self.move.with_user(self.printer)._get_print_signer(), self.issuer)

    def test_issuer_is_not_copied(self):
        self.move.print_signer_id = self.issuer
        self.assertFalse(self.move.copy().print_signer_id)

    def test_field_is_not_hidden_by_country_prefix(self):
        # полето трябва да остане видимо и в GR/CY фирми: config-ите крият по префикс
        self.assertFalse(self.env["account.move"]._l10n_bg_is_marked("print_signer_id"))
