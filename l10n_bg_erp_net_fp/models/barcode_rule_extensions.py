# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Extend the core `barcode.rule` with **routing hints** so the proxy's
WebSocket reader feed can target a specific field on a specific form
in the Odoo backend.

Without these hints, a scan goes through the core barcode_service bus
and any active form-view handler may pick it up — POS / inventory /
attendance, etc. With them, the live_refresh barcode_handler can
dispatch the parsed value straight to the right `<input>` even when
the active view is something else entirely (e.g. operator scans a
GTIN into a custom MO form while the navbar is over a different
record).

Three new fields, all optional:

    l10n_bg_target_model_id    — ir.model the rule targets
    l10n_bg_target_field       — name of the field on that model
    l10n_bg_target_form_xmlid  — optional, narrows to a specific
                                 form view (xml_id of the
                                 ir.ui.view); when empty the
                                 dispatcher matches by model only.

And one classmethod-style helper on `barcode.nomenclature`:

    parse_for_target(barcode)  →  dict({
        rule_id, type, encoding, base_code, parsed_value,
        target: {model, field, form_xmlid}
    })  |  None
"""
from odoo import api, fields, models


class BarcodeRule(models.Model):
    _inherit = "barcode.rule"

    l10n_bg_target_model_id = fields.Many2one(
        "ir.model",
        string="Target Model",
        ondelete="cascade",
        index=True,
        help="When set, the barcode_handler in the browser will write "
        "the parsed value into a field of this model on the currently-"
        "open Form view. Leave empty to fall back to the global "
        "barcode_service dispatch.",
    )
    l10n_bg_target_field = fields.Char(
        string="Target Field",
        help="Name of the field on `Target Model` that receives the "
        "parsed value. Must be a Char/Float/Monetary/Integer.",
    )
    l10n_bg_target_form_xmlid = fields.Char(
        string="Target Form (xml_id)",
        help="Optional — narrows targeting to one specific form view "
        "(e.g. 'stock.view_picking_form'). When empty, any open form "
        "of `Target Model` accepts the scan.",
    )


class BarcodeNomenclature(models.Model):
    _inherit = "barcode.nomenclature"

    @api.model
    def parse_for_target(self, barcode):
        """Run the configured nomenclature parse on `barcode` and
        return — in addition to the parsed value — the routing hints
        declared on the matching rule.

        Returns:
            dict with keys:
                rule_id        — barcode.rule id of the match
                type           — rule.type ('product', 'weight', etc.)
                encoding       — rule.encoding (ean13, gs1, ...)
                base_code      — barcode minus the prefix/check digit
                                 (as `parse_barcode` returns)
                parsed_value   — the value the rule extracts
                                 (weight in kg for weight rules,
                                 price in currency units for price
                                 rules, etc.)
                target         — {model, field, form_xmlid} taken
                                 from the matching rule's
                                 l10n_bg_target_* fields. Empty dict
                                 if no targeting was configured.
            or None if no rule matches.

        Pure ORM call — safe to expose over JSON-RPC from the JS
        handler (no privilege checks beyond standard ACL on
        barcode.nomenclature).
        """
        self.ensure_one()
        parsed = self.parse_barcode(barcode)
        if not parsed or parsed.get("type") == "error":
            return None
        rule = self.rule_ids.filtered(
            lambda r: r.type == parsed.get("type")
            and r.encoding == parsed.get("encoding")
        )[:1]
        target = {}
        if rule:
            if rule.l10n_bg_target_model_id:
                target["model"] = rule.l10n_bg_target_model_id.model
            if rule.l10n_bg_target_field:
                target["field"] = rule.l10n_bg_target_field
            if rule.l10n_bg_target_form_xmlid:
                target["form_xmlid"] = rule.l10n_bg_target_form_xmlid
        return {
            "rule_id": rule.id if rule else False,
            "type": parsed.get("type"),
            "encoding": parsed.get("encoding"),
            "base_code": parsed.get("base_code") or parsed.get("code"),
            "parsed_value": parsed.get("value"),
            "target": target,
        }
