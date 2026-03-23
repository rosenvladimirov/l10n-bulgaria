import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class NraCredentialsWizard(models.TransientModel):
    _name = "nra.credentials.wizard"
    _description = "NRA API Credentials Setup"

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    api_key = fields.Char(
        string="API Key (Client ID)",
        required=True,
    )
    api_secret = fields.Char(
        string="API Secret (Client Secret)",
        required=True,
    )

    def action_save_credentials(self):
        """Save NRA API credentials to the crypto wallet."""
        self.ensure_one()
        if not self.api_key or not self.api_secret:
            raise UserError(_("Both API Key and API Secret are required."))
        self.company_id._nra_set_credentials(self.api_key, self.api_secret)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("NRA API Credentials"),
                "message": _(
                    "Credentials saved securely in your crypto wallet."
                ),
                "type": "success",
                "sticky": False,
            },
        }
