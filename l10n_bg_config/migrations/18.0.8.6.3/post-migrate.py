#  Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Upgrade-time setup for l10n_bg_config 18.0.8.6.3.

Re-runs ``_setup_registration_cron`` so existing installs pick up the
refined logic: own ACTIVE cron when the publisher cron is missing OR
inactive (mandatory auto-push, independent of the often-disabled
publisher warranty cron).
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    from odoo.addons.l10n_bg_config.hooks import _setup_registration_cron
    _setup_registration_cron(env)
    _logger.info("l10n_bg_config 18.0.8.6.3 post-migrate: registration cron ensured (own active if publisher inactive)")
