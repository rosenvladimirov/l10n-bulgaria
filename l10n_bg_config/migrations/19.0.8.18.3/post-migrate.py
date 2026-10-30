#  Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Черният списък (`blacklist.enc` + `l10n_bg.blacklist_key`) е махнат.

Лицензът на OPL-1 модулите се спира и пуска само с подписан отговор на
лицензния сървър в `l10n_bg_license_client` (ADR
l10n-bg-license-key-registration/0002). Без ключа заварен клиент 19.0.1.0.x
не пише и не трие файла `blacklist.enc` (в общ код — за всички бази).
"""


def migrate(cr, version):
    cr.execute("DELETE FROM ir_config_parameter WHERE key = 'l10n_bg.blacklist_key'")
