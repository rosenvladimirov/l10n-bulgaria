"""
PLU push wizard — pick a target device set, preview the plan, push.

Replaces the old `fiscal_plu.action_push_to_device` button which
implicitly fanned out to every fiscal device on the company. That
implicit fan-out caused the well-known "PLU sync failed: Timeout: no
response from browser within 90s" surprise — the call was hitting an
unrelated proxy/printer that the operator didn't even mean to target.

Wizard flow:
  1. Open from a list selection, a single PLU form, the
     fiscal.printer.device form, or the top menu — entry-point sets
     a smart default scope (selected if any, else pending).
  2. Pick one or more target devices. Default = every device
     configured on a pos.config in the same company.
  3. Run with dry_run=True (default) to see exactly which slots get
     INSERT/UPDATE/NOOP per device, with old-vs-new prices.
  4. Uncheck dry_run, Run again to push for real.

Block-on-conflict policy: any PLU in `conflict` state aborts the run
with a UserError before any device call. Forces the operator to
resolve the conflict first instead of silently skipping it.
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class L10nBgFiscalPluPushWizard(models.TransientModel):
    _name = "l10n.bg.fiscal.plu.push.wizard"
    _description = "Push PLUs to fiscal device(s)"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )

    # ─── Scope (which PLUs to push) ─────────────────────────────────

    scope = fields.Selection(
        [
            ("selected", "Selected PLUs only"),
            ("pending", "All Pending + Stale"),
            ("all_pushable", "All except Conflict / Error"),
        ],
        required=True,
        default=lambda self: self._default_scope(),
    )
    plu_ids = fields.Many2many(
        "l10n.bg.fiscal.plu",
        string="PLUs",
        domain="[('company_id', '=', company_id)]",
    )

    # ─── Target (which devices) ─────────────────────────────────────

    device_ids = fields.Many2many(
        "fiscal.printer.device",
        string="Target devices",
        required=True,
        default=lambda self: self._default_devices(),
    )

    # ─── Mode ───────────────────────────────────────────────────────

    dry_run = fields.Boolean(
        string="Dry-run (preview only)",
        default=True,
        help="Preview the plan without sending anything to the device. "
        "Uncheck and Run again to push for real.",
    )

    # ─── Output (populated after Run) ───────────────────────────────

    summary_html = fields.Html(readonly=True)
    last_run_at = fields.Datetime(readonly=True)

    # ─── Defaults (entry-point aware) ───────────────────────────────

    @api.model
    def _default_scope(self):
        """If launched with active records (mass-action / form button),
        default to 'selected'; otherwise 'pending'."""
        ctx = self.env.context
        if ctx.get("active_model") == "l10n.bg.fiscal.plu" and ctx.get(
            "active_ids"
        ):
            return "selected"
        return "pending"

    @api.model
    def _default_devices(self):
        """All fiscal devices configured on a pos.config in the current
        company. Pre-fills the M2M so the common single-device case
        is one click — the operator can prune if they want."""
        company = self.env.company
        if not company:
            return False
        pos_devices = (
            self.env["pos.config"]
            .search(
                [
                    ("company_id", "=", company.id),
                    ("l10n_bg_fiscal_printer_id", "!=", False),
                ]
            )
            .mapped("l10n_bg_fiscal_printer_id")
        )
        return pos_devices

    @api.model
    def default_get(self, fields_list):
        """Pre-populate plu_ids from active_ids when launched from a
        list mass action or single-record form button."""
        vals = super().default_get(fields_list)
        ctx = self.env.context
        if ctx.get("active_model") == "l10n.bg.fiscal.plu" and ctx.get(
            "active_ids"
        ):
            vals["plu_ids"] = [(6, 0, list(ctx["active_ids"]))]
        return vals

    # ─── Resolve scope → recordset ──────────────────────────────────

    def _resolve_plus(self):
        """Return the l10n.bg.fiscal.plu recordset implied by `scope`."""
        self.ensure_one()
        Plu = self.env["l10n.bg.fiscal.plu"]
        if self.scope == "selected":
            return self.plu_ids.filtered(
                lambda p: p.company_id == self.company_id
            )
        domain = [("company_id", "=", self.company_id.id), ("active", "=", True)]
        if self.scope == "pending":
            domain.append(("push_state", "in", ("pending", "stale", "name_drift")))
        elif self.scope == "all_pushable":
            domain.append(
                ("push_state", "not in", ("conflict", "error"))
            )
        return Plu.search(domain)

    # ─── The action ─────────────────────────────────────────────────

    def action_run(self):
        self.ensure_one()
        if not self.device_ids:
            raise UserError(_("Pick at least one target device."))

        plus = self._resolve_plus()
        if not plus:
            raise UserError(
                _("No PLUs match the selected scope on company %s.")
                % self.company_id.display_name
            )

        # Run consistency first so push_state is fresh for the conflict
        # gate below — handles the case where a price changed since the
        # PLU was last validated but `_check_consistency` hasn't been
        # rerun.
        for plu in plus:
            plu._check_consistency()

        conflicts = plus.filtered(lambda p: p.push_state in ("conflict", "error"))
        if conflicts:
            lines = "\n".join(
                f"  • {p.display_name}: {p.push_message or p.push_state}"
                for p in conflicts
            )
            raise UserError(
                _(
                    "Cannot push — %(n)d PLU(s) are in conflict/error. "
                    "Fix them first:\n\n%(lines)s"
                )
                % {"n": len(conflicts), "lines": lines}
            )

        pushable = plus.filtered(
            lambda p: p.push_state in ("pending", "stale", "name_drift", "pushed")
        )
        if not pushable:
            raise UserError(
                _("Nothing to push after consistency check.")
            )

        per_device = []
        for device in self.device_ids:
            per_device.append(self._run_for_device(device, pushable))

        self.write(
            {
                "summary_html": self._render_summary(per_device, dry=self.dry_run),
                "last_run_at": fields.Datetime.now(),
            }
        )
        # Reopen the wizard so the user sees the result without losing
        # the form state (selected scope, devices, etc.).
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def _run_for_device(self, device, plus):
        """Either simulate the push (dry_run) or execute it. Returns a
        dict for the per-device summary block."""
        self.ensure_one()
        plan = self._plan_for_device(device, plus)
        if self.dry_run:
            return {"device": device, "plan": plan, "ok": None, "error": None}
        try:
            ok = device._l10n_bg_push_plu_registry(plus)
            return {"device": device, "plan": plan, "ok": bool(ok), "error": None}
        except Exception as exc:  # noqa: BLE001
            return {
                "device": device,
                "plan": plan,
                "ok": False,
                "error": str(exc),
            }

    def _plan_for_device(self, device, plus):
        """Build the per-PLU action plan: INSERT / UPDATE / NOOP, with
        old-vs-new where available. We do NOT call the device for the
        'old' values — `plu.last_pushed_at` + `plu_programmed` are the
        best snapshot we have without round-tripping every PLU.
        """
        plan = []
        for plu in plus:
            if not plu.last_pushed_at:
                action = "INSERT"
            elif plu.push_state == "stale":
                action = "UPDATE"
            elif plu.push_state == "name_drift":
                action = "UPDATE (name)"
            elif plu.push_state == "pushed":
                action = "NOOP"
            else:
                action = "UPDATE"
            plan.append(
                {
                    "slot": plu.slot,
                    "name": plu.name,
                    "price": plu.price,
                    "state": plu.push_state,
                    "action": action,
                }
            )
        return plan

    def _render_summary(self, per_device, dry):
        """HTML for the wizard's read-only summary field."""
        prefix = (
            _("Dry-run preview — nothing was sent to any device.")
            if dry
            else _("Push completed.")
        )
        chunks = [f"<p><b>{prefix}</b></p>"]
        for entry in per_device:
            d = entry["device"]
            plan = entry["plan"]
            if dry:
                status = _("(preview)")
            elif entry["ok"]:
                status = _("✓ OK")
            else:
                status = _("✗ FAILED: %s") % (entry["error"] or "unknown")
            chunks.append(
                f"<h4>{d.name} — {len(plan)} PLU(s) {status}</h4>"
            )
            chunks.append(
                "<table class='table table-sm'>"
                "<thead><tr>"
                f"<th>{_('Slot')}</th>"
                f"<th>{_('Action')}</th>"
                f"<th>{_('Name')}</th>"
                f"<th>{_('Price')}</th>"
                f"<th>{_('State')}</th>"
                "</tr></thead><tbody>"
            )
            for row in plan:
                chunks.append(
                    "<tr>"
                    f"<td>{row['slot']}</td>"
                    f"<td>{row['action']}</td>"
                    f"<td>{row['name']}</td>"
                    f"<td>{row['price']:.2f}</td>"
                    f"<td>{row['state']}</td>"
                    "</tr>"
                )
            chunks.append("</tbody></table>")
        return "\n".join(chunks)
