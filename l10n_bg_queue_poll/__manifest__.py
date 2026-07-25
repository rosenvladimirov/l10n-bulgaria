# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "Queue Poll (poll-until-condition via queue_job)",
    "version": "19.0.1.2.0",
    "category": "Technical",
    "summary": "Generic queue_job engine that polls a model method with "
               "adaptive backoff until it reports final, then live-refreshes",
    "description": """
Queue Poll
==========

A generic ``queue.poll.mixin`` for asynchronous "poll until final" work,
built on OCA ``queue_job``.

A consumer model inherits the mixin and calls
``recs._queue_poll_start("_my_poll_method", refresh={...})``.  A job is
enqueued that calls the method; while it returns falsy the job re-enqueues
itself with exponential backoff (capped) up to a maximum number of
attempts.  When the method returns truthy (final) -- or, optionally, on
every tick -- the job pushes a live-refresh notification described by the
caller-supplied refresh descriptor, via ``l10n_bg_live_refresh``.

The job owns the refresh: the consumer only declares *what* to refresh
(model / res_ids / mode / fields), not *when*.  No business logic here;
this is shared infrastructure (first consumer: InfoPay payment status).
""",
    "author": "Rosen Vladimirov, Terraros Commerce Ltd.",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "license": "LGPL-3",
    "depends": ["queue_job", "l10n_bg_live_refresh"],
    "installable": True,
}
