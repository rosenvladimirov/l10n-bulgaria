# -*- coding: utf-8 -*-
"""19.0.1.1.0 — новите знание-skills за ДДС и локализацията.

`post_init_hook` тръгва само при инсталация, не при `-u`: без тази миграция
новите skills остават `draft` и никога не съвпадат в семантичния път.
Токенизира само нетокенизираните skills на модула и само ако има фирма с
Qdrant — иначе ги оставя за ръчна токенизация, както hook-ът.
"""
import logging

from odoo import SUPERUSER_ID, api

from odoo.addons.l10n_bg_ai_accounting_glue.hooks import _module_skills, _qdrant_configured

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    skills = _module_skills(env).filtered(lambda s: s.state != "indexed")
    if not skills:
        return
    if not _qdrant_configured(env):
        _logger.info(
            "l10n_bg_ai_accounting_glue 19.0.1.1.0: %s skill(s) остават draft — "
            "Qdrant не е конфигуриран", len(skills))
        return
    skills.action_tokenize_description()
    _logger.info("l10n_bg_ai_accounting_glue 19.0.1.1.0: токенизирани %s skill(s)", len(skills))
