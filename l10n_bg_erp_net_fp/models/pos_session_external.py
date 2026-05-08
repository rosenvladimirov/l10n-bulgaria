"""
pos.session — external POS mode hook (Phase 2).

When `pos.config.l10n_bg_external_pos_mode` is enabled, opening a POS
session triggers a push of the configuration (PLU table, VAT groups,
operators, logo, header/footer) to the assigned fiscal device. The
device is then "ready to sell" — operator hits PLU numbers / scans
barcodes directly on the apparat, not in the Odoo POS UI.

Push happens in `_l10n_bg_external_open_push()` which is called from
`action_pos_session_open()` after the standard session-open logic
runs (so the session is actually open before we push). Push errors
are aggregated and surfaced on the session form (push_status field)
but do NOT block the session from opening — the cashier can still
operate, with a manual retry button as fallback.
"""

import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


PUSH_STATUS = [
    ("none", "Not pushed"),
    ("partial", "Partial (some items failed)"),
    ("ok", "Pushed"),
    ("error", "Push failed"),
]


class PosSession(models.Model):
    _inherit = "pos.session"

    # Shadow of config_id.l10n_bg_external_pos_mode — exposed to the
    # POS frontend via _load_pos_data_fields (we cannot expose fields
    # directly on pos.config; see feedback_pos_config_load_pos_data_fields.md)
    l10n_bg_external_pos_mode = fields.Boolean(
        related="config_id.l10n_bg_external_pos_mode",
        readonly=True,
        store=True,
    )

    l10n_bg_external_push_status = fields.Selection(
        PUSH_STATUS,
        default="none",
        readonly=True,
        copy=False,
        string="External-mode push status",
    )
    l10n_bg_external_push_summary = fields.Text(
        readonly=True,
        copy=False,
        string="Push summary",
        help="Human-readable summary of the last PLU/config push to the "
        "fiscal device when external POS mode is active.",
    )
    l10n_bg_external_push_at = fields.Datetime(
        readonly=True,
        copy=False,
        string="Last push",
    )
    # All fiscal.session records opened for this pos.session — one
    # per fiscal device (multi-device shops have many).
    l10n_bg_fiscal_session_ids = fields.One2many(
        "fiscal.session",
        "pos_session_id",
        string="Fiscal sessions (Z-cycles)",
        readonly=True,
    )
    l10n_bg_fiscal_session_id = fields.Many2one(
        "fiscal.session",
        compute="_compute_l10n_bg_primary_fiscal_session",
        string="Primary fiscal session",
        readonly=True,
        store=False,
        help="First-opened fiscal.session for this pos.session "
        "(backward-compat alias). Use l10n_bg_fiscal_session_ids for "
        "the full set in multi-device shops.",
    )

    @api.depends("l10n_bg_fiscal_session_ids")
    def _compute_l10n_bg_primary_fiscal_session(self):
        for sess in self:
            sess.l10n_bg_fiscal_session_id = (
                sess.l10n_bg_fiscal_session_ids[:1]
            )

    # ------------------------------------------------------------------
    # Open hook — orchestrate push when external mode is on
    # ------------------------------------------------------------------

    def action_pos_session_open(self):
        res = super().action_pos_session_open()
        for sess in self:
            cfg = sess.config_id
            if not cfg.l10n_bg_external_pos_mode:
                continue
            if not cfg.l10n_bg_all_fiscal_devices:
                # Constraint on pos.config blocks toggle-without-device
                # already; this is a defensive double-check.
                _logger.warning(
                    "External POS mode on '%s' but no fiscal devices assigned.",
                    cfg.name,
                )
                continue
            sess._l10n_bg_external_open_push()
        return res

    def _l10n_bg_external_open_push(self):
        """Orchestrate the open-time push for all configured fiscal
        devices on this POS configuration. Each device gets its own
        fiscal.session (Z-cycle) and the same PLU/VAT/operator config.

        Sequence per device:
          1. Open `fiscal.session`
          2. Push VAT groups
          3. Push operators
          4. Push PLU table from registry
          5. Push logo
          6. Push header/footer
          7. X-report sanity
        """
        self.ensure_one()
        all_steps = []  # [(device.name, step, ok, message), ...]
        for device in self.config_id.l10n_bg_all_fiscal_devices:
            for step in self._l10n_bg_push_to_device(device):
                all_steps.append((device.name, *step))

        ok_count = sum(1 for _d, _n, ok, _m in all_steps if ok)
        total = len(all_steps)
        if total and ok_count == total:
            status = "ok"
        elif ok_count == 0:
            status = "error"
        else:
            status = "partial"

        summary = "\n".join(
            f"[{dev}] {'✓' if ok else '✗'} {name}: {msg}"
            for dev, name, ok, msg in all_steps
        )
        self.write({
            "l10n_bg_external_push_status": status,
            "l10n_bg_external_push_summary": summary,
            "l10n_bg_external_push_at": fields.Datetime.now(),
        })
        if hasattr(self, "message_post"):
            self.message_post(
                body=_("External-mode push: %s\n%s") % (status, summary),
                message_type="notification",
            )
        return status

    def _l10n_bg_push_to_device(self, device):
        """Run the 7-step push sequence on ONE device. Returns a list
        of (step_name, ok: bool, message: str) tuples.
        """
        self.ensure_one()
        Plu = self.env["l10n.bg.fiscal.plu"]
        FiscalSess = self.env["fiscal.session"]
        steps = []

        # 1. Open fiscal.session for this device (skip if one already
        # exists for this pos.session+device pair — re-runs of the
        # orchestrator should not multiply sessions)
        existing = FiscalSess.search([
            ("pos_session_id", "=", self.id),
            ("device_id", "=", device.id),
            ("state", "=", "open"),
        ], limit=1)
        try:
            if existing:
                steps.append(("fiscal_session", True,
                             f"Already open {existing.name}"))
            else:
                fsess = FiscalSess.create({
                    "device_id": device.id,
                    "company_id": self.company_id.id,
                    "source": "pos_external",
                    "pos_session_id": self.id,
                })
                steps.append(("fiscal_session", True,
                             f"Opened {fsess.name}"))
        except Exception as exc:  # noqa: BLE001
            steps.append(("fiscal_session", False, str(exc)[:200]))

        # 2. VAT groups
        try:
            vat_result = device._l10n_bg_push_vat_groups()
            steps.append(("vat_groups", bool(vat_result is not False),
                         "Pushed" if vat_result else "Skipped/failed"))
        except Exception as exc:  # noqa: BLE001
            steps.append(("vat_groups", False, str(exc)[:200]))

        # 3. Operators
        try:
            ops_result = device._l10n_bg_push_operators(self.config_id)
            steps.append(("operators", bool(ops_result is not False),
                         "Pushed" if ops_result else "Skipped/failed"))
        except Exception as exc:  # noqa: BLE001
            steps.append(("operators", False, str(exc)[:200]))

        # 4. PLU table
        try:
            active_plus = Plu.search([
                ("active", "=", True),
                ("company_id", "=", self.company_id.id),
            ])
            for p in active_plus:
                p._check_consistency()
            pushable = active_plus.filtered(
                lambda r: r.push_state in ("pending", "stale", "name_drift")
            )
            blocked = active_plus.filtered(
                lambda r: r.push_state in ("conflict", "error")
            )
            push_result = device._l10n_bg_push_plu_registry(pushable)
            msg = f"{len(pushable)} pushed"
            if blocked:
                msg += f", {len(blocked)} blocked (conflict/error)"
            steps.append(("plu_table", bool(push_result is not False), msg))
        except Exception as exc:  # noqa: BLE001
            steps.append(("plu_table", False, str(exc)[:200]))

        # 5. Logo
        try:
            if device.logo_image:
                device.action_upload_logo()
                steps.append(("logo", True, "Uploaded"))
            else:
                steps.append(("logo", True, "No logo configured — skipped"))
        except Exception as exc:  # noqa: BLE001
            steps.append(("logo", False, str(exc)[:200]))

        # 6. Header/footer
        try:
            device.action_sync_header_footer()
            steps.append(("header_footer", True, "Synced"))
        except Exception as exc:  # noqa: BLE001
            steps.append(("header_footer", False, str(exc)[:200]))

        # 7. X-report sanity
        try:
            device.print_x_report()
            steps.append(("x_report", True, "Printed"))
        except Exception as exc:  # noqa: BLE001
            steps.append(("x_report", False, str(exc)[:200]))

        return steps

    # ------------------------------------------------------------------
    # Manual retry — button on session form
    # ------------------------------------------------------------------

    def action_l10n_bg_external_push_retry(self):
        """Re-run the open-time push manually. Useful when the device
        was offline at session open and is now reachable.
        """
        self.ensure_one()
        if not self.config_id.l10n_bg_external_pos_mode:
            from odoo.exceptions import UserError
            raise UserError(_(
                "External POS mode is not enabled on this configuration."
            ))
        if self.state != "opened":
            from odoo.exceptions import UserError
            raise UserError(_(
                "Session must be opened before pushing to the fiscal device."
            ))
        status = self._l10n_bg_external_open_push()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("External-mode push"),
                "message": _("Status: %s") % status,
                "type": "success" if status == "ok" else "warning",
                "sticky": status != "ok",
            },
        }

    # ==================================================================
    # Phase 3 — close hook (pull sales → import → Z → close fiscal sess)
    # ==================================================================

    def action_pos_session_closing_control(
        self, balancing_account=False, amount_to_balance=0,
        bank_payment_method_diffs=None,
    ):
        """Override of close-control entry point.

        For external-POS-mode sessions: BEFORE the standard control
        wizard runs, pull the day's receipts from the device, import
        them as pos.order records, run Z-report (if auto_z_on_close),
        and close the fiscal.session. Then proceed with the standard
        flow so the cashier can confirm cash counts.

        Failures are non-fatal — the close-control wizard still opens
        with a warning message so the cashier can decide to retry or
        force-close (the fiscal.session stays `open` until resolved).
        """
        for sess in self:
            if sess.config_id.l10n_bg_external_pos_mode:
                sess._l10n_bg_external_close_orchestrate()
        return super().action_pos_session_closing_control(
            balancing_account=balancing_account,
            amount_to_balance=amount_to_balance,
            bank_payment_method_diffs=bank_payment_method_diffs,
        )

    def _l10n_bg_external_close_orchestrate(self):
        """Run the close sequence per device: pull sales → import →
        Z → close fiscal.session. Aggregates per-device results.
        """
        self.ensure_one()
        all_steps = []  # [(device.name, step, ok, msg), ...]

        # 0. Stale PLU warning — global, not per-device (the registry
        # is per-company)
        Plu = self.env["l10n.bg.fiscal.plu"]
        stale_count = Plu.search_count([
            ("active", "=", True),
            ("company_id", "=", self.company_id.id),
            ("push_state", "in", ("stale", "name_drift")),
        ])
        if stale_count:
            all_steps.append((
                "ALL", "stale_warning", True,
                "%d PLU(s) changed mid-shift; will re-push at next open"
                % stale_count,
            ))

        for device in self.config_id.l10n_bg_all_fiscal_devices:
            for step in self._l10n_bg_close_for_device(device):
                all_steps.append((device.name, *step))

        ok_count = sum(1 for _d, _n, ok, _m in all_steps if ok)
        total = len(all_steps)
        if total and ok_count == total:
            status = "ok"
        elif ok_count == 0:
            status = "error"
        else:
            status = "partial"

        summary = "\n".join(
            f"[{dev}] {'✓' if ok else '✗'} {name}: {msg}"
            for dev, name, ok, msg in all_steps
        )
        existing = self.l10n_bg_external_push_summary or ""
        sep = "\n--- close ---\n" if existing else ""
        self.write({
            "l10n_bg_external_push_status": status,
            "l10n_bg_external_push_summary": existing + sep + summary,
            "l10n_bg_external_push_at": fields.Datetime.now(),
        })
        if hasattr(self, "message_post"):
            self.message_post(
                body=_("External-mode close: %s\n%s") % (status, summary),
                message_type="notification",
            )
        return status

    def _l10n_bg_close_for_device(self, device):
        """Per-device close: pull → import → Z → close fiscal.session.
        Returns a list of (step_name, ok, message) tuples.
        """
        self.ensure_one()
        steps = []

        # Locate this device's fiscal.session
        fsess = self.env["fiscal.session"].search([
            ("pos_session_id", "=", self.id),
            ("device_id", "=", device.id),
            ("state", "=", "open"),
        ], limit=1)

        # 1. Pull sales from device journal
        receipts = []
        try:
            from_dt = (
                fsess.opened_at if fsess
                else (self.start_at or self.l10n_bg_external_push_at)
            )
            receipts = device._l10n_bg_pull_sales(from_dt)
            steps.append(("pull_sales", True, f"{len(receipts)} receipts"))
        except Exception as exc:  # noqa: BLE001
            steps.append(("pull_sales", False, str(exc)[:200]))

        # 2. Import receipts as pos.order (tagged with this device)
        imported_orders = self.env["pos.order"]
        try:
            imported_orders = self._l10n_bg_import_receipts(
                receipts, device=device,
            )
            steps.append((
                "import_receipts", True,
                f"{len(imported_orders)} pos.orders created",
            ))
        except Exception as exc:  # noqa: BLE001
            steps.append(("import_receipts", False, str(exc)[:200]))

        # 3. Z-report (with retry, see Phase 4)
        z_result = {"ok": True, "z_number": 0, "total": 0.0,
                    "message": "auto_z_on_close=False"}
        if self.config_id.l10n_bg_auto_z_on_close:
            z_result = device._l10n_bg_print_z()
            steps.append((
                "z_report", z_result["ok"],
                f"Z#{z_result['z_number']} total={z_result['total']:.2f}"
                if z_result["ok"] else z_result["message"],
            ))
        else:
            steps.append(("z_report", True, "Skipped (auto_z disabled)"))

        # 4. Close fiscal.session
        if fsess and fsess.state == "open":
            imported_total = sum(imported_orders.mapped("amount_total"))
            discrepancy = imported_total - (z_result.get("total") or 0.0)
            if z_result["ok"]:
                fsess.write({
                    "state": "closed",
                    "closed_at": fields.Datetime.now(),
                    "z_report_number": z_result["z_number"],
                    "z_total_amount": z_result["total"],
                    "imported_receipt_count": len(imported_orders),
                    "discrepancy": discrepancy,
                })
                steps.append((
                    "close_fiscal_session", True,
                    f"Closed (discrepancy={discrepancy:.2f})",
                ))
            else:
                fsess.write({
                    "imported_receipt_count": len(imported_orders),
                })
                steps.append((
                    "close_fiscal_session", False,
                    "Z failed — fiscal.session stays open",
                ))
        else:
            steps.append((
                "close_fiscal_session", True,
                "No matching fiscal.session — skipped",
            ))

        return steps

    def _l10n_bg_import_receipts(self, receipts, device=None):
        """Create pos.order records from a normalised receipts list.

        Dedupe by `pos_reference` keyed on (device_id, receipt_number)
        — multi-device shops may emit the same fiscal receipt number
        from different cash registers, so the device id MUST be part
        of the key.

        Returns the recordset of newly created pos.order records.
        """
        self.ensure_one()
        if not receipts:
            return self.env["pos.order"]

        device_tag = f"D{device.id}/" if device else ""

        # Build PLU → product.product reverse lookup
        Plu = self.env["l10n.bg.fiscal.plu"]
        active_plus = Plu.search([
            ("company_id", "=", self.company_id.id),
            ("active", "=", True),
        ])
        plu_to_product = {}
        for p in active_plus:
            if p.product_ids:
                plu_to_product[p.plu_number] = p.product_ids[0]

        # Payment-method mapping: kind → pos.payment.method
        kind_to_method = {}
        for pm in self.config_id.payment_method_ids:
            k = pm.l10n_bg_external_kind
            if k and k not in kind_to_method:
                kind_to_method[k] = pm
        # Default fallback — first available cash, then any method
        default_pm = (
            kind_to_method.get("cash")
            or self.config_id.payment_method_ids[:1]
        )

        # Existing imported receipts in this session — dedupe key
        existing_refs = set(
            self.env["pos.order"].search([
                ("session_id", "=", self.id),
            ]).mapped("pos_reference")
        )

        created = self.env["pos.order"]
        for rec in receipts:
            ref = f"FP/{device_tag}{rec['number']}"
            if ref in existing_refs:
                continue

            lines_vals = []
            for it in rec["items"]:
                product = plu_to_product.get(it["plu"])
                if not product:
                    # Unknown PLU — skip line; could also raise but
                    # better to import-best-effort and warn.
                    _logger.warning(
                        "Receipt %s: unknown PLU %s — skipping line",
                        rec["number"], it["plu"],
                    )
                    continue
                lines_vals.append((0, 0, {
                    "product_id": product.id,
                    "qty": it["qty"],
                    "price_unit": it["price"],
                    "price_subtotal": it["qty"] * it["price"],
                    "price_subtotal_incl": it["qty"] * it["price"],
                }))

            if not lines_vals:
                continue

            payments_vals = []
            for pay in rec["payments"]:
                pm = kind_to_method.get(pay["kind"]) or default_pm
                if not pm:
                    continue
                payments_vals.append((0, 0, {
                    "amount": pay["amount"],
                    "payment_method_id": pm.id,
                    "name": fields.Datetime.now(),
                    "session_id": self.id,
                }))

            order_vals = {
                "session_id": self.id,
                "company_id": self.company_id.id,
                "pos_reference": ref,
                "amount_total": rec["total"],
                "amount_paid": rec["total"],
                "amount_return": 0.0,
                "amount_tax": 0.0,
                "lines": lines_vals,
                "payment_ids": payments_vals,
                "date_order": rec["datetime"] or fields.Datetime.now(),
                "state": "paid",
            }
            try:
                created |= self.env["pos.order"].create(order_vals)
            except Exception as exc:  # noqa: BLE001
                _logger.error(
                    "Failed to import receipt %s: %s", rec["number"], exc
                )
                continue
        return created

    def action_l10n_bg_external_force_close(self):
        """Force-close ALL still-open fiscal sessions for this pos.session
        without device communication. Use ONLY when the device(s) are
        offline; marks each as 'closed_partial' so back-office can
        reconcile manually with the device's Z-report.
        """
        self.ensure_one()
        open_fsess = self.l10n_bg_fiscal_session_ids.filtered(
            lambda fs: fs.state == "open"
        )
        if not open_fsess:
            return False
        open_fsess.write({
            "state": "closed_partial",
            "closed_at": fields.Datetime.now(),
        })
        names = ", ".join(open_fsess.mapped("name"))
        if hasattr(self, "message_post"):
            self.message_post(
                body=_(
                    "Force-closed without device contact: %s. "
                    "Reconcile manually with each device's Z-report."
                ) % names,
                message_type="notification",
            )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Force-close"),
                "message": _(
                    "%(n)d fiscal session(s) marked closed_partial."
                ) % {"n": len(open_fsess)},
                "type": "warning",
                "sticky": True,
            },
        }
