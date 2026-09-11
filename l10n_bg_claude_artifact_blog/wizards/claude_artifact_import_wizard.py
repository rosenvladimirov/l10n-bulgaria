# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Ръчният вход: прикачен файл или поставен текст.

Втори канал наред с `collect` през RPC — качването не зависи от MCP връзка,
а има случаи, в които артефактът вече е на диска.
"""

import base64
import binascii

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ClaudeArtifactImportWizard(models.TransientModel):
    _name = "claude.artifact.import.wizard"
    _description = "Import Claude Artifact"

    name = fields.Char("Title", help="Leave empty to take the artifact own title.")
    source_format = fields.Selection(
        [("html", "HTML"), ("markdown", "Markdown")], default="html", required=True,
    )
    upload_file = fields.Binary("Artifact File", attachment=False)
    upload_filename = fields.Char()
    pasted_source = fields.Text(
        "Pasted Source", help="Paste the artifact markup here instead of a file.",
    )
    source_url = fields.Char("Artifact URL")
    session_ref = fields.Char("Session")
    blog_id = fields.Many2one("blog.blog", "Target Blog")
    author_id = fields.Many2one(
        "res.partner", "Author", default=lambda self: self.env.user.partner_id,
    )
    tag_ids = fields.Many2many("blog.tag", string="Tags")
    build_now = fields.Boolean("Build snippets right away", default=True)

    @api.onchange("upload_filename")
    def _onchange_upload_filename(self):
        """Разширението казва формата — .md не е HTML, колкото и да прилича."""
        name = (self.upload_filename or "").lower()
        if name.endswith((".md", ".markdown")):
            self.source_format = "markdown"
        elif name.endswith((".html", ".htm")):
            self.source_format = "html"

    def action_import(self):
        self.ensure_one()
        source = self._read_source()
        payload = {
            "title": self.name or "",
            "content": source,
            "format": self.source_format,
            "url": self.source_url or "",
            "session": self.session_ref or "",
            "build": self.build_now,
        }
        if self.blog_id:
            payload["blog_id"] = self.blog_id.id
        result = self.env["claude.artifact"].collect(payload)
        artifact = self.env["claude.artifact"].browse(result["id"])
        artifact_vals = {}
        if self.author_id:
            artifact_vals["author_id"] = self.author_id.id
        if self.tag_ids:
            artifact_vals["tag_ids"] = [(6, 0, self.tag_ids.ids)]
        if artifact_vals:
            artifact.write(artifact_vals)
        return {
            "type": "ir.actions.act_window",
            "res_model": "claude.artifact",
            "res_id": artifact.id,
            "view_mode": "form",
        }

    def _read_source(self):
        self.ensure_one()
        if self.upload_file:
            try:
                raw = base64.b64decode(self.upload_file)
            except (binascii.Error, ValueError) as error:
                raise UserError(_("The uploaded file could not be decoded.")) from error
            for encoding in ("utf-8", "utf-8-sig", "cp1251"):
                try:
                    return raw.decode(encoding)
                except UnicodeDecodeError:
                    continue
            raise UserError(
                _("The uploaded file is not UTF-8 nor CP1251 text.")
            )
        if (self.pasted_source or "").strip():
            return self.pasted_source
        raise UserError(_("Upload a file or paste the artifact source."))
