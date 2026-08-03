# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import models

# Заглушени префикси на proxy събития — низ, разделен със запетаи, напр.
# "cfx.,mqtt.". ПРАЗНО по подразбиране: заварените бази не променят
# поведението си, докато някой не зададе параметъра изрично.
TOAST_MUTE_PARAM = "l10n_bg_live_refresh.toast_mute_prefixes"


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        res = super().session_info()
        if self.env.user._is_internal():
            res["l10n_bg_live_refresh_toast_mute"] = \
                self._l10n_bg_live_refresh_toast_mute()
        return res

    def _l10n_bg_live_refresh_toast_mute(self):
        """Върни заглушените префикси като списък от низове.

        Машинните потоци (CFX, MQTT) вървят по СЪЩИЯ bus канал
        ``erpnet_fp_proxy_events`` като събитията за оператора, но с
        темпо от порядъка на десетки в секунда. Всяко тяхно събитие
        става toast, а тялото му е неразличимо (``proxy · device``),
        защото машинният payload няма нито едно от полетата, които
        toast-ът форматира. Тук се четат префиксите, които браузърът
        да пропуска — самите bus събития продължават да текат, така
        че дашбордите и Shop Floor не се засягат.
        """
        raw = self.env["ir.config_parameter"].sudo().get_param(
            TOAST_MUTE_PARAM, default="") or ""
        return [prefix.strip() for prefix in raw.split(",") if prefix.strip()]
