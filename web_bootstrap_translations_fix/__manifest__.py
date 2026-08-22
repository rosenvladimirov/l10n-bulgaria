{
    "name": "Web Bootstrap Translations — Missing Catalogue Fix",
    "version": "19.0.1.0.0",
    "license": "AGPL-3",
    "category": "Technical",
    "author": "Rosen Vladimirov, Terraros Commerce Ltd.",
    "website": "https://github.com/OCA/l10n-bulgaria",
    "summary": "A bootstrap module without a translation for an active "
               "language must not break the web client boot.",
    "description": """
Web Bootstrap Translations — Missing Catalogue Fix
==================================================

``/web/webclient/bootstrap_translations`` walks every module whose manifest
declares ``bootstrap`` and loads ``<module>/i18n/<lang>.po``. The core code
guards against a missing file:

    f_name = file_path(f'{addon_name}/i18n/{lang}.po')
    if not f_name:
        continue

but ``file_path`` **raises** ``FileNotFoundError`` instead of returning a falsy
value, so that guard is dead code. One bootstrap module without a catalogue for
one active language and the whole endpoint fails — and the web client awaits it
during boot, so every session gets a blank page.

It bit this installation on 22.08.2026: ``api_doc`` is ``auto_install`` and
ships with no ``i18n`` directory at all, so it broke Greek and Bulgarian for
all users the moment a module upgrade pulled it in.

This module does not reimplement the endpoint. It replaces the ``file_path``
symbol **as imported by that controller** with a wrapper that returns ``None``
instead of raising — which makes the core author's own guard work as written.
Everything else keeps the original behaviour, including the exception for
callers outside this one controller.
""",
    "depends": ["web"],
    "installable": True,
    # Дефектът чупи ВСЯКА сесия, тъй че лекът не бива да чака някой да се сети
    # да го инсталира.
    "auto_install": True,
    "application": False,
}
