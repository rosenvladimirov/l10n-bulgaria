#  Part of Odoo. See LICENSE file for full copyright and licensing details.
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging
import sys

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def install(package):
    try:
        __import__(package)
    except Exception:
        import subprocess

        subprocess.call([sys.executable, "-m", "pip", "install", package])


install("openupgradelib")

try:
    from openupgradelib import openupgrade
except ImportError:
    openupgrade = None


@openupgrade.migrate(use_env=True)
def migrate(env, version):
    fields_to_rename = [
        ("res.city", "res_city", "type_village_city_id", "l10n_bg_type_settlement_id"),
        ("res.city", "res_city", "ekatte", "l10n_bg_ecattu"),
        ("res.city", "res_city", "bg_code", "l10n_bg_code"),
        ("res.city", "res_city", "city_hall_id", "l10n_bg_city_hall_id"),
        ("res.city", "res_city", "municipality_id", "l10n_bg_municipality_id"),
        ("res.city", "res_city", "has_taxoffice", "l10n_bg_has_tax_office"),
        ("res.city", "res_city", "structure_type", "l10n_bg_structure_type"),
    ]

    for field_to_rename in fields_to_rename:
        try:
            openupgrade.rename_fields(env, [field_to_rename])
        except Exception as e:
            _logger.error(str(e))
    # Install l10n_bg_config if needed
    env = api.Environment(env.cr, SUPERUSER_ID, {})
    IrModule = env["ir.module.module"]
    IrModule.update_list()

    l10n_bg_config_module = IrModule.search([("name", "=", "l10n_bg_config")])
    if l10n_bg_config_module.state != "installed":
        l10n_bg_config_module.button_immediate_install()
