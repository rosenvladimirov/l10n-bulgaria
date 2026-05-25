# Copyright 2026 Rosen Vladimirov
# License AGPL-3 or later (https://www.gnu.org/licenses/agpl).
"""Annex 18 годишен отчет — скелетна имплементация.

В v1 излага агрегатите за календарната година (суми по код × дейност);
ръчно подаване в НИСО. v2 (бъдеще): авто-подаване щом НИСО публикува API.

UI-преводимите низове са на английски — преводът е в i18n/bg_BG.po.
"""
from odoo import _, models


class WasteAnnualReportXlsx(models.AbstractModel):
    _name = "report.l10n_bg_waste_report.report_waste_annual_xlsx"
    _description = "Annex 18 Annual Waste Report (XLSX, skeleton)"
    _inherit = "report.report_xlsx.abstract"

    def generate_xlsx_report(self, workbook, data, _objects):
        sheet = workbook.add_worksheet("Annual Summary")
        bold = workbook.add_format({"bold": True, "bg_color": "#1F3D44", "font_color": "#FAF6EE"})
        sheet.set_column(0, 0, 14)
        sheet.set_column(1, 1, 40)
        sheet.set_column(2, 2, 14)
        sheet.set_column(3, 3, 18)

        site = self.env["l10n.bg.waste.site"].browse(data["site_id"])
        sheet.write(0, 0, _("Annual Report %s") % data["year"], bold)
        sheet.write(1, 0, _("Site"))
        sheet.write(1, 1, site.name)

        sheet.write(3, 0, _("Code"), bold)
        sheet.write(3, 1, _("Description"), bold)
        sheet.write(3, 2, _("Activity"), bold)
        sheet.write(3, 3, _("Quantity (ton)"), bold)

        # Агрегация: SUM(waste_quantity_kg) групирано по code, activity за годината,
        # филтрирано по площадката (warehouse_ids).
        warehouse_ids = site.warehouse_ids.ids or [0]
        self.env.cr.execute(
            """
            SELECT c.code, c.name, COALESCE(SUM(sml.waste_quantity_kg), 0.0) / 1000.0 AS tons
            FROM stock_move_line sml
            JOIN stock_picking p ON p.id = sml.picking_id
            JOIN l10n_bg_waste_code c ON c.id = sml.waste_code_id
            JOIN stock_picking_type pt ON pt.id = p.picking_type_id
            WHERE sml.state = 'done'
              AND date_part('year', p.date_done) = %s
              AND pt.warehouse_id = ANY(%s)
            GROUP BY c.code, c.name
            ORDER BY c.code
            """,
            (data["year"], warehouse_ids),
        )
        row = 4
        for code, name, tons in self.env.cr.fetchall():
            sheet.write(row, 0, code)
            sheet.write(row, 1, name)
            sheet.write(row, 2, "")  # activity placeholder
            sheet.write(row, 3, tons)
            row += 1
