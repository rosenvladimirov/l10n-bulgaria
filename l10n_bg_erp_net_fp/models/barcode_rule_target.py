# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Many2many-style routing targets for `barcode.rule`.

One rule may now drive a scanned value into N different form-field
slots simultaneously (e.g. the same lot barcode lands on the PO
line, on the warehouse counter, and on the audit log card all at
once). The browser-side barcode_handler fills every matched input
it can find in the DOM; missing ones are skipped silently.

Schema:
    rule_id      — barcode.rule, cascade
    model_id     — ir.model, required (which model the field is on)
    field        — Char, required (field name)
    form_xmlid   — Char, optional (e.g. 'stock.view_picking_form')
                   when empty any open form of the model matches
    sequence     — Integer (UI ordering only)
    active       — Boolean

The proxy-side parser reads this same set via the JSON dump
endpoint, so a scan can be enriched with `data.target = [...]`
list before the envelope is bus_inject'ed.
"""
from odoo import api, fields, models


class BarcodeRuleTarget(models.Model):
    _name = "l10n.bg.barcode.rule.target"
    _description = "Barcode rule routing target (form+field)"
    _order = "sequence, id"

    rule_id = fields.Many2one(
        "barcode.rule",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    model_id = fields.Many2one(
        "ir.model",
        string="Target Model",
        required=True,
        ondelete="cascade",
        index=True,
    )
    model = fields.Char(
        related="model_id.model", store=True, readonly=True, index=True,
    )
    field = fields.Char(
        string="Target Field",
        required=True,
        help="Field name on the target model (must be a writable "
        "Char/Float/Monetary/Integer in the form view).",
    )
    form_xmlid = fields.Char(
        string="Target Form (xml_id)",
        help="Optional — narrows to one specific form view "
        "(e.g. 'stock.view_picking_form'). When empty, any open "
        "form of the target model accepts the scan.",
    )
    note = fields.Char(
        help="Free-text reminder for the admin (not used by the "
        "dispatcher).",
    )

    _sql_constraints = [
        (
            "uniq_rule_target",
            "unique(rule_id, model_id, field, form_xmlid)",
            "A barcode rule target with the same model, field and form "
            "already exists.",
        ),
    ]

    @api.depends("model_id", "field", "form_xmlid")
    def _compute_display_name(self):
        for r in self:
            parts = [r.model or "?", r.field or "?"]
            if r.form_xmlid:
                parts.append(f"@{r.form_xmlid}")
            r.display_name = " · ".join(parts)
