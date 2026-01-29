#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
# from lxml import etree

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class Company(models.Model):
    _inherit = ['res.company', 'res.transliterate.mixin']
    _name = "res.company"

    name = fields.Char(translate=True)
    lang = fields.Selection(
        related="partner_id.lang",
        string="Language",
        help="If the selected language is loaded in the system, "
        "all documents related to this contact will "
        "be printed in this language. If not, it will be English.",
    )
    street = fields.Char(translate=True)
    street2 = fields.Char(translate=True)
    city = fields.Char(translate=True)
    transliterate_names = fields.Boolean(
        string="Transliterate names",
        default=False,
        help="Enable automatic transliteration of partner and company names."
    )

    def init(self):
        _logger.info("Data res.transliterate.mixin: %s", self._table)
        # Run for each concrete model that inherits this mixin.
        self.env.cr.execute(
            f'ALTER TABLE "{self._table}" '
            "ADD COLUMN IF NOT EXISTS transliterate_tracking jsonb"
        )
        super().init()
