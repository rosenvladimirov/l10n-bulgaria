"""
Pinpad-aware payment method.

Marks a `pos.payment.method` as pinpad-driven so the POS UI knows to
delegate the charge to the local Python proxy (Odoo.ErpNet.FP) which
talks to a Datecs Pay (or compatible) pinpad through its proprietary
`libdatecs_pinpad.so`.

Strict ADD-only — no existing field, view or method is touched.
"""

from odoo import _, api, fields, models


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    l10n_bg_use_pinpad = fields.Boolean(
        string="Use Pinpad (proxy-driven)",
        default=False,
        help="When enabled, the POS will call the local Python proxy to "
        "perform the card charge on a physical pinpad before allowing the "
        "order to validate. Requires a fiscal device in proxy mode.",
    )
    l10n_bg_pinpad_id = fields.Char(
        string="Pinpad identifier",
        help="Identifier of the pinpad as registered in the Odoo.ErpNet.FP "
        "proxy `config.yaml` (e.g. `datecs_pay_main`). Optional — when "
        "blank the proxy chooses its default pinpad.",
    )

    # ─── External POS mode payment routing ──────────────────────────
    # When the fiscal device is the primary POS (external mode) and
    # the Z-report is imported back into Odoo, each receipt's payment
    # block has a 'kind' (cash / card / voucher / other). To create
    # the matching pos.payment record we need to know which Odoo
    # payment method handles each kind.
    l10n_bg_external_kind = fields.Selection(
        [
            ("cash", "Cash"),
            ("card", "Card"),
            ("voucher", "Voucher / coupon"),
            ("other", "Other"),
        ],
        string="External-mode payment kind",
        help="Maps device payment types onto Odoo payment methods when "
        "importing receipts from a fiscal device acting as primary POS. "
        "Leave blank to exclude this method from external-mode imports.",
    )

    # ─── Fiscal payment type (sent to the device on receipt close) ──
    # Replaces the brittle name-heuristic in erp_net_fp_printer.js (which
    # guessed cash/card/bank from the localized method name and failed for
    # custom names like "DatecsPay"). The 11 values mirror the proxy's
    # accepted enum (point_of_sale/server/routes/printers.py).
    l10n_bg_fiscal_payment_type = fields.Selection(
        selection=[
            ("cash", "Cash"),
            ("card", "Card"),
            ("check", "Check"),
            ("bank", "Bank transfer"),
            ("coupons", "Coupons"),
            ("ext-coupons", "External coupons"),
            ("packaging", "Packaging"),
            ("internal-usage", "Internal usage"),
            ("damage", "Damage"),
            ("reserved1", "Reserved 1"),
            ("reserved2", "Reserved 2"),
        ],
        string="Fiscal payment type",
        compute="_compute_l10n_bg_fiscal_payment_type",
        store=True,
        readonly=False,
        precompute=True,
        help="Payment type sent to the Bulgarian fiscal device when closing "
        "the receipt. Auto-derived from `use_payment_terminal` (card), "
        "`is_cash_count` (cash) and journal `type` (bank) — but freely "
        "editable per method to handle vouchers/coupons/internal use.",
    )

    @api.depends("use_payment_terminal", "is_cash_count", "type")
    def _compute_l10n_bg_fiscal_payment_type(self):
        for rec in self:
            # Запазваме ръчно зададено — НЕ презаписваме
            if rec.l10n_bg_fiscal_payment_type:
                continue
            if rec.use_payment_terminal:
                rec.l10n_bg_fiscal_payment_type = "card"
            elif rec.is_cash_count:
                rec.l10n_bg_fiscal_payment_type = "cash"
            elif rec.type == "bank":
                rec.l10n_bg_fiscal_payment_type = "bank"
            else:
                rec.l10n_bg_fiscal_payment_type = "cash"

    @api.model
    def _get_payment_terminal_selection(self):
        # Register DatecsPay as a native POS payment terminal so it shows
        # in the standard "Integration" section (card + "Integrate with"
        # dropdown), alongside Adyen/Stripe/Ingenico. The actual charge is
        # done by the `datecs_pay` PaymentInterface (payment_datecs_pay.js),
        # which calls the local ErpNet.FP proxy /pinpads/<id>/purchase.
        return super()._get_payment_terminal_selection() + [
            ("datecs_pay", "DatecsPay (ErpNet.FP)"),
        ]

    @api.model
    def _load_pos_data_fields(self, config_id):
        # Add the two new fields to the data the POS browser receives,
        # so PaymentScreen can read them without an extra RPC.
        fields_list = super()._load_pos_data_fields(config_id)
        for f in ("l10n_bg_use_pinpad", "l10n_bg_pinpad_id",
                  "l10n_bg_fiscal_payment_type"):
            if f not in fields_list:
                fields_list.append(f)
        return fields_list

    @api.model
    def l10n_bg_list_pinpads(self):
        """Discover pinpads registered on the ErpNet.FP proxy.

        Used by the `pinpad_id_select` field widget to populate the
        dropdown. The payment-method form has no host of its own, so we
        resolve the proxy host from the configured fiscal.printer.device.
        Returns ``{ok, host, pinpads:[{id,label}], message}``.

        Note: in browser-proxy mode the Odoo server cannot reach the
        local proxy, so the server-side fetch below typically fails — but
        the returned ``host`` lets the widget do a browser-side fetch
        (which CAN reach the local proxy). So the host is the key output.
        """
        dev = self.env["fiscal.printer.device"].sudo().search(
            [("host", "!=", False)], limit=1)
        host = dev.host if dev else ""
        if not host:
            return {"ok": False, "host": "", "pinpads": [],
                    "message": _("No fiscal device / proxy host configured.")}
        try:
            import requests
            r = requests.get(host.rstrip("/") + "/pinpads", timeout=8, verify=False)
            r.raise_for_status()
            data = r.json() or {}
            pinpads = [
                {"id": pid,
                 "label": "%s — %s" % (pid, (info or {}).get("model")
                                       or (info or {}).get("driver") or "?")}
                for pid, info in data.items()
            ]
            return {"ok": True, "host": host, "pinpads": pinpads}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "host": host, "pinpads": [],
                    "message": str(exc)[:160]}
