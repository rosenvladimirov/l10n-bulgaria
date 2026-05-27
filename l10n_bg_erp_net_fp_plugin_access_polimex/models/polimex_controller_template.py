# -*- coding: utf-8 -*-
"""polimex.controller.template — каталог на познати Polimex модели.

Всеки template дефинира BOM-style "какво има в кутията":
- N magnets / strikes / motors (outputs — proxy access entries)
- N readers (inputs — observed през event stream)
- N door sensors (open contacts)
- N exit buttons (REX)
- aux relays

Apply Template (бутон на polimex.controller) → автоматично създава
съответните polimex.part записи. Преди това трябваше всеки потребител
ръчно да въвежда parts → грешки и непълни конфигурации.
"""

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PolimexControllerTemplate(models.Model):
    _name = "polimex.controller.template"
    _description = "Polimex Controller Template (model catalog)"
    _order = "sequence, name"
    _rec_name = "name"

    name = fields.Char(required=True, index=True,
                        help="Polimex model name (iCON110, iCON130, etc.).")
    code = fields.Char(required=True, index=True,
                       help="Programmatic identifier (icon110, icon130, ...).")
    sequence = fields.Integer(default=10)
    description = fields.Text()
    doors = fields.Integer(default=1, help="Number of doors / passages.")
    image_url = fields.Char(
        help="Optional product image URL (Polimex catalog).")
    active = fields.Boolean(default=True)
    line_ids = fields.One2many(
        "polimex.controller.template.line", "template_id",
        string="Parts")
    line_count = fields.Integer(compute="_compute_line_count")

    _sql_constraints = [
        ("code_uniq", "unique(code)", "Template code must be unique."),
    ]

    @api.depends("line_ids")
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)


class PolimexControllerTemplateLine(models.Model):
    _name = "polimex.controller.template.line"
    _description = "Polimex Template Part Definition"
    _order = "template_id, sequence, io_channel"

    template_id = fields.Many2one(
        "polimex.controller.template", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True,
                       help="E.g. 'Magnet Door 1' / 'Reader Door 1 External'.")
    kind = fields.Selection([
        ("magnet", "Electromagnetic lock"),
        ("strike", "Electric strike"),
        ("motor", "Gate motor"),
        ("reader", "RFID / keypad reader"),
        ("sensor", "Door / motion sensor"),
        ("button", "Exit button / REX"),
    ], required=True, default="magnet")
    io_channel = fields.Integer(
        required=True,
        help="RS-485 I/O channel (output number за outputs; reader number "
             "за readers; sensor channel за sensors).")
    access_suffix = fields.Char(
        help="Suffix for the proxy access:id (e.g. '_a' за door A). "
             "Final access_id = {controller_access_prefix}{suffix} при "
             "Apply Template. Само за output kinds (magnet/strike/motor).")


class PolimexControllerApply(models.Model):
    _inherit = "polimex.controller"

    template_id = fields.Many2one(
        "polimex.controller.template", string="Hardware Template",
        help="Polimex model template — позволява Apply Template бутона "
             "автоматично да създаде всички parts (magnets + readers + "
             "sensors + buttons) според известната hardware конфигурация.")

    def action_apply_template(self):
        """Create polimex.part records from the selected template.

        Pre-condition: template_id is set. Strategy: skip parts that
        already exist (по kind + io_channel) — не дубира при повторно
        прилагане. Полето access_suffix на template line е concat-нато
        с controller's identifier за уникален access:id (напр.
        'inner_door' + '_a' = 'inner_door_a').
        """
        Part = self.env["polimex.part"].sudo()
        created_total = 0
        for ctrl in self:
            if not ctrl.template_id:
                raise UserError(_(
                    "Controller %(name)s has no Hardware Template. "
                    "Select one and try again.", name=ctrl.name))
            existing = {(p.kind, p.io_channel)
                        for p in ctrl.part_ids}
            for line in ctrl.template_id.line_ids:
                key = (line.kind, line.io_channel)
                if key in existing:
                    continue
                vals = {
                    "controller_id": ctrl.id,
                    "name": line.name,
                    "kind": line.kind,
                    "io_channel": line.io_channel,
                    "sequence": line.sequence,
                    "active": True,
                }
                # Output kinds get an access_id
                if line.kind in ("magnet", "strike", "motor") \
                        and line.access_suffix:
                    # Use controller name prefix as base ID
                    base = (ctrl.name or "").lower()
                    base = "".join(c if c.isalnum() else "_" for c in base)
                    base = base.strip("_") or f"ctrl{ctrl.id}"
                    vals["access_id"] = f"{base}{line.access_suffix}"
                Part.create(vals)
                created_total += 1
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success" if created_total else "info",
                "message": _("%d parts created from template.") % created_total,
                "sticky": False,
            },
        }
