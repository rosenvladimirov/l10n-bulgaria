# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
"""Миграция на заварените кодове при инсталация.

За всеки вариант без код:
  1. taric_code на шаблона (колоната от l10n_bg_tariff_code), ако има
     точно 10 цифри — истински TARIC10;
  2. иначе цифрите на hs_code на шаблона, ако са 8 или 10.

КН от името (^\\d{8}_) НЕ се записва автоматично — за него е уизардът
„Suggest CN from product name“, който показва предложенията и записва само
избраните (решение на Росен, 10.10.2026).

taric_code се чете със SQL: при ъпгрейд на l10n_bg_tariff_code този модул
се инсталира ПРЕДИ него и полето още не е в регистъра, но колоната е в
базата.
"""
import logging
from collections import defaultdict

from .models.commodity_code_utils import digits_candidate

_logger = logging.getLogger(__name__)


def _taric_codes_by_template(env):
    env.cr.execute(
        """
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'product_template' AND column_name = 'taric_code'
        """
    )
    if not env.cr.fetchone():
        return {}
    env.cr.execute(
        "SELECT id, taric_code FROM product_template WHERE taric_code IS NOT NULL"
    )
    return {tmpl_id: code for tmpl_id, code in env.cr.fetchall()}


def migrate_legacy_codes(env):
    """Попълва l10n_bg_commodity_code от заварените taric_code/hs_code.

    Ако taric_code (10 цифри) и hs_code (8/10 цифри) се разминават в първите
    8 цифри (различен КН8), НЕ се пише нищо: вариантът остава без код, в лога
    излиза WARNING със списъка, а в историята на шаблона — бележка за ревю.
    Връща броя попълнени варианти; списъкът с конфликтите е в
    ``migrate_legacy_codes.conflicts`` (за тестове и ръчна справка).
    """
    taric_by_tmpl = _taric_codes_by_template(env)
    products = env["product.product"].with_context(active_test=False).search(
        [("l10n_bg_commodity_code", "=", False)]
    )
    by_code = defaultdict(lambda: env["product.product"])
    conflicts = []  # (шаблон, taric_code, hs_code)
    conflict_templates = env["product.template"]
    for product in products:
        template = product.product_tmpl_id
        taric = digits_candidate(taric_by_tmpl.get(template.id))
        taric = taric if taric and len(taric) == 10 else False
        hs = digits_candidate(template.hs_code)
        if taric and hs and taric[:8] != hs[:8]:
            if template not in conflict_templates:
                conflict_templates |= template
                conflicts.append((template, taric, hs))
            continue
        code = taric or hs
        if code:
            by_code[code] |= product
    migrated = 0
    for code, variants in by_code.items():
        variants.write({"l10n_bg_commodity_code": code})
        migrated += len(variants)
    _logger.info(
        "l10n_bg_commodity_code: migrated %s variant(s) from legacy "
        "taric_code/hs_code (%s distinct codes)", migrated, len(by_code),
    )
    if conflicts:
        _logger.warning(
            "l10n_bg_commodity_code: %s product template(s) NOT migrated — "
            "taric_code and hs_code differ in the CN8 part, review manually:\n%s",
            len(conflicts),
            "\n".join(
                f"  product.template {t.id} [{t.default_code or ''}] {t.name}: "
                f"taric_code={taric} hs_code={hs}"
                for t, taric, hs in conflicts
            ),
        )
        for template, taric, hs in conflicts:
            # куката тече и при инсталация, и от post-migrate на тарифите —
            # една бележка на шаблон стига
            if any(taric in (m.body or "") and hs in (m.body or "")
                   for m in template.message_ids):
                continue
            template.message_post(
                body=env._(
                    "Commodity code not migrated: the legacy TARIC code %(taric)s "
                    "and HS code %(hs)s differ in the CN8 part. Set the code "
                    "manually after review.",
                    taric=taric, hs=hs,
                ),
                subtype_xmlid="mail.mt_note",
            )
    migrate_legacy_codes.conflicts = [
        (t.id, taric, hs) for t, taric, hs in conflicts
    ]
    return migrated


migrate_legacy_codes.conflicts = []


def post_init_hook(env):
    migrate_legacy_codes(env)
