# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Воден „вертикален" инсталатор на българската локализация.

Заменя ad-hoc чекбоксовете в res.config.settings с подредени секции
(вертикали V0–V12). Секция се отключва само ако предходната (по
sequence) е инсталирана; иначе стои read-only. Всяка стъпка прави
РЕАЛНА инсталация (`button_immediate_install`, НЕ upgrade) и отваря
междинния config action, после изчаква ръчен checkpoint.

Безопасност (поука от Teo инцидента 2026-05-18): модулите се резолват
по име в runtime; ако модулът липсва в addons пътя на инстанцията —
стъпката е „unavailable" (read-only, без грешка) и НЕ блокира веригата.
"""

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class L10nBgVertical(models.Model):
    _name = "l10n.bg.vertical"
    _description = "Bulgarian Localization Installation Vertical"
    _order = "sequence, code"

    code = fields.Char(required=True, index=True, help="Stable code, e.g. V0.")
    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10, index=True)
    edition = fields.Selection(
        selection=[
            ("any", "Any edition"),
            ("ce", "Community"),
            ("ee", "Enterprise bridge"),
            ("oca", "OCA channel"),
            ("opl", "Expert (OPL-1)"),
        ],
        default="any",
        required=True,
    )
    description = fields.Text(translate=True)
    step_ids = fields.One2many(
        "l10n.bg.vertical.step", "vertical_id", string="Steps"
    )

    # Per-company изчислени (нестори — config екран, малък обем).
    step_total = fields.Integer(compute="_compute_progress")
    step_done = fields.Integer(compute="_compute_progress")
    progress = fields.Float(
        compute="_compute_progress", help="Share of required steps done."
    )
    done = fields.Boolean(compute="_compute_progress")
    is_unlocked = fields.Boolean(
        compute="_compute_state",
        help="True if the previous vertical is completed (or this is "
        "the first one). A locked vertical is read-only.",
    )
    state = fields.Selection(
        selection=[
            ("locked", "Locked"),
            ("available", "Available"),
            ("in_progress", "In progress"),
            ("done", "Completed"),
        ],
        compute="_compute_state",
    )

    _sql_constraints = [
        ("code_uniq", "unique(code)", "Vertical code must be unique."),
    ]

    @api.depends("step_ids")
    @api.depends_context("company")
    def _compute_progress(self):
        for vertical in self:
            steps = vertical.step_ids
            # Изискваните стъпки = налични, незадължителни. Недостъпните
            # (липсващ модул в тази инстанция) НЕ блокират веригата.
            required = steps.filtered(
                lambda s: s.available and not s.optional
            )
            done = required.filtered(lambda s: s.done)
            vertical.step_total = len(required)
            vertical.step_done = len(done)
            vertical.progress = (
                100.0 * len(done) / len(required) if required else 100.0
            )
            vertical.done = bool(required) and len(done) == len(required) or (
                not required and bool(steps)
            )

    @api.depends("sequence", "code", "step_ids")
    @api.depends_context("company")
    def _compute_state(self):
        ordered = self.search([])
        done_map = {v.id: v.done for v in ordered}
        prev_done = True
        unlocked_ids = set()
        for vertical in ordered:
            if prev_done:
                unlocked_ids.add(vertical.id)
            prev_done = done_map.get(vertical.id, False)
        for vertical in self:
            unlocked = vertical.id in unlocked_ids
            vertical.is_unlocked = unlocked
            if not unlocked:
                vertical.state = "locked"
            elif vertical.done:
                vertical.state = "done"
            elif vertical.step_done:
                vertical.state = "in_progress"
            else:
                vertical.state = "available"

    @api.model
    def _l10n_bg_resume_vertical(self):
        """Вертикалът, на който инсталаторът да стартира: първият
        наличен/в-прогрес; иначе първият незавършен; иначе първият
        (всички готови → отваря последователността от началото)."""
        verticals = self.search([])
        if not verticals:
            return verticals
        resume = verticals.filtered(
            lambda v: v.state in ("available", "in_progress")
        )
        if resume:
            return resume[:1]
        not_done = verticals.filtered(lambda v: not v.done)
        return (not_done or verticals)[:1]

    def action_open_wizard(self):
        """Отваря многостъпковия инсталатор, позициониран на тази
        секция. Заключена секция (предходната не е инсталирана) не се
        отваря директно — стои read-only в списъка."""
        self.ensure_one()
        if not self.is_unlocked:
            raise UserError(
                _(
                    "Section '%s' is locked. Complete the previous "
                    "vertical first."
                )
                % self.code
            )
        wizard = self.env["l10n.bg.vertical.wizard"].create(
            {"vertical_id": self.id}
        )
        return wizard._open()


class L10nBgVerticalStep(models.Model):
    _name = "l10n.bg.vertical.step"
    _description = "Bulgarian Localization Installation Step"
    _order = "vertical_id, sequence, id"

    vertical_id = fields.Many2one(
        "l10n.bg.vertical", required=True, ondelete="cascade", index=True
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True, translate=True)
    step_type = fields.Selection(
        selection=[
            ("install_module", "Install module"),
            ("config_action", "Configuration"),
            ("checkpoint", "Manual checkpoint"),
        ],
        required=True,
        default="install_module",
    )
    module_name = fields.Char(
        help="Technical name of the module to install (resolved at "
        "runtime; if absent in this instance the step is unavailable)."
    )
    action_xmlid = fields.Char(
        help="Optional XML id of the configuration action to open."
    )
    instruction = fields.Text(
        translate=True,
        help="Guidance for configuration / manual checkpoint steps.",
    )
    edition = fields.Selection(
        selection=[
            ("any", "Any"),
            ("ce", "Community"),
            ("ee", "Enterprise"),
            ("oca", "OCA"),
            ("opl", "Expert"),
        ],
        default="any",
    )
    optional = fields.Boolean(
        help="Optional step — does not block the vertical / next ones."
    )
    skip_if_auto_install = fields.Boolean(
        help="Module auto-installs with a counterpart — the installer "
        "must not act on it manually."
    )
    channel_group = fields.Char(
        help="Mutually-exclusive channel tag (e.g. one InfoPay bridge, "
        "one ErpNet.FP IoT bridge). Informational for the operator."
    )
    registry_fetch = fields.Boolean(
        help="When set, the installer offers an inline 'fetch company "
        "data from the Bulgarian Trade Register by VAT/UIC' control "
        "bound to this checkpoint step (auto-installs "
        "l10n_bg_company_registry on demand)."
    )

    module_state = fields.Char(compute="_compute_runtime")
    available = fields.Boolean(compute="_compute_runtime")
    done = fields.Boolean(compute="_compute_runtime")
    state = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("done", "Done"),
            ("skipped", "Skipped"),
            ("unavailable", "Unavailable"),
            ("auto", "Auto-installed"),
        ],
        compute="_compute_runtime",
    )

    def _get_module(self):
        """ir.module.module по `module_name` или празен recordset."""
        self.ensure_one()
        if not self.module_name:
            return self.env["ir.module.module"]
        return (
            self.env["ir.module.module"]
            .sudo()
            .search([("name", "=", self.module_name)], limit=1)
        )

    @api.depends(
        "step_type", "module_name", "skip_if_auto_install", "optional"
    )
    @api.depends_context("company")
    def _compute_runtime(self):
        Progress = self.env["l10n.bg.vertical.progress"].sudo()
        company = self.env.company
        prog = {
            p.step_id.id: p
            for p in Progress.search([("company_id", "=", company.id)])
        }
        for step in self:
            mod = step._get_module() if step.step_type == "install_module" else None
            mstate = mod.state if mod else False
            step.module_state = mstate or ""
            done = False
            available = True
            state = "pending"
            if step.step_type == "install_module":
                if not mod:
                    # Модулът не е сканиран/липсва в addons на тази
                    # инстанция → недостъпен, без грешка, не блокира.
                    available = False
                    state = "unavailable"
                elif mstate in ("installed", "to upgrade"):
                    done = True
                    state = (
                        "auto" if step.skip_if_auto_install else "done"
                    )
                elif mstate == "uninstallable":
                    available = False
                    state = "unavailable"
                else:
                    state = "auto" if step.skip_if_auto_install else "pending"
            else:
                # config_action / checkpoint → ръчно потвърждение
                p = prog.get(step.id)
                if p and p.done:
                    done = True
                    state = "done"
            step.available = available
            step.done = done
            step.state = state

    # ── действия ───────────────────────────────────────────────────────
    def _reopen_wizard(self):
        """Връща action, който преотваря стъпер-модала на текущия
        вертикал. В `target='new'` диалог row-бутон, който върне
        falsy, ЗАТВАРЯ диалога — затова всяко row-действие трябва да
        върне това (както footer Back/Next правят `wizard._open()`).
        Wizard id идва през context-а на списъка
        (`{'l10n_bg_wiz_id': id}` в `step_ids`)."""
        wid = self.env.context.get("l10n_bg_wiz_id")
        if not wid:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": _("Bulgarian Localization Installer"),
            "res_model": "l10n.bg.vertical.wizard",
            "res_id": wid,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
        }

    def _ensure_unlocked(self):
        self.ensure_one()
        if not self.vertical_id.is_unlocked:
            raise UserError(
                _(
                    "Vertical '%s' is locked. Complete the previous "
                    "vertical first."
                )
                % self.vertical_id.code
            )

    def action_install(self):
        """РЕАЛНА инсталация — само `button_immediate_install`, НИКОГА
        upgrade (поука от Teo: каскаден upgrade чупи registry-то)."""
        self.ensure_one()
        self._ensure_unlocked()
        if self.step_type != "install_module":
            raise UserError(_("This step is not a module installation."))
        mod = self._get_module()
        if not mod:
            raise UserError(
                _(
                    "Module '%s' is not available in this instance "
                    "(not in the addons path). Deploy it first."
                )
                % (self.module_name or "")
            )
        if mod.state in ("installed", "to upgrade"):
            # Вече инсталиран — нищо за правене; преотвори стъпера
            # (НЕ client reload, НЕ falsy — и двете затварят модала).
            return self._reopen_wizard()
        if mod.state == "uninstallable":
            raise UserError(
                _("Module '%s' is not installable.") % self.module_name
            )
        if self.skip_if_auto_install:
            raise UserError(
                _(
                    "Module '%s' auto-installs with its counterpart — "
                    "do not install it manually."
                )
                % self.module_name
            )
        mod.button_immediate_install()
        # НЕ client reload (затваря модала, дразнещо) и НЕ falsy (също
        # затваря диалога). Преотваряме стъпера на същия вертикал →
        # `_compute_runtime` показва стъпката „done", операторът
        # продължава. (Новоинсталираният модул носи свои менюта/assets,
        # които се появяват при ръчен refresh / на Finish — без
        # значение за самия инсталатор.)
        return self._reopen_wizard()

    def action_open_config(self):
        """Отваря междинния config action или показва инструкцията."""
        self.ensure_one()
        self._ensure_unlocked()
        if self.action_xmlid:
            action = self.env.ref(self.action_xmlid, raise_if_not_found=False)
            if action:
                return action.sudo().read()[0]
        if self.instruction:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": self.name,
                    "message": self.instruction,
                    "sticky": True,
                    "type": "info",
                },
            }
        raise UserError(
            _("No configuration action or instruction defined for '%s'.")
            % self.name
        )

    def _set_progress(self, done):
        self.ensure_one()
        Progress = self.env["l10n.bg.vertical.progress"].sudo()
        company = self.env.company
        rec = Progress.search(
            [("company_id", "=", company.id), ("step_id", "=", self.id)],
            limit=1,
        )
        vals = {"done": done, "done_date": fields.Datetime.now()}
        if rec:
            rec.write(vals)
        else:
            Progress.create(
                dict(vals, company_id=company.id, step_id=self.id)
            )
        # Mark done/reset/checkpoint — преотвори стъпера (falsy би
        # затворил target='new' диалога). Стъпката се преизчислява и
        # операторът остава в инсталатора.
        return self._reopen_wizard()

    def action_mark_done(self):
        self.ensure_one()
        self._ensure_unlocked()
        return self._set_progress(True)

    def action_reset(self):
        self.ensure_one()
        return self._set_progress(False)


class L10nBgVerticalProgress(models.Model):
    _name = "l10n.bg.vertical.progress"
    _description = "Bulgarian Localization Step Progress (per company)"
    _rec_name = "step_id"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
        ondelete="cascade",
    )
    step_id = fields.Many2one(
        "l10n.bg.vertical.step",
        required=True,
        index=True,
        ondelete="cascade",
    )
    done = fields.Boolean()
    done_date = fields.Datetime()
    note = fields.Text()

    _sql_constraints = [
        (
            "company_step_uniq",
            "unique(company_id, step_id)",
            "One progress record per company and step.",
        ),
    ]
