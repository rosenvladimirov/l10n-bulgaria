from odoo.exceptions import ValidationError
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


@tagged("post_install", "-at_install")
class TestPartnerPersonalUic(TransactionCase):
    """Лице с роля в декларациите пази своя ЕГН/ЛНЧ (l10n_bg_config 19.0.8.18.0).

    Ядрото синхронизира ДДС номера на фирмата към дъщерните контакти; без
    защитата ЕГН-то на представляващия/съставителя се заменяше с ЕИК на фирмата.
    """

    EGN = "7523169263"

    def setUp(self):
        super().setUp()
        self.company_partner = self.env["res.partner"].create({
            "name": "Фирма ЕООД", "is_company": True, "vat": "BG202588745",
        })

    def test_representative_keeps_own_egn_on_company_vat_sync(self):
        manager = self.env["res.partner"].create({
            "name": "Иван Управител", "parent_id": self.company_partner.id, "type": "represent",
        })
        manager.write({"l10n_bg_uic": self.EGN, "l10n_bg_uic_type": "bg_egn"})
        self.company_partner.write({"vat": "BG175074752"})
        self.assertEqual(manager.vat, "BG175074752", "ядрото пак синхронизира ДДС номера")
        self.assertEqual(manager.l10n_bg_uic, self.EGN)
        self.assertEqual(manager.l10n_bg_uic_type, "bg_egn")

    def test_authorized_person_keeps_own_egn(self):
        agent = self.env["res.partner"].create({
            "name": "Мария Счетоводител", "parent_id": self.company_partner.id, "type": "agent",
            "l10n_bg_uic": self.EGN, "l10n_bg_uic_type": "bg_egn",
        })
        self.company_partner.write({"vat": ""})
        self.assertEqual(agent.l10n_bg_uic, self.EGN)

    def test_plain_contact_still_follows_the_company(self):
        contact = self.env["res.partner"].create({
            "name": "Петър Служител", "parent_id": self.company_partner.id, "type": "contact",
        })
        self.company_partner.write({"vat": "BG175074752"})
        self.assertEqual(contact.l10n_bg_uic, "175074752")

    def test_invalid_egn_is_refused(self):
        manager = self.env["res.partner"].create({
            "name": "Иван Управител", "parent_id": self.company_partner.id, "type": "represent",
        })
        with self.assertRaises(ValidationError):
            manager.write({"l10n_bg_uic": "7523169264", "l10n_bg_uic_type": "bg_egn"})


@tagged("post_install", "-at_install")
class TestCoreLabels(TransactionCase):

    def test_core_labels_are_fixed(self):
        from odoo.addons.l10n_bg_config.hooks import _l10n_bg_fix_core_labels
        if not self.env["res.lang"]._lang_get("bg_BG"):
            self.env["res.lang"]._activate_lang("bg_BG")
        field = self.env["ir.model.fields"]._get("account.tax", "include_base_amount")
        field.update_field_translations("field_description", {"bg_BG": "Affect Base of Subsequent Taxes"})
        _l10n_bg_fix_core_labels(self.env)
        self.assertEqual(field.with_context(lang="bg_BG").field_description,
                         "Засяга основата на следващите данъци")
        # ръчен превод не се пипа
        field.update_field_translations("field_description", {"bg_BG": "Моят превод"})
        _l10n_bg_fix_core_labels(self.env)
        self.assertEqual(field.with_context(lang="bg_BG").field_description, "Моят превод")
