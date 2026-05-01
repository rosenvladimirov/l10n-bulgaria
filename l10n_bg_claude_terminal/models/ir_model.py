# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
import re
import textwrap

from odoo import api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

_LANG_BLOCK = re.compile(r"\[([a-z]{2}_[A-Z]{2})\](.*?)\[/\1\]", re.DOTALL)
_UNMARKED_DEFAULT_LANG = "en_US"


def _extract_lang(text, lang):
    """Language filter — same semantics as 18.0/19.0 ports."""
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
        """Cross-version `_explanation` reader — 16.0 variant.

        16.0 lacks the ``ai.view.registry`` model, so the whitelist
        mechanism from later ports cannot be used.  Callers must supply
        ``model_names`` explicitly — no auto-discovery.
        """
        lang = lang or self.env.lang or _UNMARKED_DEFAULT_LANG

        if not model_names:
            raise UserError(
                "On Odoo 16.0 `model_names` is required: "
                "ai.view.registry whitelist is not available on this "
                "version. Pass an explicit list of model names."
            )

        result = {}
        for name in model_names:
            model = self.env.get(name)
            if model is None:
                continue
            parts = []
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
