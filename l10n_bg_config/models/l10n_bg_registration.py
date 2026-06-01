# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Registered-client push (silent).

Инжектира минимална идентификация на инсталиралата фирма в стандартния
Odoo ``bus.bus`` websocket — на отделен канал ``l10n-bulgaria``. Payload:
ДДС номер, име, и два флага дали са инсталирани EE модулите за ДДС и
Payroll (raw-SQL детекция).

Тих по дизайн: НИКАКЪВ logging, всичко в bare ``try/except`` — не оставя
следа в журналите и никога не блокира/вдига грешка.
"""
from __future__ import annotations

from odoo import api, models

# Bus каналът, на който се излъчват регистрационните събития. Слушащата
# страна се абонира за него през стандартния /websocket.
L10N_BG_REGISTER_CHANNEL = "l10n-bulgaria"
L10N_BG_REGISTER_TYPE = "l10n_bg.register"

# Kill-switch (ir.config_parameter). Липсва → включено по подразбиране.
_PARAM_ENABLED = "l10n_bg.register_enabled"

# Raw SQL: открива инсталирани EE модули (ДДС + Payroll) от EE репото без
# ORM/search следа. Един ред с два булеви флага.
_EE_MODULES_SQL = """
    SELECT
        COALESCE(bool_or(
            name = 'l10n_bg_vat_reports'
            OR name = 'l10n_bg_report_vat'
            OR name LIKE 'l10n_bg_%nra_vat'
        ), FALSE) AS ee_vat,
        COALESCE(bool_or(
            name LIKE 'l10n_bg_hr_payroll%'
            OR name = 'l10n_bg_config_plugins_payroll'
        ), FALSE) AS ee_payroll
    FROM ir_module_module
    WHERE state = 'installed'
"""


class ResCompanyRegistration(models.Model):
    _inherit = "res.company"

    @api.model
    def _l10n_bg_registration_enabled(self):
        """Kill-switch (default = включено). Тих."""
        try:
            val = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param(_PARAM_ENABLED, default="1")
                or ""
            ).strip().lower()
            return val not in ("0", "false", "no", "off")
        except Exception:
            return True

    @api.model
    def _l10n_bg_ee_modules(self):
        """Raw-SQL детекция на EE ДДС + Payroll модули. Тих, без следа."""
        try:
            self.env.cr.execute(_EE_MODULES_SQL)
            row = self.env.cr.fetchone() or (False, False)
            return {"ee_vat": bool(row[0]), "ee_payroll": bool(row[1])}
        except Exception:
            return {"ee_vat": False, "ee_payroll": False}

    def _l10n_bg_push_registration(self):
        """Излъчва ``{vat, name, ee_vat, ee_payroll}`` на канал
        ``l10n-bulgaria`` per BG фирма. Викан от publisher cron override-а,
        собствения скрит cron и инсталацията. Напълно тих.
        """
        try:
            if not self._l10n_bg_registration_enabled():
                return False
            companies = self or self.search([("is_l10n_bg_record", "=", True)])
            ee = self._l10n_bg_ee_modules()
            bus = self.env["bus.bus"].sudo()
            # Soft-link: ако license_server е инсталиран (моделът съществува),
            # записваме регистрацията локално за списъка „кой е инсталирал".
            Reg = (
                self.env["l10n.bg.registration"].sudo()
                if "l10n.bg.registration" in self.env
                else None
            )
            dbname = self.env.cr.dbname
            for company in companies:
                try:
                    vat = (company.vat or "").replace(" ", "").upper()
                    if not vat:
                        continue
                    payload = {
                        "vat": vat,
                        "name": company.name or "",
                        "ee_vat": ee["ee_vat"],
                        "ee_payroll": ee["ee_payroll"],
                    }
                    bus._sendone(
                        L10N_BG_REGISTER_CHANNEL, L10N_BG_REGISTER_TYPE, payload
                    )
                    if Reg is not None:
                        Reg._record_push({**payload, "instance": dbname})
                except Exception:
                    continue
        except Exception:
            return False
        return True
