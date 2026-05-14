#  Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Retroactive recompute of account.move.line.account_tag_ids.

Used after:
  - changing product.l10n_bg_account_tag_ids
  - changing partner.l10n_bg_tax_tag_(receivable|payable)_ids
  - running the auto-map GOD/GFO Tags wizard
  - any bulk change to account.tag_ids
"""
import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)

_BATCH_SIZE = 10000


class L10nBgRecomputeAmlReportTagsWizard(models.TransientModel):
    _name = "l10n.bg.recompute.aml.report.tags.wizard"
    _description = "Retroactively recompute aml.account_tag_ids"

    date_from = fields.Date(
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(month=1, day=1),
    )
    date_to = fields.Date(
        required=True,
        default=fields.Date.context_today,
    )
    company_ids = fields.Many2many(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    posted_only = fields.Boolean(default=True)
    processed_count = fields.Integer(readonly=True)

    def action_recompute(self):
        self.ensure_one()
        domain = [
            ("date", ">=", self.date_from),
            ("date", "<=", self.date_to),
            ("company_id", "in", self.company_ids.ids),
        ]
        if self.posted_only:
            domain.append(("parent_state", "=", "posted"))

        amls = self.env["account.move.line"].search(domain)
        _logger.info(
            "BG aml report tag recompute: %s lines in %s..%s for companies %s",
            len(amls), self.date_from, self.date_to, self.company_ids.ids,
        )
        processed = 0
        for offset in range(0, len(amls), _BATCH_SIZE):
            chunk = amls[offset:offset + _BATCH_SIZE]
            chunk.with_context(
                l10n_bg_skip_report_tag_apply=True,
            )._l10n_bg_compute_account_tag_ids()
            self.env.cr.commit()
            processed += len(chunk)
            _logger.info("BG aml recompute: %s/%s done", processed, len(amls))

        self.processed_count = processed
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("BG Report Tags Recomputed"),
                "message": _("Processed %s move line(s).") % processed,
                "type": "success",
                "sticky": False,
            },
        }
