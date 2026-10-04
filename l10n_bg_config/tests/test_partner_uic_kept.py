from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPartnerUicKept(TransactionCase):
    # Формите пращат vat при всеки запис — празен и непроменен ДДС не трие ЕИК

    def test_unchanged_empty_vat_keeps_uic(self):
        partner = self.env["res.partner"].create({"name": "Без ДДС ЕООД"})
        partner.write({"l10n_bg_uic": "202588745", "l10n_bg_uic_type": "bg_uic"})
        partner.write({"vat": "", "street": "Плиска 25"})
        self.assertEqual(partner.l10n_bg_uic, "202588745")

    def test_uic_in_same_write_kept(self):
        partner = self.env["res.partner"].create({"name": "Без ДДС ЕООД"})
        partner.write({"vat": "", "l10n_bg_uic": "202588745", "l10n_bg_uic_type": "bg_uic"})
        self.assertEqual(partner.l10n_bg_uic, "202588745")

    def test_removed_vat_still_clears_derived_uic(self):
        # досегашното поведение: махнат ДДС номер маха и изведения от него ЕИК
        partner = self.env["res.partner"].create({"name": "С ДДС ЕООД"})
        partner.write({"vat": "BG202588745"})
        self.assertEqual(partner.l10n_bg_uic, "202588745")
        partner.write({"vat": ""})
        self.assertFalse(partner.l10n_bg_uic)
