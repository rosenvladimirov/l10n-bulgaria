# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import fields, models


class PrintSignerMixin(models.AbstractModel):
    """Кой подписва документа при печат (ИЗДАТЕЛ / СЪСТАВИЛ).

    Името е неутрално (без l10n_bg_), защото подписът важи за фирмите от
    всяка държава: config-ите на BG/GR/CY крият полетата по префикс, а това
    поле не бива да се крие. Дали подписът се ВИЖДА решава групата на
    печатащия (в отчетите), не държавата.

    Ред на избор: изрично зададеният на документа → куката
    `_get_print_signer_default` (настройките за печат я разширяват:
    фирма → партньор → вид документ) → този, който печата.
    """

    _name = "print.signer.mixin"
    _description = "Document issuer for printed reports"

    print_signer_id = fields.Many2one(
        comodel_name="res.users",
        string="Issuer",
        copy=False,
        help="Person whose name, signature and company stamp are printed as the issuer "
        "of this document. Leave empty to use the print settings or the person printing.",
    )

    def _get_print_signer(self):
        """Подписващият за един документ; винаги връща потребител."""
        self.ensure_one()
        return self.print_signer_id or self._get_print_signer_default()

    def _get_print_signer_default(self):
        # кука за настройките за печат; без тях подписва този, който печата
        self.ensure_one()
        return self.env.user


class AccountMove(models.Model):
    _inherit = ["account.move", "print.signer.mixin"]
    _name = "account.move"
