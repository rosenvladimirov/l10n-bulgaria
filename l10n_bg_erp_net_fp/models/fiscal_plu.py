"""
l10n.bg.fiscal.plu — Fiscal PLU Slot.

Per-company registry of PLU (Price Look-Up) slots that get pushed to
fiscal devices on POS session open. Each slot links to one or more
`product.product` records (M2M — supports synonymous items, bundles,
variant collapsing). The slot's `name` and `price` are a snapshot of
what's currently programmed on the device; the source of truth for
the price is `pos.config.pricelist_id`.

Mid-shift price/name changes do NOT trigger an automatic re-push —
the slot is marked `stale` and re-pushed on the next session open
(otherwise the device would mix old and new prices in the same
fiscal session, breaking the audit trail required by Наредба Н-18).
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class L10nBgFiscalPlu(models.Model):
    _name = "l10n.bg.fiscal.plu"
    _description = "Fiscal PLU Slot"
    _order = "plu_number"

    plu_number = fields.Integer(
        string="PLU #",
        required=True,
        index=True,
        copy=False,
        help="Slot number on the fiscal device (1..N depending on capacity).",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    source_pricelist_id = fields.Many2one(
        "product.pricelist",
        required=True,
        default=lambda self: self._default_source_pricelist(),
        help="Pricelist used to compute PLU price. Defaults to "
        "pos.config.pricelist_id of this company's POS configurations.",
    )
    product_ids = fields.Many2many(
        "product.product",
        "l10n_bg_fiscal_plu_product_rel",
        "plu_id",
        "product_id",
        string="Linked products",
        help="Products which trigger this PLU when scanned/sold. "
        "Multiple products → one PLU = synonymous items, bundles "
        "or variant collapsing.",
    )

    name = fields.Char(
        required=True,
        help="Article name printed on the fiscal receipt. Snapshot — "
        "synced from the canonical (first) linked product on demand.",
    )
    price = fields.Monetary(
        required=True,
        currency_field="currency_id",
        help="Price programmed on the device. Snapshot — synced from "
        "source pricelist on demand. Mid-shift changes mark the slot "
        "stale; re-push happens on next POS open.",
    )
    currency_id = fields.Many2one(
        related="source_pricelist_id.currency_id",
        store=True,
        readonly=True,
    )
    vat_group_id = fields.Many2one(
        "account.tax.group",
        string="VAT group",
        help="Maps to the device's tax slots (А/Б/В/Г in БГ).",
    )
    department_id = fields.Integer(
        string="Department",
        default=1,
        help="Device department slot (1..99). Default 1.",
    )

    active = fields.Boolean(
        default=True,
        help="Inactive slots are skipped during PLU push.",
    )
    push_state = fields.Selection(
        [
            ("pending", "Pending push"),
            ("pushed", "Pushed"),
            ("stale", "Stale (changed)"),
            ("conflict", "Conflict (M2M products disagree)"),
            ("name_drift", "Name drift (renamed)"),
            ("error", "Push error"),
        ],
        default="pending",
        required=True,
        index=True,
        copy=False,
    )
    push_message = fields.Char(
        readonly=True,
        copy=False,
        help="Human-readable detail of the current push_state — "
        "validation diagnostics or error message from the device.",
    )
    last_pushed_at = fields.Datetime(readonly=True, copy=False)
    last_validated_at = fields.Datetime(readonly=True, copy=False)
    note = fields.Text()

    _sql_constraints = [
        (
            "uniq_company_plu_number",
            "unique(company_id, plu_number)",
            "PLU number must be unique per company.",
        ),
    ]

    # ------------------------------------------------------------------
    # Defaults / computes
    # ------------------------------------------------------------------

    @api.model
    def _default_source_pricelist(self):
        """Pick the most reasonable pricelist:
        first pos.config.pricelist_id of the active company,
        else the company default pricelist.
        """
        company = self.env.company
        pos_cfg = self.env["pos.config"].search(
            [("company_id", "=", company.id), ("pricelist_id", "!=", False)],
            limit=1,
        )
        if pos_cfg:
            return pos_cfg.pricelist_id.id
        return self.env["product.pricelist"].search(
            [("company_id", "in", (False, company.id))],
            limit=1,
        ).id or False

    @api.depends("plu_number", "name")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = (
                f"#{rec.plu_number} {rec.name}"
                if rec.plu_number and rec.name
                else (rec.name or "/")
            )

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------

    def _set_state(self, state, message):
        """Set push_state + push_message, stamp last_validated_at."""
        self.ensure_one()
        self.write(
            {
                "push_state": state,
                "push_message": message,
                "last_validated_at": fields.Datetime.now(),
            }
        )
        return state, message

    # ------------------------------------------------------------------
    # Consistency check
    # ------------------------------------------------------------------

    def _check_consistency(self):
        """Validate a single PLU against its source pricelist + linked
        products. Sets push_state to one of:
          - 'pending'    — consistent, ready to push
          - 'stale'      — PLU.price ≠ pricelist eval
          - 'conflict'   — linked products evaluate to different prices
          - 'name_drift' — PLU.name ≠ canonical product display_name
          - 'error'      — no products linked / pricelist missing
        """
        self.ensure_one()
        if not self.product_ids:
            return self._set_state("error", _("No products linked to PLU."))
        if not self.source_pricelist_id:
            return self._set_state("error", _("No source pricelist set."))

        pl = self.source_pricelist_id
        prices = {p: pl._get_product_price(p, quantity=1.0) for p in self.product_ids}
        unique = {round(p, 2) for p in prices.values()}

        if len(unique) > 1:
            diff = ", ".join(
                f"{p.display_name}={pr:.2f}" for p, pr in prices.items()
            )
            return self._set_state(
                "conflict",
                _("Products in PLU have different pricelist prices: %s") % diff,
            )

        expected_price = next(iter(unique))
        canonical = self.product_ids[0]
        expected_name = canonical.display_name

        if abs((self.price or 0.0) - expected_price) > 0.005:
            return self._set_state(
                "stale",
                _("PLU price %(plu)s ≠ pricelist %(pl)s")
                % {"plu": f"{self.price:.2f}", "pl": f"{expected_price:.2f}"},
            )

        if self.name != expected_name:
            return self._set_state(
                "name_drift",
                _("PLU name '%(plu)s' ≠ product '%(prod)s'")
                % {"plu": self.name, "prod": expected_name},
            )

        return self._set_state("pending", _("Consistent — ready to push."))

    def action_check_consistency(self):
        """Manual consistency check (button). Returns the records as
        an action so the UI refreshes with the new states."""
        for rec in self:
            rec._check_consistency()
        return True

    # ------------------------------------------------------------------
    # Sync from pricelist
    # ------------------------------------------------------------------

    def action_sync_from_pricelist(self):
        """Pull current name + price from source pricelist into the
        snapshot fields. Resets push_state to 'pending'.
        """
        for rec in self:
            if not rec.product_ids:
                continue
            canonical = rec.product_ids[0]
            rec.name = canonical.display_name
            rec.price = rec.source_pricelist_id._get_product_price(
                canonical, quantity=1.0
            )
            rec.push_state = "pending"
            rec.push_message = _(
                "Synced from pricelist '%s'."
            ) % rec.source_pricelist_id.name
            rec.last_validated_at = fields.Datetime.now()
        return True

    # ------------------------------------------------------------------
    # Auto-allocate next free PLU number
    # ------------------------------------------------------------------

    @api.model
    def _next_free_plu(self, company_id, max_capacity=10000):
        """Find the lowest unused PLU number for the given company,
        gap-fill (1, 2, 4 free → returns 3). max_capacity is a sanity
        ceiling; real device limits enforced at push time.
        """
        used = set(
            self.with_context(active_test=False)
            .search([("company_id", "=", company_id)])
            .mapped("plu_number")
        )
        for n in range(1, max_capacity + 1):
            if n not in used:
                return n
        raise UserError(
            _(
                "PLU capacity exceeded (%s slots used). Deactivate "
                "unused slots first."
            )
            % len(used)
        )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("plu_number"):
                vals["plu_number"] = self._next_free_plu(
                    vals.get("company_id") or self.env.company.id
                )
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Manual push to device (retry / forced)
    # ------------------------------------------------------------------

    def action_push_to_device(self):
        """Push the selected PLUs to all fiscal devices configured on
        the company's POS configurations. Skips PLUs in 'conflict' or
        'error' state (they need manual fix first).

        Useful for retry after a failed open-time push, or for ad-hoc
        re-program of a single PLU without reopening the session.
        """
        self.ensure_one() if len(self) == 1 else None
        if not self:
            return False
        # Group by company; same company → same device set
        by_company = {}
        for rec in self:
            by_company.setdefault(rec.company_id.id, self.env[self._name])
            by_company[rec.company_id.id] |= rec

        results = []
        for company_id, plus in by_company.items():
            # Run consistency first — exclude conflict/error
            for p in plus:
                p._check_consistency()
            pushable = plus.filtered(
                lambda r: r.push_state in ("pending", "stale", "name_drift", "pushed")
            )
            if not pushable:
                results.append(
                    f"Company #{company_id}: nothing to push "
                    f"(all in conflict/error state)."
                )
                continue
            devices = self.env["pos.config"].search([
                ("company_id", "=", company_id),
                ("l10n_bg_fiscal_printer_id", "!=", False),
            ]).mapped("l10n_bg_fiscal_printer_id")
            if not devices:
                results.append(
                    f"Company #{company_id}: no fiscal devices configured "
                    f"on any POS config."
                )
                continue
            for device in devices:
                ok = device._l10n_bg_push_plu_registry(pushable)
                results.append(
                    f"{device.name}: {'OK' if ok else 'FAILED'} "
                    f"({len(pushable)} PLUs)"
                )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Manual PLU push"),
                "message": "\n".join(results),
                "type": "info",
                "sticky": True,
            },
        }
