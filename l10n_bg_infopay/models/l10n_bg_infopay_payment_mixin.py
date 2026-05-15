# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

"""Mixin for InfoPay payment-order bridges.

Bridges (OCA `account_payment_order`, EE `account_batch_payment`, or
any other host) inherit this mixin alongside their host model and
override the small set of placeholders below to supply the host-
specific data (debtor IBAN, payment lines, etc.).  All API calls,
session lifecycle and admin/user-token routing live here — bridge
modules MUST NOT reach for ``infopay.provider`` directly.

Payment paths (след 01.01.2026, BG в еврозоната):

* Single — SEPA EUR `/api/payments/sepa-credit-transfers`.
* Bulk — SEPA EUR `/api/bulk-payments/sepa-credit-transfers` (2..250).
* Status polling — single or bulk; poll until ``IsFinal=true``.

Borica е маркирала трите `-bgn` endpoint-а като ``deprecated: true``;
domestic credit + budget + bulk-domestic вече не се ползват от bridge.
За НАП/мита/община операторът ползва банковия портал ръчно докато
Borica добави `/domestic-budget-transfers-eur`.
"""

import logging

from odoo import models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class InfopayPaymentMixin(models.AbstractModel):
    _name = "l10n.bg.infopay.payment.mixin"
    _description = "InfoPay payment-order mixin (host-agnostic)"

    # ── overrides ─────────────────────────────────────────────────────

    def _l10n_bg_infopay_get_company(self):
        """Return ``res.company`` for the host."""
        self.ensure_one()
        raise NotImplementedError(
            "%s must implement _l10n_bg_infopay_get_company" % self._name
        )

    def _l10n_bg_infopay_use_admin_token(self):
        """Payment paths default to user token (admin=False) — payments
        require write access and a user-supplied wallet password by
        contract.  Cron-driven payment orchestrators that need to
        run unattended should override to True AND ensure the admin
        ERP registration in the InfoPay portal carries write scope
        (rare; usually scope is read-only).
        """
        return False

    # ── single payments ───────────────────────────────────────────────

    def _l10n_bg_infopay_create_sepa(
        self, debtor_iban, creditor_name, creditor_iban,
        amount, description, creditor_country,
        creditor_city=None, service_level=None, end_to_end_id=None,
    ):
        """Create a single SEPA EUR credit transfer."""
        return self._l10n_bg_infopay_with_session(
            "_create_sepa_payment",
            debtor_iban=debtor_iban,
            creditor_name=creditor_name,
            creditor_iban=creditor_iban,
            amount=amount,
            description=description,
            creditor_country=creditor_country,
            creditor_city=creditor_city,
            service_level=service_level,
            end_to_end_id=end_to_end_id,
        )

    # ── bulk payments ─────────────────────────────────────────────────

    def _l10n_bg_infopay_create_bulk_sepa(
        self, debtor_iban, payments, service_level=None,
    ):
        """Bulk SEPA EUR — *payments*: dicts with ``creditor_name,
        creditor_iban, amount, description, country``.  Min 2 / max 250.

        ``service_level`` ∈ ``SEPA`` (standard) | ``INST`` (instant);
        прилага се за всеки payment в bulk-а.
        """
        if not 2 <= len(payments) <= 250:
            raise UserError(self.env._(
                "Bulk SEPA payments require 2-250 items; got %d.",
                len(payments),
            ))
        return self._l10n_bg_infopay_with_session(
            "_create_bulk_sepa_payments",
            debtor_iban=debtor_iban,
            payments=payments,
            service_level=service_level,
        )

    # ── status polling ────────────────────────────────────────────────

    def _l10n_bg_infopay_get_payment_status(self, payment_id, bulk=False):
        """Return raw payment-status dict; caller checks
        ``IsFinal`` and acts on terminal states.
        """
        return self._l10n_bg_infopay_with_session(
            "_get_payment_status",
            payment_id=payment_id,
            bulk=bulk,
        )

    # ── private session orchestration ─────────────────────────────────

    def _l10n_bg_infopay_with_session(self, provider_method, **kwargs):
        """Wrap a single provider call with session create/close.

        ``provider_method`` is the public method name on
        ``infopay.provider`` (must be one of those that accept
        ``session`` as first arg + ``**kwargs``).  Bridges should not
        bypass this — keeps session lifecycle consistent across the
        codebase.
        """
        self.ensure_one()
        company = self._l10n_bg_infopay_get_company()
        admin = self._l10n_bg_infopay_use_admin_token()
        provider = self.env["infopay.provider"]
        method = getattr(provider, provider_method, None)
        if not callable(method):
            raise UserError(self.env._(
                "Unknown InfoPay provider method '%s'.", provider_method,
            ))
        session = provider._create_session(company, admin=admin)
        try:
            return method(session, **kwargs)
        finally:
            provider._close_session(session)
