# -*- coding: utf-8 -*-
"""Търсене и сортиране по преводимото име — коректност и индекси.

Смисъл имат на база с колация ``C`` (както Odoo създава базите): там
``lower()``/``ILIKE`` не сгъват кирилицата, а сортирането е по кодова точка.
Без ICU колацията ``und-x-icu`` тестовете за сгъване/сортиране се пропускат.
"""
from unittest.mock import patch

from odoo.tests import TransactionCase, tagged

from odoo.addons.partner_multilang.models.collation import has_fold, order_collation


@tagged('post_install', '-at_install')
class TestMultilangSearch(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.lang']._activate_lang('bg_BG')
        Partner = cls.env['res.partner'].with_context(tracking_disable=True)
        cls.asimi = Partner.with_context(lang='bg_BG').create({'name': 'АСИМИ - ЕООД', 'is_company': True})
        cls.asimi.with_context(lang='en_US').write({'name': 'ASIMI - EOOD'})
        cls.byala = Partner.with_context(lang='bg_BG').create({'name': 'Бяла Звезда ООД', 'is_company': True})
        cls.byala.with_context(lang='en_US').write({'name': 'Byala Zvezda OOD'})
        cls.small = Partner.with_context(lang='bg_BG').create({'name': 'асими склад', 'is_company': True})
        cls.small.with_context(lang='en_US').write({'name': 'asimi sklad'})

    def _require_icu(self):
        if not has_fold(self.env):
            self.skipTest("Няма ICU колация und-x-icu в тази база")

    # ------------------------------------------------------------------ търсене
    def test_ilike_folds_cyrillic_case(self):
        """Малки букви намират името с главни (при колация C ядрото връща 0)."""
        self._require_icu()
        found = self.env['res.partner'].with_context(lang='bg_BG').search([('name', 'ilike', 'асими - еоод')])
        self.assertIn(self.asimi, found)

    def test_name_search_in_other_language(self):
        """Потребител на en_US намира партньора по кирилското име — и обратно."""
        self._require_icu()
        en = self.env['res.partner'].with_context(lang='en_US')
        self.assertIn(self.asimi, en.search([('display_name', 'ilike', 'асими - еоод')]))
        bg = self.env['res.partner'].with_context(lang='bg_BG')
        self.assertIn(self.byala, bg.search([('display_name', 'ilike', 'byala zvezda')]))

    def test_negative_operator_excludes_every_translation(self):
        self._require_icu()
        en = self.env['res.partner'].with_context(lang='en_US')
        found = en.search([('display_name', 'not ilike', 'асими'), ('id', 'in', (self.asimi | self.byala | self.small).ids)])
        self.assertEqual(found, self.byala)

    def test_exact_match_in_other_language(self):
        en = self.env['res.partner'].with_context(lang='en_US')
        self.assertEqual(
            en.search([('display_name', '=', 'Бяла Звезда ООД')]) & (self.asimi | self.byala), self.byala,
        )
        self.assertEqual(
            en.search([('display_name', 'in', ['Бяла Звезда ООД', 'ASIMI - EOOD'])]) & (self.asimi | self.byala),
            self.asimi | self.byala,
        )

    def test_search_uses_single_query_not_one_per_language(self):
        """Старият код правеше search() за всяко поле и всеки език (N×M)."""
        Partner = self.env['res.partner'].with_context(lang='bg_BG')
        with patch.object(type(Partner), 'search', autospec=True, side_effect=type(Partner).search) as search:
            Partner._search_display_name('ilike', 'асими')
        calls = search.call_args_list
        self.assertEqual(calls, [], "търсенето по име не бива да вика search() за всеки език")

    # ------------------------------------------------------------------ индекси
    def _index_names(self):
        self.env.cr.execute("SELECT indexname FROM pg_indexes WHERE tablename = 'res_partner'")
        return {row[0] for row in self.env.cr.fetchall()}

    def test_fold_indexes_exist(self):
        self._require_icu()
        names = self._index_names()
        self.assertIn('res_partner__name_pm_fold', names)
        self.assertIn('res_partner__complete_name_multilanguage_pm_fold', names)
        self.assertIn('res_partner__complete_name_multilanguage_bg_bg_pm_order', names)

    def test_ilike_query_uses_fold_index(self):
        """Изразът в заявката е същият като в индекса — PostgreSQL го избира.

        Мутация: ``fold()`` в заявката различен от индекса → индексът не се ползва.
        """
        self._require_icu()
        query = self.env['res.partner'].with_context(lang='bg_BG')._search([('name', 'ilike', 'асими - еоод')])
        sql_code, params = query.select().code, query.select().params
        self.env.cr.execute("SET LOCAL enable_seqscan = off")
        self.env.cr.execute("EXPLAIN " + sql_code, params)
        plan = "\n".join(row[0] for row in self.env.cr.fetchall())
        self.assertIn('res_partner__name_pm_fold', plan, plan)

    def test_order_query_uses_order_index(self):
        self._require_icu()
        query = self.env['res.partner'].with_context(lang='bg_BG')._search(
            [], order='complete_name_multilanguage', limit=80,
        )
        self.env.cr.execute("SET LOCAL enable_seqscan = off")
        self.env.cr.execute("EXPLAIN " + query.select().code, query.select().params)
        plan = "\n".join(row[0] for row in self.env.cr.fetchall())
        self.assertIn('res_partner__complete_name_multilanguage_bg_bg_pm_order', plan, plan)

    # ------------------------------------------------------------------ сортиране
    def test_order_follows_language_collation(self):
        """„асими склад“ е преди „Бяла Звезда ООД“ по азбучен ред.

        При колация ``C`` е обратно: ``Б`` (U+0411) < ``а`` (U+0430).
        Мутация: без ``COLLATE`` в ORDER BY → тестът пада.
        """
        if not order_collation(self.env, 'bg_BG'):
            self.skipTest("Няма ICU колация за bg_BG")
        ids = (self.byala | self.small).ids
        ordered = self.env['res.partner'].with_context(lang='bg_BG').search([('id', 'in', ids)], order='name')
        self.assertEqual(ordered.ids, [self.small.id, self.byala.id])
