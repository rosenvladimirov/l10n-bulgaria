#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_bg_eori = fields.Char(
        string='EORI Number',
        help='Economic Operators Registration and Identification number (EORI) '
             'used for customs operations in the EU',
        tracking=True,
        copy=False,
    )
