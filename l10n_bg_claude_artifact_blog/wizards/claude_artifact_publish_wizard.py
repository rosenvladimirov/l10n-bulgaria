# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Публикуване на няколко артефакта наведнъж — пак само като чернова."""

from odoo import _, fields, models
from odoo.exceptions import UserError


class ClaudeArtifactPublishWizard(models.TransientModel):
    _name = "claude.artifact.publish.wizard"
    _description = "Publish Claude Artifacts as Blog Drafts"

    artifact_ids = fields.Many2many("claude.artifact", string="Artifacts", required=True)
    blog_id = fields.Many2one("blog.blog", "Target Blog", required=True)
    author_id = fields.Many2one(
        "res.partner", "Author", default=lambda self: self.env.user.partner_id,
    )
    tag_ids = fields.Many2many("blog.tag", string="Tags")
    rebuild = fields.Boolean("Rebuild snippets first", default=True)

    def action_publish(self):
        self.ensure_one()
        if not self.artifact_ids:
            raise UserError(_("Select at least one artifact."))
        vals = {"blog_id": self.blog_id.id}
        if self.author_id:
            vals["author_id"] = self.author_id.id
        if self.tag_ids:
            vals["tag_ids"] = [(6, 0, self.tag_ids.ids)]
        self.artifact_ids.write(vals)
        if self.rebuild:
            self.artifact_ids.action_build()
        self.artifact_ids.action_publish_draft()
        posts = self.artifact_ids.mapped("blog_post_id")
        return {
            "type": "ir.actions.act_window",
            "name": _("Blog Drafts"),
            "res_model": "blog.post",
            "view_mode": "list,form",
            "domain": [("id", "in", posts.ids)],
        }
