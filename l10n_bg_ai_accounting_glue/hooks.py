# -*- coding: utf-8 -*-
"""Токенизация структура за знание-skills в този модул.

Самото съществуване на ai.skill запис НЕ е достатъчно — L1 description-ът
трябва да се embed-не в Qdrant (`action_tokenize_description`), за да е
matchable от pipeline-а (`match_for_vector`). Тук носим тази структура:
post_init индексира skills-ите при install, uninstall ги изчиства.
"""
import logging

_logger = logging.getLogger(__name__)

# XML id-тата на знание-skills, които този модул внася.
SKILL_XMLIDS = [
    "l10n_bg_ai_accounting_glue.skill_bg_erp_correction_safety",
    "l10n_bg_ai_accounting_glue.skill_bg_intercompany_transit_cogs",
    "l10n_bg_ai_accounting_glue.skill_bg_so_phantom_qty_delivered",
]
# ai.view.registry записи (form view-та на таргет документите).
REGISTRY_XMLIDS = [
    "l10n_bg_ai_accounting_glue.reg_sale_order",
    "l10n_bg_ai_accounting_glue.reg_stock_picking",
]


def _module_skills(env):
    skills = env["ai.skill"].browse()
    for xid in SKILL_XMLIDS:
        rec = env.ref(xid, raise_if_not_found=False)
        if rec:
            skills |= rec
    return skills


def _module_registries(env):
    regs = env["ai.view.registry"].browse()
    for xid in REGISTRY_XMLIDS:
        rec = env.ref(xid, raise_if_not_found=False)
        if rec:
            regs |= rec
    return regs


def _qdrant_configured(env):
    """Токенизацията иска Qdrant URL на поне една фирма
    (огледало на ai.view.registry._is_enabled)."""
    return bool(
        env["res.company"].sudo().search([("claude_qdrant_url", "!=", False)], limit=1)
    )


def post_init_hook(env):
    """Индексирай L1 description-ите след install — само ако Qdrant е
    конфигуриран; иначе skills остават `draft` за по-късна токенизация
    (ръчно от AI менюто или при настройка на Qdrant)."""
    # field_spec от form view-та (не иска Qdrant)
    regs = _module_registries(env)
    if regs:
        try:
            regs.action_parse_arch()
            _logger.info("l10n_bg_ai_accounting_glue: parsed %s registry view(s)", len(regs))
        except Exception:
            _logger.exception("l10n_bg_ai_accounting_glue: registry parse failed")
    skills = _module_skills(env)
    if not skills:
        _logger.warning("l10n_bg_ai_accounting_glue: няма намерени skills за токенизация")
        return
    if not _qdrant_configured(env):
        _logger.info(
            "l10n_bg_ai_accounting_glue: %s знание-skills остават draft — "
            "Qdrant не е конфигуриран; токенизирай при настройка на embedding.",
            len(skills),
        )
        return
    skills.action_tokenize_description()
    _logger.info("l10n_bg_ai_accounting_glue: токенизирани %s знание-skills", len(skills))


def uninstall_hook(env):
    """Изчисти Qdrant точките на skills при uninstall (без orphan вектори)."""
    skills = _module_skills(env)
    if skills:
        skills.action_purge_from_qdrant()
