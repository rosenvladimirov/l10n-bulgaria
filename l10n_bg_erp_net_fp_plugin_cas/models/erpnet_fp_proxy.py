# -*- coding: utf-8 -*-
"""Reroute _PUSH_CONFIG_SOURCES for cas plug-in."""

from odoo import models


class _ErpNetFpProxyCasRouting(models.Model):
    _inherit = 'erpnet.fp.proxy'

    @property
    def _PUSH_CONFIG_SOURCES(self):
        sources = dict(super()._PUSH_CONFIG_SOURCES)
        sources['scales'] = ('cas.scale',
                              'l10n_bg_erp_net_fp_plugin_cas')
        return sources
