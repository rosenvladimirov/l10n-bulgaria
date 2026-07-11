# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging
import re
import textwrap

from odoo import api, models

_logger = logging.getLogger(__name__)

# Language marker: full Odoo lang codes (bg_BG, en_US, de_DE, ...)
_LANG_BLOCK = re.compile(r"\[([a-z]{2}_[A-Z]{2})\](.*?)\[/\1\]", re.DOTALL)

# Unmarked legacy text is treated as en_US only.
# Odoo 20 core `_explanation` strings are plain English without markers —
# they leak through to en_US users and are skipped for everyone else.
_UNMARKED_DEFAULT_LANG = "en_US"


def _extract_lang(text, lang):
    """Return the language-filtered portion of an ``_explanation`` string.

    Rules (matching the Skills concept in odoo_explanation_backport_architecture):

    * ``[xx_YY]...[/xx_YY]`` blocks — included only when ``xx_YY == lang``.
    * Unmarked text (no lang blocks) — treated as ``en_US``.  Included only
      when ``lang == "en_US"``; skipped otherwise.
    * Mixed text (some unmarked + some marked) — only marker-matched blocks
      count, unmarked prose is ignored when markers exist.
    """
    if not text:
        return None
    blocks = _LANG_BLOCK.findall(text)
    if not blocks:
        if lang == _UNMARKED_DEFAULT_LANG:
            return text.strip()
        return None
    matched = [body.strip() for code, body in blocks if code == lang]
    return "\n\n".join(matched) if matched else None


class IrModel(models.Model):
    _inherit = "ir.model"

    @api.model
    def get_ai_explanations(self, model_names=None, lang=None):
        """Return per-model ``_explanation`` text, filtered by language.

        Cross-version implementation: works on 16/17/18/19 via the
        ``models.Model._explanation`` monkey patch done in ``__init__.py``,
        and on 20.0 via the native attribute.

        :param list model_names: optional model name filter; when falsy,
            every model in the ai.view.registry with ``active=True`` is
            returned.
        :param str lang: Odoo language code (e.g. ``"bg_BG"``, ``"en_US"``).
            Defaults to ``self.env.lang`` or ``"en_US"``.
        :return: ``{model_name: text}`` — only models with a non-empty
            language-matched explanation are included.
        """
        lang = lang or self.env.lang or _UNMARKED_DEFAULT_LANG

        # Whitelist: active tokenizer registry entries.  Models absent from the
        # registry intentionally do not leak AI context — this mirrors the
        # ai_tokenizer's own access rules (tokenized ⇔ AI-exposed).
        tokenizer_reg = self.env["ai.view.registry"].sudo()
        whitelist = set(
            tokenizer_reg.search([("active", "=", True)]).mapped("model_id.model")
        )
        if model_names:
            whitelist &= set(model_names)

        result = {}
        for name in whitelist:
            model = self.env.get(name)
            if model is None:
                continue
            parts = []
            # MRO walk identical in spirit to Odoo 20 `_reflect_model_params`:
            # general → specific, concatenate each explicit `_explanation`
            # that belongs to the target model (mixins with different `_name`
            # contribute nothing).
            for base in reversed(type(model).mro()):
                raw = base.__dict__.get("_explanation")
                if not raw:
                    continue
                if getattr(base, "_name", None) != name:
                    continue
                extracted = _extract_lang(textwrap.dedent(raw).strip(), lang)
                if extracted:
                    parts.append(extracted)
            if parts:
                result[name] = "\n\n".join(parts)
        return result
