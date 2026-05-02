# Copyright 2026 Your Company
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

_logger = logging.getLogger(__name__)


def _post_init_mark_existing_verified(env):
    """Mark every existing portal/internal user as already verified.

    Without this, an upgrade installs `email_verified=False` everywhere and
    locks pre-existing customers out of /shop until an admin flips them by
    hand.
    """
    users = env["res.users"].sudo().search([("email_verified", "=", False)])
    if not users:
        return
    users.write({"email_verified": True})
    _logger.info(
        "website_sale_email_verification: marked %s pre-existing users as "
        "email_verified.",
        len(users),
    )
