from odoo import _, api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    l10n_bg_nra_declaration_ids = fields.Many2many(
        "nra.declaration",
        compute="_compute_l10n_bg_nra_declarations",
        string="НАП Декларации",
        help="All NRA declarations that reference this employee by ЕГН. "
             "Declaration type plug-ins (ETZ, НОИ, etc.) register their "
             "line models via _l10n_bg_nra_declaration_lookups.",
    )
    l10n_bg_nra_declaration_count = fields.Integer(
        compute="_compute_l10n_bg_nra_declarations",
        string="НАП Декларации (брой)",
    )

    # ------------------------------------------------------------------
    # Extensibility hook — plug-in modules register their line models
    # ------------------------------------------------------------------

    def _l10n_bg_nra_declaration_lookups(self):
        """Return a list of (line_model_name, field_name) pairs used
        to find declarations referencing this employee.

        Each declaration-type plug-in (l10n_bg_api_nra_etz,
        l10n_bg_api_nra_noi, …) overrides this and appends its own
        line model + ЕГН field. The base module returns an empty list.
        """
        return []

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------

    @api.depends("identification_id")
    def _compute_l10n_bg_nra_declarations(self):
        Declaration = self.env["nra.declaration"]
        lookups = self._l10n_bg_nra_declaration_lookups()

        for employee in self:
            egn = (employee.identification_id or "").strip()
            if not egn or not lookups:
                employee.l10n_bg_nra_declaration_ids = False
                employee.l10n_bg_nra_declaration_count = 0
                continue

            declaration_ids = set()
            for model_name, egn_field in lookups:
                # Guard against modules being partially installed
                if model_name not in self.env:
                    continue
                lines = self.env[model_name].search([(egn_field, "=", egn)])
                declaration_ids.update(lines.mapped("declaration_id.id"))

            if declaration_ids:
                declarations = Declaration.browse(list(declaration_ids))
            else:
                declarations = Declaration.browse()
            employee.l10n_bg_nra_declaration_ids = declarations
            employee.l10n_bg_nra_declaration_count = len(declarations)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_view_l10n_bg_nra_declarations(self):
        """Open a list/form view of NRA declarations for this employee.

        Recomputes the declaration lookup on the fly (not relying on the
        cached Many2many field) so the domain is always in sync with the
        current state — and scopes strictly to this employee's ЕГН.
        """
        self.ensure_one()
        egn = (self.identification_id or "").strip()
        declaration_ids = set()
        if egn:
            for model_name, field_name in self._l10n_bg_nra_declaration_lookups():
                if model_name not in self.env:
                    continue
                lines = self.env[model_name].search([(field_name, "=", egn)])
                declaration_ids.update(lines.mapped("declaration_id.id"))

        action = {
            "type": "ir.actions.act_window",
            "name": _("НАП Декларации — %s", self.name),
            "res_model": "nra.declaration",
            "view_mode": "list,form",
            "target": "current",
            "domain": [("id", "in", list(declaration_ids))],
            "context": {
                "default_company_id": self.company_id.id,
                "create": False,
            },
            "help": _(
                "<p class='o_view_nocontent_smiling_face'>"
                "No NRA declarations for %(name)s yet"
                "</p>",
                name=self.name,
            ),
        }
        if len(declaration_ids) == 1:
            action.update({
                "view_mode": "form",
                "res_id": list(declaration_ids)[0],
                "views": [(False, "form")],
            })
        return action
