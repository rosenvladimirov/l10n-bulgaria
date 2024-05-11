#  Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import SUPERUSER_ID, api


def pre_init_hook(cr):
    cr.execute(
        """ALTER TABLE IF EXISTS res_partner
    ADD COLUMN IF NOT EXISTS l10n_bg_uic_backup character varying(64) COLLATE pg_catalog."default" NOT NULL;"""
    )
    env = api.Environment(cr, SUPERUSER_ID, {})
    partners = env["res.partner"].search([("l10n_bg_uic", "!=", False)])
    for partner_id in partners:
        cr.execute(
            f"""UPDATE res_partner
    SET l10n_bg_uic_backup = {partner_id.l10n_bg_uic}
    WHERE id = {partner_id.id};"""
        )
    env["ir.model.fields"].search(
        [
            ("model", "=", "res.partner"),
        ]
    )


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    l10n_bg_uic_backup = {}
    cr.execute("""SELECT l10n_bg_uic_backup FROM res_partner;""")
    for partner_id in cr.dictfetchall():
        l10n_bg_uic_backup.update(
            {
                partner_id["id"]: partner_id["l10n_bg_uic_backup"],
            }
        )
    for partner_id in env["res.partner"].search(
        [("id", "in", l10n_bg_uic_backup.keys())]
    ):
        partner_id.l10n_bg_uic = l10n_bg_uic_backup[partner_id.id]
    cr.execute("""ALTER TABLE res_partner DROP COLUMN IF EXISTS l10n_bg_uic_backup;""")
