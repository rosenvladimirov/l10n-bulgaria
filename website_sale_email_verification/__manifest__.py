# Copyright 2026 Your Company
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Website Sale Email Verification",
    "summary": "Mandatory email verification (link/OTP) for shop registration "
               "with disposable email blocklist.",
    "version": "18.0.1.0.1",
    "category": "Website/Website",
    "license": "AGPL-3",
    "author": "Rosen Vladimirov",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "depends": [
        "website_sale_no_public_order",
        "mail",
    ],
    # disposable_email_domains is a soft dependency used only by the
    # _refresh_from_package fallback when the Kickbox HTTP endpoint is
    # unreachable. Importing it is wrapped in try/except inside the model,
    # so the module installs and runs without it. Install it manually
    # (`pip install disposable_email_domains`) on the server if you want
    # the offline fallback to work.
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
