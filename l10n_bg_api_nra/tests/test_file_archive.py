# -*- coding: utf-8 -*-
import base64
from datetime import date

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "l10n_bg_nra")
class TestNraFileArchive(TransactionCase):
    """Ф1 — архивен модел: номерация (годишен reset) + immutability."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Archive = cls.env["l10n_bg.nra.file.archive"]
        cls.company = cls.env.company

    def _make(self, file_date, content=b"hello", **kw):
        vals = {
            "file_date": file_date,
            "company_id": self.company.id,
            "declaration_type": "dec6",
            "file_format": "txt",
            "file_name": "NRA62007.TXT",
            "period_year": str(file_date.year),
            "period_month": "1",
            "file_content": base64.b64encode(content),
        }
        vals.update(kw)
        return self.Archive.create(vals)

    def test_01_numbering_yearly(self):
        """Годишен поток NRAF/ГГГГ/NNNNN + reset при нова година."""
        r1 = self._make(date(2026, 3, 15))
        r2 = self._make(date(2026, 7, 20))
        self.assertEqual(r1.name, "NRAF/2026/00001")
        self.assertEqual(r2.name, "NRAF/2026/00002")
        # нова година → броячът се нулира
        r3 = self._make(date(2027, 1, 10))
        self.assertEqual(r3.name, "NRAF/2027/00001")

    def test_02_file_size_compute(self):
        r = self._make(date(2026, 3, 15), content=b"12345")
        self.assertEqual(r.file_size, 5)

    def test_03_immutability(self):
        r = self._make(date(2026, 3, 15))
        # съдържанието/номерът НЕ се променят след създаване
        with self.assertRaises(UserError):
            r.write({"file_content": base64.b64encode(b"tampered")})
        with self.assertRaises(UserError):
            r.write({"name": "NRAF/2026/09999"})
        # note е позволено
        r.write({"note": "проверено"})
        self.assertEqual(r.note, "проверено")

    def test_04_soft_link_survives_declaration_delete(self):
        decl = self.env["nra.declaration"].create({
            "declaration_type": "xml",
            "company_id": self.company.id,
            "period_year": "2026",
            "period_month": "1",
        })
        r = self._make(date(2026, 3, 15), declaration_id=decl.id)
        self.assertEqual(r.declaration_id, decl)
        decl.unlink()
        r.invalidate_recordset()
        # архивът оцелява; връзката става празна (ondelete=set null)
        self.assertTrue(r.exists())
        self.assertFalse(r.declaration_id)
