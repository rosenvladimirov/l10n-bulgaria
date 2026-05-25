# Copyright 2026 Rosen Vladimirov
# License AGPL-3 or later (https://www.gnu.org/licenses/agpl).
"""Площадка — физическо местоположение, на което се извършва дейност с отпадъци.

Чл. 8, ал. 2 от Наредба №1/2014: всяка инсталация/площадка води отделна
отчетна книга. Свързваме площадката с един или повече stock.warehouse —
така stock.picking-ите от тези складове генерират записи към тази площадка.
"""
from odoo import _, api, fields, models


class WasteSite(models.Model):
    _name = "l10n.bg.waste.site"
    _description = "Waste Treatment Site"
    _order = "company_id, name"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        string="Name",
        required=True,
        tracking=True,
    )
    code = fields.Char(
        string="Internal Code",
        copy=False,
        default=lambda self: self.env["ir.sequence"].next_by_code("l10n.bg.waste.site"),
        readonly=True,
    )
    site_number = fields.Char(
        string="Site Number",
        tracking=True,
        help="Site number as referenced in the operating permit.",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Address Contact",
        help="Partner record holding the physical address of the site.",
    )
    municipality = fields.Char(string="Municipality")
    city = fields.Char(string="City / Locality")
    ekatte = fields.Char(
        string="EKATTE",
        size=5,
        help="5-digit EKATTE code of the locality (used in regulatory reports).",
    )
    riosv_office = fields.Char(
        string="RIOSV Office",
        help="The regional environmental inspectorate (RIOSV) whose "
             "territorial scope covers this site.",
    )
    warehouse_ids = fields.Many2many(
        "stock.warehouse",
        "l10n_bg_waste_site_warehouse_rel",
        "site_id",
        "warehouse_id",
        string="Linked Warehouses",
        help="Stock pickings to/from the locations of these warehouses are "
             "attributed to this site in regulatory aggregations.",
    )
    note = fields.Text()
    active = fields.Boolean(default=True)

    _code_unique = models.Constraint(
        "unique(code, company_id)",
        "Site code must be unique per company.",
    )
