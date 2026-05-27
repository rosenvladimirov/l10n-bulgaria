# -*- coding: utf-8 -*-
"""Reroute _PUSH_CONFIG_SOURCES for honeywell plug-in."""

from odoo import models


class _ErpNetFpProxyHoneywellRouting(models.Model):
    _inherit = 'erpnet.fp.proxy'

    @property
    def _PUSH_CONFIG_SOURCES(self):
        sources = dict(super()._PUSH_CONFIG_SOURCES)
        sources['readers'] = ('honeywell.reader',
                              'l10n_bg_erp_net_fp_plugin_honeywell')
        return sources
