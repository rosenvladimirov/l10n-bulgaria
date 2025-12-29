#  Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class Company(models.Model):
    _inherit = "res.company"

    layout_background = fields.Selection(
        selection_add=[("Section", "Included in layout")],
        ondelete={"Section": "set default"},
    )
    layout_background_header_image = fields.Binary("Background Header Image")
    layout_background_footer_image = fields.Binary("Background Footer Image")

    layout_background_l_image = fields.Binary("Background Article Image-landscape")
    layout_background_l_header_image = fields.Binary("Background Header Image-landscape")
    layout_background_l_footer_image = fields.Binary("Background Footer Image-landscape")

    logo_print = fields.Binary("Logo print")
    font = fields.Selection(
        selection_add=[
            ("SF_Text", "SF Text"),
            ("SF_Pro_Text", "SF Text Pro"),
        ],
        ondelete={"SF_Text": "set default", "SF_Pro_Text": "set default"},
    )
