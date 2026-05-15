# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    mypos_flow = fields.Selection(
        [
            ("redirect", "Hosted Redirect (default)"),
            ("embedded", "Embedded iFrame (on-site)"),
        ],
        string="myPOS Checkout Flow",
        default="redirect",
        help=(
            "Redirect: shopper goes to the myPOS hosted page (RSA-signed "
            "IPCPurchase).\n"
            "Embedded: the myPOS SDK mounts a branded iFrame in the Odoo "
            "checkout — no client-side signature; security is the signed "
            "server-to-server urlNotify callback. Visa/Mastercard/Maestro "
            "only (no Apple/Google Pay)."
        ),
    )

    def _get_redirect_form_view(self, is_validation=False):
        """Swap the rendered template when the provider is in embedded mode.

        Odoo renders whatever this returns into the payment page; for
        embedded we return a template that mounts the myPOS iFrame and
        calls MyPOSEmbedded.createPayment instead of auto-submitting a
        signed redirect form.
        """
        self.ensure_one()
        if self.code == "mypos" and self.mypos_flow == "embedded":
            return self.env.ref("payment_mypos_embedded.embedded_form")
        return super()._get_redirect_form_view(is_validation=is_validation)
