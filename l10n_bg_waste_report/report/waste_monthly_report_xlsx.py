# Copyright 2026 Rosen Vladimirov
# License AGPL-3 or later (https://www.gnu.org/licenses/agpl).
"""Annex 4 XLSX генератор за месечната отчетна книга.

Структура (по Наредба №1/2014, образец на Прил. №4):
* Sheet 'Header'           — фирма, ЕИК, площадка, община, ЕКАТТЕ
* Sheet 'I. Received'      — Дата · Код · Описание · Юр. лице (от) · ЕИК · Основание · Количество (тон)
* Sheet 'II. Treated'      — Дата · Код · Дейност (R/D) · Количество (тон) · Описание
* Sheet 'III. Generated'   — Дата · Код · Количество (тон)
* Sheet 'IV. Delivered'    — Дата · Код · Юр. лице (на) · ЕИК · Основание · Количество (тон)

UI-преводимите низове са на английски — българският превод се прави през
i18n/bg_BG.po, така че реалният PDF/XLSX излиза в BG щом потребителят е
с lang=bg_BG (което е стандарт за регулаторно подаване).
"""
from odoo import _, models


class WasteMonthlyReportXlsx(models.AbstractModel):
    _name = "report.l10n_bg_waste_report.report_waste_monthly_xlsx"
    _description = "Annex 4 Monthly Waste Bookkeeping (XLSX)"
    _inherit = "report.report_xlsx.abstract"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _styles(self, workbook):
        return {
            "title": workbook.add_format({"bold": True, "font_size": 14, "align": "left"}),
            "h_section": workbook.add_format({"bold": True, "font_size": 11, "bg_color": "#1F3D44", "font_color": "#FAF6EE", "align": "left"}),
            "h_col": workbook.add_format({"bold": True, "bg_color": "#8FA89E", "font_color": "#1F3D44", "border": 1, "align": "center"}),
            "cell": workbook.add_format({"border": 1, "align": "left"}),
            "num": workbook.add_format({"border": 1, "align": "right", "num_format": "#,##0.000"}),
            "date": workbook.add_format({"border": 1, "align": "center", "num_format": "dd.mm.yyyy"}),
        }

    def _site(self, data):
        return self.env["l10n.bg.waste.site"].browse(data["site_id"])

    def _warehouse_ids(self, site):
        return site.warehouse_ids.ids

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------
    def _write_header(self, sheet, styles, site, data):
        company = self.env["res.company"].browse(data["company_id"])
        sheet.set_column(0, 0, 28)
        sheet.set_column(1, 1, 42)
        rows = [
            (_("Legal Entity"), company.name),
            (_("VAT / EIK"), company.vat or ""),
            (_("Address"), (company.partner_id.contact_address_inline or "").strip()),
            (_("Site"), site.name),
            (_("Site Number"), site.site_number or ""),
            (_("Municipality"), site.municipality or ""),
            (_("Locality"), site.city or ""),
            (_("EKATTE"), site.ekatte or ""),
            (_("RIOSV"), site.riosv_office or ""),
            (_("Period"), f"{data['date_from']} - {data['date_to']}"),
        ]
        sheet.write(0, 0, _("Monthly Waste Bookkeeping - Annex 4 of Ordinance 1/2014"), styles["title"])
        for i, (k, v) in enumerate(rows, start=2):
            sheet.write(i, 0, k, styles["cell"])
            sheet.write(i, 1, v, styles["cell"])

    def _q_incoming(self, site, data):
        """Връща list dicts за раздел I. Получен отпадък."""
        domain = [
            ("state", "=", "done"),
            ("date_done", ">=", data["date_from"]),
            ("date_done", "<", data["date_to"]),
            ("picking_type_id.code", "=", "incoming"),
            ("move_line_ids.waste_code_id", "!=", False),
        ]
        if site.warehouse_ids:
            domain += [("picking_type_id.warehouse_id", "in", site.warehouse_ids.ids)]
        pickings = self.env["stock.picking"].search(domain)
        rows = []
        for p in pickings:
            for ml in p.move_line_ids.filtered(lambda l: l.waste_code_id):
                rows.append({
                    "date": p.date_done.date() if p.date_done else None,
                    "code": ml.waste_code_id.code,
                    "name": ml.waste_code_id.name,
                    "origin_name": (ml.waste_origin_partner_id or p.partner_id).name or "",
                    "origin_vat": (ml.waste_origin_partner_id or p.partner_id).vat or "",
                    "basis": p.waste_transport_doc or p.name,
                    "quantity_ton": (ml.waste_quantity_kg or 0.0) / 1000.0,
                })
        return rows

    def _q_outgoing(self, site, data):
        """Раздел IV. Предаден отпадък."""
        domain = [
            ("state", "=", "done"),
            ("date_done", ">=", data["date_from"]),
            ("date_done", "<", data["date_to"]),
            ("picking_type_id.code", "=", "outgoing"),
            ("move_line_ids.waste_code_id", "!=", False),
        ]
        if site.warehouse_ids:
            domain += [("picking_type_id.warehouse_id", "in", site.warehouse_ids.ids)]
        pickings = self.env["stock.picking"].search(domain)
        rows = []
        for p in pickings:
            for ml in p.move_line_ids.filtered(lambda l: l.waste_code_id):
                rows.append({
                    "date": p.date_done.date() if p.date_done else None,
                    "code": ml.waste_code_id.code,
                    "name": ml.waste_code_id.name,
                    "dest_name": p.partner_id.name or "",
                    "dest_vat": p.partner_id.vat or "",
                    "basis": p.waste_transport_doc or p.name,
                    "quantity_ton": (ml.waste_quantity_kg or 0.0) / 1000.0,
                })
        return rows

    def _write_table(self, sheet, styles, headers, rows, value_keys, col_widths):
        for i, w in enumerate(col_widths):
            sheet.set_column(i, i, w)
        for c, h in enumerate(headers):
            sheet.write(0, c, h, styles["h_col"])
        for r, row in enumerate(rows, start=1):
            for c, k in enumerate(value_keys):
                v = row.get(k)
                if isinstance(v, float):
                    sheet.write_number(r, c, v, styles["num"])
                elif hasattr(v, "isoformat"):
                    sheet.write_datetime(r, c, v, styles["date"])
                else:
                    sheet.write(r, c, v or "", styles["cell"])

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    def generate_xlsx_report(self, workbook, data, _objects):
        styles = self._styles(workbook)
        site = self._site(data)

        sh_header = workbook.add_worksheet("Header")
        self._write_header(sh_header, styles, site, data)

        # Section I — received
        sh1 = workbook.add_worksheet("I. Received")
        self._write_table(
            sh1, styles,
            headers=[_("Date"), _("Code"), _("Description"), _("Sender"), _("Sender VAT"), _("Basis"), _("Quantity (ton)")],
            rows=self._q_incoming(site, data),
            value_keys=["date", "code", "name", "origin_name", "origin_vat", "basis", "quantity_ton"],
            col_widths=[12, 10, 38, 32, 14, 22, 14],
        )

        # Section II — treated  (v1: skeleton — depends on MO consumption tracking)
        sh2 = workbook.add_worksheet("II. Treated")
        self._write_table(
            sh2, styles,
            headers=[_("Date"), _("Code"), _("Activity (R/D)"), _("Quantity (ton)"), _("Description")],
            rows=[],
            value_keys=["date", "code", "activity", "quantity_ton", "description"],
            col_widths=[12, 10, 14, 14, 40],
        )

        # Section III — generated (v1: skeleton)
        sh3 = workbook.add_worksheet("III. Generated")
        self._write_table(
            sh3, styles,
            headers=[_("Date"), _("Code"), _("Quantity (ton)")],
            rows=[],
            value_keys=["date", "code", "quantity_ton"],
            col_widths=[12, 10, 14],
        )

        # Section IV — delivered
        sh4 = workbook.add_worksheet("IV. Delivered")
        self._write_table(
            sh4, styles,
            headers=[_("Date"), _("Code"), _("Receiver"), _("Receiver VAT"), _("Basis"), _("Quantity (ton)")],
            rows=self._q_outgoing(site, data),
            value_keys=["date", "code", "dest_name", "dest_vat", "basis", "quantity_ton"],
            col_widths=[12, 10, 32, 14, 22, 14],
        )
