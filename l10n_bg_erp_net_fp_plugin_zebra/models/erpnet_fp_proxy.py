# -*- coding: utf-8 -*-
"""Reroute _PUSH_CONFIG_SOURCES for zebra plug-in."""

from odoo import models


class _ErpNetFpProxyZebraRouting(models.Model):
    _inherit = 'erpnet.fp.proxy'

    @property
    def _PUSH_CONFIG_SOURCES(self):
        sources = dict(super()._PUSH_CONFIG_SOURCES)
        sources['readers'] = ('zebra.reader',
                              'l10n_bg_erp_net_fp_plugin_zebra')
        return sources
