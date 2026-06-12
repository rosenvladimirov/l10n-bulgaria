# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Discuss Proxy — listen to internal chat from outside",
    "version": "19.0.1.0.1",
    "summary": "Publish internal Discuss messages of monitored users to the "
               "Centrifugo proxy so an external Claude can listen and reply "
               "(mirror of the Telegram bridge, but for Odoo Discuss).",
    "author": "Rosen Vladimirov",
    "website": "https://github.com/rosenvladimirov",
    "license": "AGPL-3",
    "category": "Discuss",
    "depends": [
        "mail",  # discuss.channel + mail.message
    ],
    "data": [
        "views/res_users_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
}
