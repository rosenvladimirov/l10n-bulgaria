# -*- coding: utf-8 -*-
"""Reroute _PUSH_CONFIG_SOURCES — Datecs plugin owns printers + pinpads
kinds (replacing default model names които може да не съществуват).
"""

from odoo import models


class _ErpNetFpProxyDatecsRouting(models.Model):
    _inherit = 'erpnet.fp.proxy'

    @property
    def _PUSH_CONFIG_SOURCES(self):
        sources = dict(super()._PUSH_CONFIG_SOURCES)
        sources['printers'] = ('datecs.printer',
                                'l10n_bg_erp_net_fp_plugin_datecs')
        sources['pinpads'] = ('datecs.pinpad',
                               'l10n_bg_erp_net_fp_plugin_datecs')
        return sources
