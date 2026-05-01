# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

MAX_O2M_ROWS = 100
MAX_M2M_NAMES = 20


class AiDocumentBuilder(models.AbstractModel):
    """Flatten an ORM record into structured text for embedding."""

    _name = "ai.document.builder"
    _description = "AI Tokenizer — Composite Document Builder"

    # ──────────────────────────────────────────────────────────
    # Entry point
    # ──────────────────────────────────────────────────────────

    @api.model
    def build(self, registry, record):
        """Return (text, token_count) for a single record."""
        if not record or not record.exists():
            return "", 0
        spec = self._load_spec(registry)
        if not spec:
            # Lazy: parse the arch now if the registry was never parsed.
            self.env["ai.view.registry"].browse(registry.id).action_parse_arch()
            registry.invalidate_recordset(["field_spec"])
            spec = self._load_spec(registry)

        lines = []
        lines.append("---")
        lines.append(f"Model: {record._name}")
        lines.append(f"View: {registry.view_type.capitalize() if registry.view_type else 'Form'}")
        lines.append(f"Record: {record.display_name}")
        company = record._fields.get("company_id") and record.company_id or False
        if company:
            lines.append(f"Company: {company.display_name}")
        lines.append("---")

        for item in spec:
            self._render_spec_item(record, item, lines)

        lines.append("---")
        text = "\n".join(lines)
        token_count = max(1, len(text) // 4)
        return text, token_count

    # ──────────────────────────────────────────────────────────
    # Internals
    # ──────────────────────────────────────────────────────────

    def _load_spec(self, registry):
        if not registry.field_spec:
            return []
        try:
            return json.loads(registry.field_spec)
        except Exception:
            return []

    def _render_spec_item(self, record, item, lines):
        path = item.get("path")
        ftype = item.get("type")
        label = item.get("label") or path
        if not path or not ftype:
            return
        if path not in record._fields:
            return
        # A broken compute/related in some 3rd-party module can raise at
        # attribute access (e.g. stock_move_forced_lot_multi_dimension on
        # Odoo 19 still calls uom.uom.category_id which no longer exists).
        # Skip the single field instead of failing the whole document.
        try:
            value = record[path]
        except Exception as exc:
            _logger.warning(
                "ai.document.builder: skip %s.%s — %s: %s",
                record._name, path, type(exc).__name__, exc,
            )
            return

        if ftype in ("char", "text", "html", "integer", "float", "monetary",
                     "boolean", "date", "datetime", "selection"):
            rendered = self._scalar(ftype, record, path, value)
            if rendered not in (None, "", False):
                lines.append(f"{label}: {rendered}")
            return

        if ftype == "many2one":
            if value:
                try:
                    lines.append(f"{label}: {value.display_name}")
                except Exception as exc:
                    _logger.warning(
                        "ai.document.builder: skip %s.%s display_name — %s: %s",
                        record._name, path, type(exc).__name__, exc,
                    )
            return

        if ftype == "many2many":
            if not value:
                return
            try:
                names = value[:MAX_M2M_NAMES].mapped("display_name")
            except Exception as exc:
                _logger.warning(
                    "ai.document.builder: skip %s.%s mapped display_name — %s: %s",
                    record._name, path, type(exc).__name__, exc,
                )
                return
            suffix = "" if len(value) <= MAX_M2M_NAMES else f" (+{len(value) - MAX_M2M_NAMES} more)"
            lines.append(f"{label}: {', '.join(names)}{suffix}")
            return

        if ftype == "one2many":
            self._render_one2many(item, value, lines)
            return

        if ftype == "reference":
            if value:
                try:
                    lines.append(f"{label}: {value.display_name}")
                except Exception as exc:
                    _logger.warning(
                        "ai.document.builder: skip %s.%s reference — %s: %s",
                        record._name, path, type(exc).__name__, exc,
                    )
            return

        # Binary/json/etc — skip silently.

    def _scalar(self, ftype, record, path, value):
        if value in (None, False) and ftype != "boolean":
            return ""
        if ftype == "selection":
            field = record._fields[path]
            try:
                selection = field._description_selection(record.env)
                mapping = dict(selection or [])
                return mapping.get(value, value)
            except Exception:
                return value
        if ftype == "html":
            # Strip tags crudely — embeddings don't need structure, just text.
            import re
            text = re.sub(r"<[^>]+>", " ", value or "")
            text = re.sub(r"\s+", " ", text).strip()
            return text[:2000]
        if ftype == "text":
            return (value or "").strip()[:2000]
        if ftype == "boolean":
            return "yes" if value else "no"
        return value

    def _render_one2many(self, item, lines_recordset, lines):
        label = item.get("label") or item.get("path")
        subfields = item.get("subfields") or []
        if not lines_recordset:
            return
        total = len(lines_recordset)
        rows = lines_recordset[:MAX_O2M_ROWS]
        if not subfields:
            lines.append(f"{label}: {total} item(s)")
            return
        lines.append(f"{label}:")
        # Table header
        header = ["#"] + [sf.get("label") or sf.get("path") for sf in subfields]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "|".join("---" for _ in header) + "|")
        for idx, line_rec in enumerate(rows, 1):
            cells = [str(idx)]
            for sf in subfields:
                sp = sf.get("path")
                st = sf.get("type")
                if not sp or sp not in line_rec._fields:
                    cells.append("")
                    continue
                # Defensive: any compute/related on the line field can raise
                # (broken 3rd-party module) — skip the cell, keep the row.
                try:
                    v = line_rec[sp]
                    if st == "many2one":
                        cells.append(v.display_name if v else "")
                    elif st == "many2many":
                        if not v:
                            cells.append("")
                        else:
                            names = v[:5].mapped("display_name")
                            cells.append(", ".join(names) + ("…" if len(v) > 5 else ""))
                    elif st in ("char", "text"):
                        cells.append((v or "").strip().replace("\n", " ").replace("|", "/")[:120])
                    elif st == "selection":
                        field = line_rec._fields[sp]
                        try:
                            sel = dict(field._description_selection(line_rec.env) or [])
                            cells.append(sel.get(v, v or ""))
                        except Exception:
                            cells.append(str(v or ""))
                    elif st == "boolean":
                        cells.append("yes" if v else "no")
                    else:
                        cells.append(str(v) if v not in (None, False) else "")
                except Exception as exc:
                    _logger.warning(
                        "ai.document.builder: skip %s.%s on row — %s: %s",
                        line_rec._name, sp, type(exc).__name__, exc,
                    )
                    cells.append("")
            lines.append("| " + " | ".join(cells) + " |")
        if total > MAX_O2M_ROWS:
            lines.append(f"… (+{total - MAX_O2M_ROWS} more rows)")
