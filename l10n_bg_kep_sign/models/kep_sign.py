# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Pluggable КЕП signing engine.

Базов интерфейс: `env['l10n.bg.kep.sign'].sign(content_bytes, company)` връща
detached PKCS7 (.p7s) bytes — server-side подписване. Кой backend се ползва се
определя от `company.l10n_bg_kep_sign_provider`. Glue модулите добавят метод
`_sign_<provider>(content, company)` и разширяват selection-а:
  - l10n_bg_kep_sign_proxy   → 'proxy'   (Odoo.ErpNet.FP, server-side)
  - l10n_bg_kep_sign_stampit → 'stampit' (browser-side LSManager — НЕ server)

StampIT е браузърен: server-side `sign()` за него хвърля грешка; той се ползва
през frontend action (виж glue модула).
"""
from odoo import _, api, models
from odoo.exceptions import UserError


class L10nBgKepSign(models.AbstractModel):
    _name = "l10n.bg.kep.sign"
    _description = "KEP Signing Engine (pluggable)"

    @api.model
    def sign(self, content_bytes, company=None):
        """Връща detached PKCS7 (.p7s) bytes за `content_bytes`.

        Делегира към `_sign_<provider>` от активния glue. Хвърля, ако няма
        конфигуриран/инсталиран server-side provider.
        """
        company = company or self.env.company
        provider = company.l10n_bg_kep_sign_provider
        if not provider or provider == "none":
            raise UserError(_(
                "No КЕП signing provider configured for company %s "
                "(Settings → Accounting → KEP Signing).") % company.display_name)
        method = getattr(self, "_sign_%s" % provider, None)
        if method is None:
            raise UserError(_(
                "КЕП provider '%(p)s' is not installed or is browser-side only "
                "(no server-side signing). Install the matching glue module."
            ) % {"p": provider})
        return method(content_bytes, company)

    # Glue модулите за browser-side провайдери (StampIT) добавят кода си тук.
    _KEP_BROWSER_ONLY = set()

    @api.model
    def is_server_side(self, company=None):
        """True ако активният provider може да подписва server-side."""
        company = company or self.env.company
        provider = company.l10n_bg_kep_sign_provider
        return bool(provider and provider != "none"
                    and provider not in self._KEP_BROWSER_ONLY
                    and getattr(self, "_sign_%s" % provider, None))
