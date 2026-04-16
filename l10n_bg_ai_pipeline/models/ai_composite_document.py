# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AiCompositeDocument(models.Model):
    """Re-route the existing tokenize entry point through the pipeline.

    The base module ships a monolithic ``action_tokenize_and_index`` —
    we keep the public name for backwards compatibility but push the
    actual work to ``ai.pipeline.runner``. Skill injection and any
    downstream glue (invoice posting, NRA export, …) live in pipeline
    steps.
    """

    _inherit = "ai.composite.document"

    def action_tokenize_and_index(self):
        """Run the ``tokenize`` pipeline for each document in self."""
        Runner = self.env["ai.pipeline.runner"]
        Qdrant = self.env["ai.qdrant.client"]
        overall_ok = True
        to_purge = self.browse()
        for doc in self:
            ctx = Runner.run("tokenize", doc=doc)
            if doc.state != "indexed":
                overall_ok = False
            # abort_reason = 'source_record_missing' purges the doc to
            # mirror the legacy behaviour.  Collect first, unlink once
            # at the end so we never delete the record we're iterating.
            if ctx.get("abort") and \
                    ctx.get("abort_reason") == "source_record_missing":
                if doc.qdrant_point_id:
                    try:
                        Qdrant.delete_point(doc.qdrant_point_id)
                    except Exception:
                        _logger.exception("qdrant purge failed")
                to_purge |= doc
        if to_purge:
            to_purge.unlink()
        return overall_ok
