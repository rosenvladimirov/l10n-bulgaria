# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class QueuePollMixin(models.AbstractModel):
    """Poll a model method with adaptive backoff until it reports final.

    Inherit this mixin on a model, then::

        recs._queue_poll_start(
            "_my_poll_method",
            kwargs={"token": tok},
            refresh={"model": "account.payment", "mode": "record"},
        )

    ``_my_poll_method(*args, **kwargs)`` runs on the same recordset inside a
    queue_job worker and must return a truthy value when the polled state is
    final (stop) or a falsy value to keep polling.  While not final the job
    re-enqueues itself with exponential, capped backoff up to
    ``max_attempts``.  On final (or every tick if ``refresh_every_tick``) the
    job pushes a live-refresh through ``l10n_bg_live_refresh`` using the
    caller's descriptor -- the job owns *when*, the caller owns *what*.

    All of ``args`` / ``kwargs`` / ``refresh`` must be JSON-serializable
    (they are persisted on the queue.job record).
    """

    _name = "queue.poll.mixin"
    _description = "Queue Poll Mixin (poll-until-final via queue_job)"

    def _queue_poll_start(self, poll_method, args=None, kwargs=None,
                          refresh=None, max_attempts=20, base_delay=30,
                          max_delay=900, backoff=2.0,
                          refresh_every_tick=False, channel="root",
                          identity_key=None, description=None):
        """Enqueue the first poll tick for ``self``.  Returns the job."""
        if not hasattr(self, poll_method):
            raise ValueError(
                "queue.poll: %s has no method %r" % (self._name, poll_method)
            )
        desc = description or "Poll %s.%s until final" % (
            self._name, poll_method,
        )
        delayable = self.with_delay(
            channel=channel,
            description=desc,
            identity_key=identity_key,
        )
        return delayable._queue_poll_tick(
            poll_method, args or [], kwargs or {}, refresh,
            refresh_every_tick, 0, max_attempts,
            base_delay, max_delay, backoff,
        )

    def _queue_poll_tick(self, poll_method, args, kwargs, refresh,
                         refresh_every_tick, attempt, max_attempts,
                         base_delay, max_delay, backoff):
        """One poll iteration (runs as a queue_job).  Re-enqueues itself."""
        is_final = bool(getattr(self, poll_method)(*args, **kwargs))

        if is_final or refresh_every_tick:
            self._queue_poll_notify(refresh)

        if is_final:
            return "final after %d attempt(s)" % (attempt + 1)

        if attempt + 1 >= max_attempts:
            _logger.warning(
                "queue.poll: %s.%s gave up after %d attempts (still not final)",
                self._name, poll_method, max_attempts,
            )
            return "not final, max attempts (%d) reached" % max_attempts

        delay = min(int(max_delay), int(base_delay * (backoff ** attempt)))
        self.with_delay(
            eta=delay,
            description="Poll %s.%s (attempt %d)" % (
                self._name, poll_method, attempt + 2,
            ),
        )._queue_poll_tick(
            poll_method, args, kwargs, refresh, refresh_every_tick,
            attempt + 1, max_attempts, base_delay, max_delay, backoff,
        )
        return "not final, re-enqueued in %ss (next attempt %d/%d)" % (
            delay, attempt + 2, max_attempts,
        )

    def _queue_poll_notify(self, refresh):
        """Fire the caller's live-refresh descriptor (defaults from self)."""
        if not refresh:
            return
        spec = dict(refresh)
        spec.setdefault("model", self._name)
        spec.setdefault("res_ids", self.ids)
        spec.setdefault("mode", "record")
        self.env["live.refresh"].notify(**spec)
