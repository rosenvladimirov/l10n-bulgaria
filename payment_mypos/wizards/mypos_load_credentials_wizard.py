# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

"""One-shot wizard for stashing freshly-generated myPOS partner credentials
into the company-owner's crypto.wallet.

Two input modes:

  • paste JSON — the exact shape `tools/mypos_browser credentials` writes
    (``{"clientId": "...", "clientSecret": "...", ...}``); we pluck the
    two keys, ignore the rest.
  • manual fields — for operators who'd rather type the values straight
    into Odoo than handle a file.

The wizard never persists the secret in a transient field for longer
than the request — the wallet write happens inline and we clear the
field before returning.
"""

import json
import logging

from odoo import _, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class MyPosLoadCredentialsWizard(models.TransientModel):
    _name = "mypos.load.credentials.wizard"
    _description = "myPOS: Load Partner API Credentials into Wallet"

    provider_id = fields.Many2one(
        "payment.provider",
        string="myPOS Provider",
        required=True,
        domain="[('code', '=', 'mypos')]",
    )

    input_mode = fields.Selection(
        [("json", "Paste JSON (from mypos_browser credentials)"),
         ("manual", "Enter clientId / clientSecret manually")],
        default="json",
        required=True,
        help=(
            "JSON mode accepts the file produced by `mypos credentials "
            "--integration-id N` — paste its contents into the field below."
        ),
    )

    raw_json = fields.Text(
        string="JSON payload",
        help="Paste the entire JSON file (clientId, clientSecret, etc.)",
    )

    client_id = fields.Char(
        string="clientId",
        help="Partner-API client identifier (visible, not a secret on its own)",
    )

    client_secret = fields.Char(
        string="clientSecret",
        help="Partner-API secret. Goes straight to the wallet; never stored on this wizard.",
    )

    def _extract_pair(self):
        """Return (client_id, client_secret) from whichever input mode is set."""
        self.ensure_one()
        if self.input_mode == "json":
            if not (self.raw_json or "").strip():
                raise ValidationError(_("Paste the JSON payload first."))
            try:
                doc = json.loads(self.raw_json)
            except json.JSONDecodeError as e:
                raise ValidationError(_("Invalid JSON: %s") % e) from e
            cid = doc.get("clientId") or (doc.get("raw_credentials") or {}).get(
                "integrationCredentials", {}
            ).get("clientId") or (doc.get("integrationCredentials") or {}).get("clientId")
            sec = doc.get("clientSecret") or (doc.get("raw_credentials") or {}).get(
                "integrationCredentials", {}
            ).get("clientSecret") or (doc.get("integrationCredentials") or {}).get("clientSecret")
            if not (cid and sec):
                raise ValidationError(_(
                    "JSON does not contain clientId/clientSecret. Expected the file "
                    "produced by `mypos credentials --integration-id N`."
                ))
            return cid, sec
        if not (self.client_id and self.client_secret):
            raise ValidationError(_("Both clientId and clientSecret are required."))
        return self.client_id, self.client_secret

    def action_store(self):
        """Persist the credentials into the company-owner's wallet, then
        wipe the wizard's transient secret fields and dismiss."""
        self.ensure_one()
        cid, sec = self._extract_pair()
        self.provider_id._mypos_set_client_credentials(cid, sec)
        # Wipe transient state so re-opening the wizard shows a blank form.
        self.write({
            "raw_json": False,
            "client_id": False,
            "client_secret": False,
        })
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "title": _("myPOS"),
                "message": _("Credentials stored in the company-owner's wallet."),
                "sticky": False,
            },
        }
