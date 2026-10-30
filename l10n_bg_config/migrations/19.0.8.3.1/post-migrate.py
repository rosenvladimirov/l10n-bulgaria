#  Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Upgrade-time backfill for l10n_bg_config 19.0.8.3.1.

The blacklist mechanism (8.2.0) shipped its initialization in
``post_init_hook`` plus a ``post_migrate_hook`` manifest key. Stock Odoo
does NOT honor a ``post_migrate_hook`` manifest key (only OpenUpgrade
does), and ``post_init_hook`` runs only on a *fresh* install — never on
``-u``. As a result every database upgraded past 8.2.0 is left without:

* ``ir.config_parameter`` ``l10n_bg.blacklist_key`` (Fernet key)
* a populated ``res_company.is_l10n_bg_multilanguage`` JSON

This post-migrate script applies both effects idempotently on upgrade.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        # Fresh install: post_init_hook already handled it.
        return

    env = api.Environment(cr, SUPERUSER_ID, {})

    # Ключът на черния списък вече не се слага: механизмът е махнат в
    # 19.0.8.18.3 (ADR l10n-bg-license-key-registration/0002).
    companies = env["res.company"].search([])
    companies._inverse_is_l10n_bg_multilanguage()

    _logger.info(
        "l10n_bg_config 19.0.8.3.1 post-migrate: "
        "multilanguage state refreshed for %s company(ies)",
        len(companies),
    )
