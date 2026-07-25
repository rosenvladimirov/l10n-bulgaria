#  Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.api import SUPERUSER_ID, Environment


def pre_init_hook(cr):
    cr.execute(
        """
        ALTER TABLE res_partner
        ADD COLUMN IF NOT EXISTS display_name_bg character varying;
        """
    )
    cr.execute("UPDATE res_partner SET display_name_bg=display_name_en;")


def post_init_hook(cr, registry):
    env = Environment(cr, SUPERUSER_ID, {})
    for partnr_id in env["res.partner"].search([]):
        partnr_id.with_context(lang="bg_BG").write(
            {
                "name": partnr_id.name,
                "city": partnr_id.city,
                "street": partnr_id.street,
            }
        )

    for partnr_id in env["res.partner"].search([]):
        partnr_id.with_context(lang="bg_BG").write(
            {
                "city": partnr_id.city,
                "street": partnr_id.street,
            }
        )
