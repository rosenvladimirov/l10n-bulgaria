#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.


def pre_init_hook(cr):
    cr.execute(
        """
        ALTER TABLE res_partner
        ADD COLUMN IF NOT EXISTS display_name_bg character varying;
        """
    )
    cr.execute(
        "UPDATE res_partner SET display_name_bg=display_name_en;"
    )
