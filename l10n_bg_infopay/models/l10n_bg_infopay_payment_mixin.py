# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

"""Mixin for InfoPay payment-order bridges.

Bridges (OCA `account_payment_order`, EE `account_batch_payment`, or
any other host) inherit this mixin alongside their host model and
override the small set of placeholders below to supply the host-
specific data (debtor IBAN, payment lines, etc.).  All API calls,
session lifecycle and admin/user-token routing live here — bridge
modules MUST NOT reach for ``infopay.provider`` directly.

Payment paths:

* Single — domestic BGN, SEPA EUR, domestic budget (tax/НАП).
* Bulk — domestic BGN bulk, SEPA EUR bulk (each min 2 / max 250).
* Status polling — single or bulk; poll until ``IsFinal=true``.
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

    def _l10n_bg_infopay_create_domestic(
        self, debtor_iban, creditor_name, creditor_iban,
        amount, description,
        service_level=None, end_to_end_id=None,
    ):
        """Create a single BGN domestic credit transfer.

        Returns the raw provider response — caller stores
        ``paymentId`` + ``scaRedirect`` URL for the human SCA step.
        """
        return self._l10n_bg_infopay_with_session(
            "_create_domestic_payment",
            debtor_iban=debtor_iban,
            creditor_name=creditor_name,
            creditor_iban=creditor_iban,
            amount=amount,
            description=description,
            service_level=service_level,
            end_to_end_id=end_to_end_id,
        )

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

    def _l10n_bg_infopay_create_budget(
        self, debtor_iban, creditor_name, creditor_iban,
        amount, description, ultimate_debtor,
        tax_payer_id, tax_payer_type,
        service_level=None, end_to_end_id=None,
    ):
        """Create a single domestic-budget (tax / НАП) BGN transfer.

        ``tax_payer_type`` ∈ ``EGN | EIK | PNF``.
        """
        if tax_payer_type not in ("EGN", "EIK", "PNF"):
            raise UserError(self.env._(
                "tax_payer_type must be one of EGN, EIK, PNF; got %s.",
                tax_payer_type,
            ))
        return self._l10n_bg_infopay_with_session(
            "_create_budget_payment",
            debtor_iban=debtor_iban,
            creditor_name=creditor_name,
            creditor_iban=creditor_iban,
            amount=amount,
            description=description,
            ultimate_debtor=ultimate_debtor,
            tax_payer_id=tax_payer_id,
            tax_payer_type=tax_payer_type,
            service_level=service_level,
            end_to_end_id=end_to_end_id,
        )

    # ── bulk payments ─────────────────────────────────────────────────

    def _l10n_bg_infopay_create_bulk_domestic(self, debtor_iban, payments):
        """Bulk BGN domestic — *payments*: list of dicts with keys
        ``creditor_name, creditor_iban, amount, description``.
        Min 2 / max 250.
        """
        if not 2 <= len(payments) <= 250:
            raise UserError(self.env._(
                "Bulk domestic payments require 2-250 items; got %d.",
                len(payments),
            ))
        return self._l10n_bg_infopay_with_session(
            "_create_bulk_domestic_payments",
            debtor_iban=debtor_iban,
            payments=payments,
        )

    def _l10n_bg_infopay_create_bulk_sepa(self, debtor_iban, payments):
        """Bulk SEPA EUR — *payments*: dicts with ``creditor_name,
        creditor_iban, amount, description, country``.  Min 2 / max 250.
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
