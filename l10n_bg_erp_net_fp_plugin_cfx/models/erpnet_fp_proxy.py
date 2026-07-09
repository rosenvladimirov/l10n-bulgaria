# Copyright 2026 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Регистрация на CFX като push_config източник + разширения на
device/config-template kind selection-ите (reachable-via-inherit
начина: selection_add).
"""

from odoo import fields, models


class ErpNetFpProxyCfxRouting(models.Model):
    _inherit = 'erpnet.fp.proxy'

    @property
    def _PUSH_CONFIG_SOURCES(self):
        # CFX секцията се генерира от cfx.endpoint.get_config_payload();
        # action_push_config_all я включва автоматично.
        sources = dict(super()._PUSH_CONFIG_SOURCES)
        sources['cfx'] = ('cfx.endpoint', 'l10n_bg_erp_net_fp_plugin_cfx')
        return sources


class ErpNetFpProxyDeviceCfx(models.Model):
    _inherit = 'erpnet.fp.proxy.device'

    # Добавя 'cfx' към _KIND_LABELS на fleet device-а. При uninstall на
    # модула cfx device записите се трият (cascade) — required поле.
    kind = fields.Selection(
        selection_add=[('cfx', 'CFX machine')],
        ondelete={'cfx': 'cascade'},
    )


class ErpNetFpProxyConfigTemplateCfx(models.Model):
    _inherit = 'erpnet.fp.proxy.config.template'

    # Добавя 'cfx' към _KIND_SELECTION на config-template-а. При
    # uninstall падаме към default kind (mqtt).
    kind = fields.Selection(
        selection_add=[('cfx', 'CFX')],
        ondelete={'cfx': 'set default'},
    )
