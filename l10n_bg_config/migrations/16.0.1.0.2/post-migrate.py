# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.api import Environment, SUPERUSER_ID

import logging
_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = Environment(cr, SUPERUSER_ID, {})
    for partner_id in env['res.partner'].search([('vat', '!=', False), ('l10n_bg_uic', '=', False)]):
        partner_id._validate_l10n_bg_uic()
