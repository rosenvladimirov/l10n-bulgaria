# -*- coding: utf-8 -*-
{
    "name": "Bulgaria AI Accounting Skills",
    "summary": (
        "General Bulgarian accounting / MRP AI skills (knowledge-only) "
        "for the l10n_bg_ai_pipeline skills engine."
    ),
    "version": "20.0.1.0.0",
    "development_status": "Alpha",
    "category": "Accounting/Localizations",
    "license": "OPL-1",
    "author": "Rosen Vladimirov",
    "website": (
        "https://github.com/rosenvladimirov/l10n-bulgaria/tree/19.0/"
        "l10n_bg_ai_accounting_glue"
    ),
    "depends": [
        # Базовият skills engine — общи знание-skills, без backing код, без EE.
        "l10n_bg_ai_pipeline",
        # sale/stock — за ai.view.registry на sale.order + stock.picking
        # (документите, които transit-COGS / phantom-qty skills таргетират). CE.
        "sale",
        "stock",
    ],
    "data": [
        "data/skills.xml",
        "data/view_registry.xml",
    ],
    # Токенизация структура: post_init индексира L1 description-ите на
    # знание-skills в Qdrant (ако е конфигуриран); uninstall ги изчиства.
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "installable": True,
    "application": False,
    "auto_install": False,
}
