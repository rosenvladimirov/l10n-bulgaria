#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from odoo import fields, models, api, _

_logger = logging.getLogger(__name__)

try:
    import stdnum
    from stdnum.exceptions import InvalidFormat, InvalidChecksum, InvalidLength, InvalidComponent, ValidationError
except ImportError:
    _logger.debug("Cannot `import external dependency python stdnum package`.")


def _l10n_bg_uic_type():
    return [
        ('bg_uic', _('BG Unified identification number (BULSTAT)')),
        ('bg_egn', _('BG Identification number')),
        ('bg_pnf', _('BG Personal number of a foreigner')),
        ('bg_onnra', _('BG Official number from the National Revenue Agency')),
        ('bg_crauid', _('BG Unique identification code under the CRA')),
        ('bg_non_eu', _('BG Non EU Tax administration number')),
        ('eu_vat', _('EU Tax administration number'))
    ]


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # l10n_bg_uic = fields.Char('Unique identification code')
    l10n_bg_uic_type = fields.Selection(selection=_l10n_bg_uic_type(),
                                        string='Type of Bulgaria UID',
                                        help="Choice type of Bulgaria UID.")
    l10n_bg_uic = fields.Char(
        string="Unique identification code",
        help="Unique identification code for the Bulgaria received from trade registry")
