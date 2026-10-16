# -*- coding: utf-8 -*-
"""init() не взема изключителна ключалка, когато колоните вече ги има (16.10.2026).

ALTER TABLE … ADD COLUMN IF NOT EXISTS иска ACCESS EXCLUSIVE дори когато не
прави нищо — обновяването на модул, който наследява res.company, падаше с
lock timeout, докато друга транзакция чете таблицата.
"""
from unittest.mock import patch

from odoo.tests import TransactionCase, tagged
from odoo.tools import sql


@tagged("post_install", "-at_install")
class TestInitNoAlter(TransactionCase):

    def _alters_during_init(self, model):
        cr = self.env.cr
        seen = []
        original = type(cr).execute

        def execute(self_cr, query, params=None, log_exceptions=True):
            text = str(query.code if hasattr(query, "code") else query)
            if "ALTER TABLE" in text.upper():
                seen.append(text)
            return original(self_cr, query, params, log_exceptions)

        with patch.object(type(cr), "execute", execute):
            model.init()
        return seen

    def test_company_init_without_alter(self):
        self.assertTrue(sql.column_exists(self.env.cr, "res_company", "transliterate_tracking"))
        self.assertEqual(self._alters_during_init(self.env["res.company"]), [])

    def test_partner_init_without_alter(self):
        self.assertTrue(sql.column_exists(self.env.cr, "res_partner", "complete_name_multilanguage"))
        self.assertEqual(self._alters_during_init(self.env["res.partner"]), [])
