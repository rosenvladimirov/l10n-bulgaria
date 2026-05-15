# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Standalone poll-until-final dispatcher (no consumer inheritance).

Attaching the engine to a host model fails in Odoo's registry rebuild
either way: an empty ``AbstractModel`` in ``_inherit`` triggers
``Many2many ... use the same table`` on the host's core M2M fields, and a
plain extra Python base triggers ``__bases__ assignment: object layout
differs``.  So the engine is its own ``queue.poll`` AbstractModel and runs
queue_job jobs *on itself* -- consumers inherit nothing, they only call::

    self.env["queue.poll"].start(
        "account.payment", recs.ids, "_my_poll_method",
        refresh={"mode": "record"},
    )

``_my_poll_method`` runs on ``env[model].browse(res_ids)`` inside a
queue_job worker; return truthy when final (stop) or falsy to keep
polling.  ``args``/``kwargs``/``refresh`` must be JSON-serializable.
The job owns *when* to refresh; the caller's descriptor owns *what*.
"""
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class QueuePoll(models.AbstractModel):
    _name = "queue.poll"
    _description = "Queue Poll Engine (poll-until-final via queue_job)"

    @api.model
    def start(self, model, res_ids, method, args=None, kwargs=None,
              refresh=None, max_attempts=20, base_delay=30, max_delay=900,
              backoff=2.0, refresh_every_tick=False, channel="root",
              identity_key=None, description=None):
        """Enqueue the first poll tick.  Returns the queue_job."""
        recs = self.env[model].browse(res_ids)
        if not hasattr(recs, method):
            raise ValueError(
                "queue.poll: %s has no method %r" % (model, method)
            )
        desc = description or "Poll %s.%s until final" % (model, method)
        return self.with_delay(
            channel=channel, description=desc, identity_key=identity_key,
        )._tick(
            model, list(res_ids), method, args or [], kwargs or {}, refresh,
            refresh_every_tick, 0, max_attempts, base_delay, max_delay,
            backoff,
        )

    def _tick(self, model, res_ids, method, args, kwargs, refresh,
              refresh_every_tick, attempt, max_attempts, base_delay,
              max_delay, backoff):
        """One poll iteration (runs as a queue_job); re-enqueues itself."""
        recs = self.env[model].browse(res_ids).exists()
        is_final = (
            True if not recs
            else bool(getattr(recs, method)(*args, **kwargs))
        )

        if is_final or refresh_every_tick:
            self._notify(model, res_ids, refresh)

        if is_final:
            return "final after %d attempt(s)" % (attempt + 1)

        if attempt + 1 >= max_attempts:
            _logger.warning(
                "queue.poll: %s.%s gave up after %d attempts (not final)",
                model, method, max_attempts,
            )
            return "not final, max attempts (%d) reached" % max_attempts

        delay = min(int(max_delay), int(base_delay * (backoff ** attempt)))
        self.with_delay(
            eta=delay,
            description="Poll %s.%s (attempt %d)" % (
                model, method, attempt + 2,
            ),
        )._tick(
            model, res_ids, method, args, kwargs, refresh,
            refresh_every_tick, attempt + 1, max_attempts, base_delay,
            max_delay, backoff,
        )
        return "not final, re-enqueued in %ss (next %d/%d)" % (
            delay, attempt + 2, max_attempts,
        )

    def _notify(self, model, res_ids, refresh):
        """Fire the caller's live-refresh descriptor (defaults applied)."""
        if not refresh:
            return
        spec = dict(refresh)
        spec.setdefault("model", model)
        spec.setdefault("res_ids", list(res_ids))
        spec.setdefault("mode", "record")
        self.env["live.refresh"].notify(**spec)
