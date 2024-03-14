# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.api import Environment, SUPERUSER_ID
from odoo.addons.l10n_bg_config.hooks import migrate_account_account_tag

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = Environment(cr, SUPERUSER_ID, {})
    migrate_account_account_tag(env)
