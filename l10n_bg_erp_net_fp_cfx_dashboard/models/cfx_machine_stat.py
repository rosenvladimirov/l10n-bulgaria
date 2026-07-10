# Copyright 2026 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Live-refresh emit при нов cfx.machine.stat ред.

Тук се калемим (без да пипаме базовия CFX плъгин) към cfx.machine.stat и
добавяме live.refresh.mixin. При всеки create излъчваме ДВА сигнала:

1. Broadcast на bus канал ``cfx_dashboard`` — стига до ВСЕКИ отворен CFX
   монитор, независимо кой е акаунтът. Нужно е, защото CFX ingest върви
   през HMAC-подписан контролер (sudo/API потребител), а операторът, който
   гледа дашборда, е друг потребител — per-user каналите не биха го стигнали.
   Клиентската услуга cfx_dashboard_bus.js го превръща в env.bus
   "CFX_STAT_NEW", а мостът дебоунсва + презарежда данните на дашборда.

2. Per-user ``l10n_bg_live_refresh`` ``list`` сигнал — освежава отворените
   cfx.machine.stat *списъчни* изгледи на текущия потребител (бонус, ползва
   съществуващия engine; за дашборда се разчита на broadcast-а по-горе).
"""
from odoo import api, models

# Broadcast bus канал за CFX мониторите. Клиентът се абонира със същия низ.
CFX_DASHBOARD_CHANNEL = "cfx_dashboard"


class CfxMachineStat(models.Model):
    _name = "cfx.machine.stat"
    _inherit = ["cfx.machine.stat", "live.refresh.mixin"]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # 1) broadcast към всички отворени монитори
        self.env["bus.bus"]._sendone(
            CFX_DASHBOARD_CHANNEL,
            "cfx.machine.stat/new",
            {"model": self._name, "count": len(records)},
        )
        # 2) per-user list сигнал за живи списъчни изгледи
        records._live_refresh_notify(mode="list")
        return records
