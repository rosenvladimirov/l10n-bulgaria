# Copyright 2026 Your Company
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Website Sale Email Verification",
    "summary": "Mandatory email verification (link/OTP) for shop registration "
               "with disposable email blocklist.",
    "version": "18.0.1.0.0",
    "category": "Website/Website",
    "license": "AGPL-3",
    "author": "Rosen Vladimirov",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "depends": [
        "website_sale_no_public_order",
        "mail",
    ],
    "external_dependencies": {
        "python": ["disposable_email_domains"],
    },
    "data": [
        "security/ir.model.access.csv",
        "data/res_company_data.xml",
        "data/disposable_email_seed.xml",
        "data/mail_template_data.xml",
        "data/ir_cron_data.xml",
        "views/disposable_email_domain_views.xml",
        "views/res_config_settings_views.xml",
        "views/res_users_views.xml",
        "views/templates.xml",
    ],
    "post_init_hook": "_post_init_mark_existing_verified",
    "installable": True,
    "application": False,
}
