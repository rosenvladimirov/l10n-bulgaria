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
