# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, fields, models


def l10n_bg_member_163a(record):
    return [
        ("01", _("Delivery under Part I of Annex 2 of VAT")),
        ("02", _("Delivery under Part II of Annex 2 of VAT")),
        ("03", _("Import under Annex 3 of VAT")),
        ("07", _("Supply, import or IC acquisition of bread")),
        ("08", _("Supply, import or IC acquisition of flour")),
        ("41", _("Sending or transporting goods")),
        ("43", _("Under Art. 15a, para. 4 of VAT")),
        ("46", _("Correction of an error made when specifying the VAT.")),
        ("48", _("Return under Art. 15a, para. 5 of VAT")),
    ]


class ProductCategory(models.Model):
    _inherit = "product.category"

    l10n_bg_art_163a = fields.Selection(
        selection=l10n_bg_member_163a,
        string="Art. 163a from VAT",
        help="01. - Delivery under Part I of Annex 2 of VAT.\n"
        "02. - Delivery under Part II of Annex 2 of VAT.\n"
        "03. - Import under Annex 3 of VAT.\n"
        "07. - Supply, import or intra-Community acquisition of bread.\n"
        "08. - Supply, import or intra-Community acquisition of flour.\n"
        "41. - Sending or transporting goods from the territory of the "
        "country to the territory of another member state under the regime "
        "of storage of goods on demand under Art. 15a of VAT.\n"
        "Replacement of the person for whom the goods "
        "were intended under Art. 15a, para. 4 of VAT.\n"
        "Correction of an error made when specifying the VAT identification number "
        "of the person for whom the goods are intended in operations reflected with code 41.\n"
        "Return of goods to the territory of the country under Art. 15a, para. 5 of VAT.",
    )
