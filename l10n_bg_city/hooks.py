# Part of Odoo. See LICENSE file for full copyright and licensing details.
import csv
import os

import odoo
from odoo.api import SUPERUSER_ID, Environment


def post_init_hook(cr, registry):
    env = Environment(cr, SUPERUSER_ID, {})
    country_id = env.ref("base.bg")
    module = __name__.split("addons.")[1].split(".")[0]
    module_path = ""
    for adp in odoo.addons.__path__:
        module_path = adp + os.sep + module
        if os.path.isdir(module_path):
            break
    module_path += os.sep + "data"
    files = [
        os.path.join(module_path, "res.city.bg.csv"),
        os.path.join(module_path, "city_hall", "res.city.bg.csv"),
        os.path.join(module_path, "municipality", "res.city.bg.csv"),
        os.path.join(module_path, "settlement", "res.city.bg.csv"),
    ]
    res_city_model = env["res.city"]
    res_country_state = env["res.country.state"]
    for file_name in files:
        with open(file=file_name) as csv_file:
            cn_codes = csv.DictReader(csv_file, delimiter=",")
            for row in cn_codes:
                res_id = env.ref(row["id"])
                if res_id:
                    res_city_id = res_city_model.search([("id", "=", res_id.id)])
                    if res_city_id:
                        res_city_id.with_context(lang="bg_BG").write(
                            {
                                "name": row["name"],
                                "country_id": country_id.id,
                            }
                        )

    with open(file=os.path.join(module_path, "res.country.state.bg.csv")) as csv_file:
        cn_codes = csv.DictReader(csv_file, delimiter=",")
        for row in cn_codes:
            res_id = env.ref(row["id"])
            if res_id:
                res_city_id = res_country_state.search([("id", "=", res_id.id)])
                if res_city_id:
                    res_city_id.with_context(lang="bg_BG").write(
                        {
                            "name": row["name"],
                            "country_id": country_id.id,
                        }
                    )
