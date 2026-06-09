# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Odoo 20/master back-compat shim.

Master removed ``ir.config_parameter.get_param``/``set_param`` in favour of
``_get(key, type_)`` / ``set_str``/``set_bool``/… . The Bulgarian localization
calls the old API in ~100 places; rather than churn every call site on the
20.0 branch we re-expose the historical signatures here, on the foundational
``l10n_bg_config`` model that everything depends on.
"""
from odoo import models


class IrConfigParameter(models.Model):
    _inherit = "ir.config_parameter"

    def get_param(self, key, default=False):
        value = self._get(key, "str")[0]
        return default if value is None else value

    def set_param(self, key, value):
        return self.set_str(key, "" if value is None else str(value))
