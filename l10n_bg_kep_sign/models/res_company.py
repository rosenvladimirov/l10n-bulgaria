# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    # Selection-ът се разширява от glue модулите (proxy/stampit).
    l10n_bg_kep_sign_provider = fields.Selection(
        selection=[("none", "None")],
        string="КЕП Signing Provider", default="none",
        help="Which backend signs documents with the qualified e-signature: "
             "StampIT (browser) or the local Odoo.ErpNet.FP proxy (server).")
