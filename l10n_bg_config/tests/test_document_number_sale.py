from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDocumentNumberSale(TransactionCase):
    """Номерът на локален документ при продажба е нашият номер, не `ref` на клиента."""

    def _move(self, move_type, ref):
        move = self.env["account.move"].new({"move_type": move_type, "ref": ref, "state": "posted"})
        move.name = "0000012345"
        move._compute_l10n_bg_document_number()
        return move

    def test_sale_takes_our_number_not_customer_ref(self):
        move = self._move("out_invoice", "S35939")
        self.assertEqual(move.l10n_bg_document_number, move._format_l10n_bg_name("0000012345"))

    def test_sale_refund_takes_our_number(self):
        move = self._move("out_refund", "PO04274")
        self.assertEqual(move.l10n_bg_document_number, move._format_l10n_bg_name("0000012345"))

    def test_entry_still_falls_back_to_ref(self):
        # без продажба поведението е старото: ref, после name
        move = self._move("entry", "REF-1")
        self.assertEqual(move.l10n_bg_document_number, "REF-1")
