#  Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Upgrade-time setup for l10n_bg_config 18.0.8.6.0.

The registered-client push (18.0.8.6.0) wires its recurring trigger in
``post_init_hook`` via ``_setup_registration_cron`` — attaching to the
publisher „нотифи" cron when present, or creating a hidden standalone
cron otherwise. ``post_init_hook`` runs only on a *fresh* install, so
this post-migrate applies the same wiring idempotently on upgrade.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        # Fresh install: post_init_hook already handled it.
        return

    env = api.Environment(cr, SUPERUSER_ID, {})

    from odoo.addons.l10n_bg_config.hooks import _setup_registration_cron

    _setup_registration_cron(env)

    _logger.info(
        "l10n_bg_config 18.0.8.6.0 post-migrate: registration cron wired "
        "(publisher piggyback or hidden standalone)")
