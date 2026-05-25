# Copyright 2026 Rosen Vladimirov
# License AGPL-3 or later (https://www.gnu.org/licenses/agpl).
"""Идентификационен документ за превоз на опасни отпадъци (Приложение №8).

Чл. 12 на Наредба №1/2014: при превоз на опасни отпадъци (и в някои случаи
при превоз по републиканска мрежа) се попълват 6 еднакви екземпляра — за
товародател / превозвач / товарополучател, плюс по един за РИОСВ-ите.
"""
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class WasteIdDocument(models.Model):
    _name = "l10n.bg.waste.id.document"
    _description = "Annex 8 - Hazardous Waste Transport Identification Document"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, name"

    name = fields.Char(
        string="Document #",
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
        tracking=True,
    )
    date = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("sender_signed", "Signed by Sender"),
            ("carrier_signed", "Signed by Carrier"),
            ("completed", "Completed"),
            ("sent_to_riosv", "Sent to RIOSV"),
        ],
        default="draft",
        tracking=True,
    )

    # --- Section A — Goods (load) ---------------------------------------
    waste_code_id = fields.Many2one(
        "l10n.bg.waste.code",
        string="Waste Code",
        required=True,
        domain="[('level','=','code'),('is_hazardous','=',True)]",
    )
    origin_description = fields.Text(string="Origin (Technological Process)")
    hazard_properties = fields.Char(string="Hazard Properties (H-codes)")
    un_number = fields.Char(string="UN Number")
    un_class = fields.Char(string="UN Class")
    un_cipher = fields.Char(string="UN Cipher")
    transport_regulation = fields.Selection(
        [
            ("adr", "ADR"),
            ("rid", "RID"),
            ("imdg", "IMDG-code"),
            ("icao", "ICAO"),
        ],
        string="International Regulation",
    )
    quantity_ton = fields.Float(string="Quantity (ton)", digits=(16, 3))
    quantity_m3 = fields.Float(string="Quantity (m³)", digits=(16, 3))
    handover_type = fields.Selection(
        [
            ("producer", "From the producing site"),
            ("intermediate", "After intermediate operations"),
        ],
        string="Handover Type",
    )

    # --- Section A — Sender ---------------------------------------------
    sender_partner_id = fields.Many2one("res.partner", string="Sender")

    # --- Section B — Carrier --------------------------------------------
    carrier_partner_id = fields.Many2one("res.partner", string="Carrier")
    vehicle_type = fields.Char(string="Vehicle Type")
    vehicle_plate = fields.Char(string="Vehicle Plate")
    has_packaging = fields.Boolean(string="Packaged Load")
    packaging_type = fields.Selection(
        [
            ("container", "Container"),
            ("bags", "Bags"),
            ("barrels", "Barrels"),
            ("other", "Other"),
        ],
    )
    route = fields.Text(string="Route")

    # --- Section C — Receiver -------------------------------------------
    receiver_partner_id = fields.Many2one("res.partner", string="Receiver")
    treatment_type = fields.Selection(
        [
            ("recovery", "Recovery"),
            ("disposal", "Disposal"),
            ("intermediate", "Intermediate Operations Only"),
        ],
    )
    delivery_date = fields.Date(string="Delivery Date")
    delivery_time = fields.Char(string="Delivery Time (HH:MM)")
    delivery_vehicle_plate = fields.Char(string="Delivery Vehicle Plate")

    # --- Link to stock --------------------------------------------------
    picking_id = fields.Many2one("stock.picking", string="Stock Picking")
    note = fields.Text()

    # --- Sequence + lifecycle -------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = seq.next_by_code("l10n.bg.waste.id.document") or _("New")
        return super().create(vals_list)

    def action_mark_completed(self):
        self.write({"state": "completed"})

    def action_send_to_riosv(self):
        for rec in self:
            if rec.state != "completed":
                raise ValidationError(
                    _("Document %s must be marked Completed before sending to RIOSV.") % rec.name
                )
            rec.message_post(
                body=_("Marked as sent to the territorial RIOSV office."),
                subtype_xmlid="mail.mt_note",
            )
            rec.state = "sent_to_riosv"
