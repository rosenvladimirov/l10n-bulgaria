# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo.api import SUPERUSER_ID, Environment

from odoo.addons.l10n_bg_config.hooks import migrate_account_account_tag

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = Environment(cr, SUPERUSER_ID, {})
    _logger.info(f"Starting migration from {version}")
    if version <= "16.0.1.0.2":
        for partner_id in env["res.partner"].search(
            [("vat", "!=", False), ("l10n_bg_uic", "=", False)]
        ):
            partner_id._validate_l10n_bg_uic()
    if version <= "16.0.1.1.0":
        migrate_account_account_tag(env)
