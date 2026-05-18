# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Многостъпков воден инсталатор на българската локализация.

Един wizard, който се отваря с бутон от секцията Settings и върви
вертикал по вертикал (V0→V12) — една стъпка = един вертикал. Всеки
екран показва подстъпките на текущия вертикал (Install / Open config /
Mark done). Навигацията е Back / Skip / Next:

- **Next** е заключен докато текущият вертикал не е завършен (същият
  gating както досега — `l10n.bg.vertical.done`); на последния
  завършен вертикал Next става Finish и затваря визарда.
- **Skip** премества само изгледа напред (оглед на по-късни вертикали);
  заключен вертикал остава read-only и реалните действия по стъпките
  пак минават през `_ensure_unlocked()` — Skip НЕ заобикаля gating-а.
- **Back** се връща на предходния вертикал.

Цялата инсталационна/gating логика остава в `l10n.bg.vertical[.step]`.
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class L10nBgVerticalWizard(models.TransientModel):
    _name = "l10n.bg.vertical.wizard"
    _description = "Bulgarian Localization Vertical Installer Wizard"

    vertical_id = fields.Many2one(
        "l10n.bg.vertical", required=True, ondelete="cascade"
    )
    code = fields.Char(related="vertical_id.code", readonly=True)
    name = fields.Char(related="vertical_id.name", readonly=True)
    edition = fields.Selection(
        related="vertical_id.edition", readonly=True
    )
    description = fields.Text(
        related="vertical_id.description", readonly=True
    )
    state = fields.Selection(related="vertical_id.state", readonly=True)
    progress = fields.Float(
        related="vertical_id.progress", readonly=True
    )
    step_ids = fields.Many2many(
        "l10n.bg.vertical.step",
        compute="_compute_step_ids",
        string="Steps",
    )

    # ── навигация (стъпер) ──────────────────────────────────────────────
    position = fields.Integer(compute="_compute_nav")
    total = fields.Integer(compute="_compute_nav")
    step_label = fields.Char(compute="_compute_nav")
    is_first = fields.Boolean(compute="_compute_nav")
    is_last = fields.Boolean(compute="_compute_nav")
    next_locked = fields.Boolean(
        compute="_compute_nav",
        help="True while the current vertical is not yet completed — "
        "the Next button stays disabled (gating).",
    )

    # ── Trade Register auto-fill (само за вертикал с registry_fetch стъпка) ─
    registry_step_id = fields.Many2one(
        "l10n.bg.vertical.step",
        compute="_compute_registry",
        help="Checkpoint step in the current vertical that offers the "
        "Trade Register auto-fill, if any.",
    )
    show_registry_fetch = fields.Boolean(compute="_compute_registry")
    registry_vat_eik = fields.Char(
        string="VAT / UIC",
        help="Bulgarian VAT (BG…) or UIC/EIK (9 or 13 digits) to look "
        "up in the Trade Register.",
    )

    def _compute_step_ids(self):
        for wiz in self:
            wiz.step_ids = wiz.vertical_id.step_ids

    @api.depends("vertical_id")
    def _compute_registry(self):
        for wiz in self:
            step = wiz.vertical_id.step_ids.filtered("registry_fetch")[:1]
            wiz.registry_step_id = step
            wiz.show_registry_fetch = bool(step)

    @api.depends("vertical_id", "vertical_id.done")
    @api.depends_context("company")
    def _compute_nav(self):
        ordered = self.env["l10n.bg.vertical"].search([])
        ids = ordered.ids
        total = len(ids)
        for wiz in self:
            idx = ids.index(wiz.vertical_id.id) if wiz.vertical_id.id in ids else 0
            wiz.position = idx + 1
            wiz.total = total
            wiz.step_label = _(
                "Step %(pos)s / %(total)s", pos=idx + 1, total=total
            )
            wiz.is_first = idx == 0
            wiz.is_last = idx + 1 >= total
            wiz.next_locked = not wiz.vertical_id.done

    # ── helpers ─────────────────────────────────────────────────────────
    def _open(self):
        """Преотваря същия wizard запис (модал) — стандартен Odoo
        многоекранен паттерн: мутираме `vertical_id` и пре-четем."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Bulgarian Localization Installer"),
            "res_model": "l10n.bg.vertical.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
        }

    def _ordered_ids(self):
        return self.env["l10n.bg.vertical"].search([]).ids

    # ── действия ────────────────────────────────────────────────────────
    def action_back(self):
        self.ensure_one()
        ids = self._ordered_ids()
        idx = ids.index(self.vertical_id.id)
        if idx > 0:
            self.vertical_id = ids[idx - 1]
        return self._open()

    def action_skip(self):
        """Само навигация напред (оглед); НЕ заобикаля gating-а —
        заключеният вертикал остава read-only."""
        self.ensure_one()
        ids = self._ordered_ids()
        idx = ids.index(self.vertical_id.id)
        if idx + 1 < len(ids):
            self.vertical_id = ids[idx + 1]
            return self._open()
        return {"type": "ir.actions.act_window_close"}

    def action_next(self):
        self.ensure_one()
        if not self.vertical_id.done:
            raise UserError(
                _(
                    "Complete vertical '%s' before continuing."
                )
                % self.vertical_id.code
            )
        ids = self._ordered_ids()
        idx = ids.index(self.vertical_id.id)
        if idx + 1 < len(ids):
            self.vertical_id = ids[idx + 1]
            return self._open()
        # последният завършен вертикал → Finish
        return {"type": "ir.actions.act_window_close"}

    def action_refresh(self):
        """Презарежда визарда (след install/config действие)."""
        self.ensure_one()
        return self._open()

    def action_registry_fetch(self):
        """Свали данните на фирмата от Търговския регистър по ДДС/ЕИК,
        попълни фирмения партньор, постави държава = България и маркирай
        чекпойнт стъпката готова. Auto-install на
        l10n_bg_company_registry при липса (install, НЕ upgrade —
        поука от Teo: каскаден upgrade чупи registry-то)."""
        self.ensure_one()
        step = self.registry_step_id
        if not step:
            raise UserError(_("This vertical has no Trade Register step."))
        if not self.registry_vat_eik:
            raise UserError(_("Enter a VAT number or UIC first."))
        Module = self.env["ir.module.module"].sudo()
        mod = Module.search(
            [("name", "=", "l10n_bg_company_registry")], limit=1
        )
        if not mod:
            raise UserError(
                _(
                    "Module 'l10n_bg_company_registry' is not available "
                    "in this instance (not in the addons path). Deploy "
                    "it first."
                )
            )
        if mod.state == "uninstallable":
            raise UserError(
                _("Module 'l10n_bg_company_registry' is not installable.")
            )
        if mod.state not in ("installed", "to upgrade"):
            mod.button_immediate_install()
            # НЕ client reload (затваря стъпер-модала — дразни).
            # Преотваряме стъпера на същия вертикал; операторът натиска
            # „Fetch" пак — модулът вече е инсталиран и fetch-ът минава
            # (новият модел е годен в следващата заявка; НЕ правим fetch
            # в същата транзакция веднага след install).
            return self._open()
        company = self.env.company
        partner = company.partner_id
        if not partner:
            raise UserError(_("The active company has no linked partner."))
        Wizard = self.env["bg.company.search.wizard"]
        try:
            rw = Wizard.create(
                {"partner_id": partner.id, "eik": self.registry_vat_eik}
            )
            rw.action_fetch_data()
            rw.action_populate_partner()
        except UserError:
            raise
        except Exception as exc:
            raise UserError(
                _("Trade Register fetch failed: %s") % exc
            ) from exc
        bg = self.env.ref("base.bg", raise_if_not_found=False)
        if bg:
            if company.country_id != bg:
                company.country_id = bg.id
            if partner.country_id != bg:
                partner.country_id = bg.id
        # чекпойнтът е готов → маркирай и презареди стъпера
        step.action_mark_done()
        return self._open()
