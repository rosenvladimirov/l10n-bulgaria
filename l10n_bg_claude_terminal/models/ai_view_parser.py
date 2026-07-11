# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from lxml import etree

from odoo import api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Fields excluded from tokenization regardless of view presence.
EXCLUDED_FIELDS = {
    "id", "create_uid", "create_date", "write_uid", "write_date",
    "__last_update", "message_ids", "message_follower_ids",
    "message_attachment_count", "message_main_attachment_id",
    "message_has_error", "message_has_sms_error", "message_needaction",
    "activity_ids", "activity_state", "activity_user_id",
    "activity_summary", "activity_type_id", "activity_date_deadline",
    "access_token", "access_url", "access_warning",
}

# Basic scalar types — serialized as `{path: value}` directly.
SCALAR_TYPES = {
    "char", "text", "html", "integer", "float", "monetary",
    "boolean", "date", "datetime", "selection",
}


class AiViewParser(models.AbstractModel):
    """Parse view arch → structured field_spec for composite tokenization."""

    _name = "ai.view.parser"
    _description = "AI Tokenizer — View Arch Parser"

    @api.model
    def parse(self, model_name, view_type="form", view_id=None, _depth=0):
        """Return a list of field descriptors for the given view.

        Each descriptor is a dict:
            {"path": str, "type": str, "label": str, ...}

        For relational fields, additional keys:
            many2one: "resolve" (e.g. "display_name")
            one2many/many2many: "subfields" (list of descriptors from subview)
        """
        if _depth > 2:
            # prevent unbounded recursion via o2m→m2o→o2m loops
            return []

        if model_name not in self.env:
            raise UserError(f"Model '{model_name}' does not exist")

        Model = self.env[model_name]
        try:
            arch_info = Model.get_view(view_id=view_id, view_type=view_type)
        except Exception as exc:
            _logger.warning("ai.view.parser: get_view failed for %s/%s: %s",
                            model_name, view_type, exc)
            return []

        arch = arch_info.get("arch")
        if not arch:
            return []

        try:
            doc = etree.fromstring(arch) if isinstance(arch, str) else arch
        except Exception:
            return []

        field_nodes = doc.xpath(".//field[@name]")
        seen = set()
        ordered_names = []
        for node in field_nodes:
            fname = node.get("name")
            if fname in EXCLUDED_FIELDS or fname in seen:
                continue
            # Skip fields hidden by `invisible="1"` or `column_invisible="1"`
            if node.get("invisible") in ("1", "True") and node.get("force_save") != "1":
                continue
            if node.get("column_invisible") in ("1", "True"):
                continue
            seen.add(fname)
            ordered_names.append((fname, node))

        fields_info = Model.fields_get(
            [n for n, _ in ordered_names],
            attributes=["type", "string", "relation", "relation_field", "required"],
        )

        specs = []
        for fname, node in ordered_names:
            finfo = fields_info.get(fname) or {}
            ftype = finfo.get("type")
            label = node.get("string") or finfo.get("string") or fname

            if not ftype:
                continue

            spec = {"path": fname, "type": ftype, "label": label}

            if ftype in SCALAR_TYPES:
                specs.append(spec)
                continue

            if ftype == "many2one":
                spec["relation"] = finfo.get("relation")
                spec["resolve"] = "display_name"
                specs.append(spec)
                continue

            if ftype in ("one2many", "many2many"):
                subview_nodes = node.xpath("./list | ./tree | ./kanban")
                subfields = []
                if subview_nodes:
                    sub_arch = subview_nodes[0]
                    sub_relation = finfo.get("relation")
                    if sub_relation and sub_relation in self.env:
                        SubModel = self.env[sub_relation]
                        sub_field_nodes = sub_arch.xpath(".//field[@name]")
                        sub_names = []
                        sub_seen = set()
                        for sn in sub_field_nodes:
                            sfn = sn.get("name")
                            if sfn in EXCLUDED_FIELDS or sfn in sub_seen:
                                continue
                            if sn.get("column_invisible") in ("1", "True"):
                                continue
                            sub_seen.add(sfn)
                            sub_names.append(sfn)
                        sub_info = SubModel.fields_get(
                            sub_names,
                            attributes=["type", "string", "relation"],
                        )
                        for sfn in sub_names:
                            si = sub_info.get(sfn) or {}
                            st = si.get("type")
                            if not st:
                                continue
                            sub_spec = {
                                "path": sfn,
                                "type": st,
                                "label": si.get("string") or sfn,
                            }
                            if st == "many2one":
                                sub_spec["relation"] = si.get("relation")
                                sub_spec["resolve"] = "display_name"
                            subfields.append(sub_spec)
                spec["relation"] = finfo.get("relation")
                spec["subfields"] = subfields
                specs.append(spec)
                continue

            if ftype == "reference":
                spec["resolve"] = "display_name"
                specs.append(spec)
                continue

            # Fall-through for binary/json/etc — include path only (will be skipped in builder)
            specs.append(spec)

        return specs
