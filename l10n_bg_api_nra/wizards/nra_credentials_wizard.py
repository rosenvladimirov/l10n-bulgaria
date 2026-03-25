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
    user_pin = fields.Char(
        string="User PIN (ЕГН/ЛНЧ на подаващия)",
        help="Personal identifier (ЕГН or ЛНЧ) of the person authorized "
             "to submit declarations. Must match the КЕП certificate.",
    )
    user_signature = fields.Text(
        string="User Certificate (КЕП Base64)",
        help="Base64-encoded public certificate from the Qualified Electronic "
             "Signature (КЕП). Remove the BEGIN/END CERTIFICATE lines and "
             "all newlines before pasting.",
    )

    def action_save_credentials(self):
        """Save NRA API credentials to the crypto wallet."""
        self.ensure_one()
        if not self.api_key or not self.api_secret:
            raise UserError(_("Both API Key and API Secret are required."))
        self.company_id._nra_set_credentials(
            self.api_key,
            self.api_secret,
            user_pin=self.user_pin or None,
            user_signature=self.user_signature or None,
        )
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
