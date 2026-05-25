# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Extend `barcode.rule` with **N routing targets** (form+field) and
expose `barcode.nomenclature.parse_for_target(barcode)` so the
live_refresh browser handler can drive scanned values straight
into the right form/field slot.

Design: the proxy stays a thin relay — it emits raw
`barcode.scanned` envelopes containing only barcode + reader_id.
The browser handler does the parse via this method (RPC) and
fans out to every matching open form. The single source of truth
for parsing rules + routing lives here in Odoo.
"""
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class BarcodeRule(models.Model):
    _inherit = "barcode.rule"

    l10n_bg_target_ids = fields.One2many(
        "l10n.bg.barcode.rule.target",
        "rule_id",
        string="Routing targets",
        help="Each scan matching this rule fills ALL listed (model, "
        "field, form) slots simultaneously. Add as many targets as "
        "you need — the browser handler skips ones whose form isn't "
        "currently open.",
    )
    l10n_bg_target_count = fields.Integer(
        compute="_compute_l10n_bg_target_count",
        store=False,
    )

    @api.depends("l10n_bg_target_ids")
    def _compute_l10n_bg_target_count(self):
        for r in self:
            r.l10n_bg_target_count = len(r.l10n_bg_target_ids)


class BarcodeNomenclature(models.Model):
    _inherit = "barcode.nomenclature"

    @api.model
    def parse_for_target(self, barcode):
        """Parse `barcode` and return the matched rule's routing
        targets, plus the parsed value. Multi-target — the caller
        is expected to fan out to all (model, field, form) slots
        listed in `target`.

        Returns:
            {
                rule_id, type, encoding, base_code, parsed_value,
                target: [{model, field, form_xmlid}, ...],
            }
            or None if no rule matches.
        """
        self.ensure_one()
        parsed = self.parse_barcode(barcode)
        if not parsed or parsed.get("type") == "error":
            return None
        rule = self.rule_ids.filtered(
            lambda r: r.type == parsed.get("type")
            and r.encoding == parsed.get("encoding")
        )[:1]
        targets = []
        if rule:
            for t in rule.l10n_bg_target_ids.filtered("active"):
                row = {
                    "model": t.model_id.model,
                    "field": t.field,
                }
                if t.form_xmlid:
                    row["form_xmlid"] = t.form_xmlid
                targets.append(row)
        return {
            "rule_id": rule.id if rule else False,
            "type": parsed.get("type"),
            "encoding": parsed.get("encoding"),
            "base_code": parsed.get("base_code") or parsed.get("code"),
            "parsed_value": parsed.get("value"),
            "target": targets,
        }

