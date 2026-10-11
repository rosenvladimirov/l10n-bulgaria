"""19.0.8.18.0 — етикетите на ядрото с подвеждащ превод („Account Payable“,
„Affect Base of Subsequent Taxes“); при инсталация го прави post_init_hook."""
from odoo import SUPERUSER_ID, api

from odoo.addons.l10n_bg_config.hooks import _l10n_bg_fix_core_labels


def migrate(cr, version):
    _l10n_bg_fix_core_labels(api.Environment(cr, SUPERUSER_ID, {}))
