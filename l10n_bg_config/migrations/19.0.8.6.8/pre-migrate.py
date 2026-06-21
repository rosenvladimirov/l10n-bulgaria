import logging

_logger = logging.getLogger(__name__)

# Старото име на групата "Bulgarian VAT" в account.move.form беше
# `account_bg_vat`. От 8.x нататък config дефинира само `account_bg_vat_entry`
# (групата `account_bg_vat` е премахната). При in-place upgrade от стара
# версия съществуващите наследяващи view-та (напр. l10n_bg_tax_admin) още
# съдържат `//group[@id='account_bg_vat']` в arch_db. Когато config зареди
# новите си view-та, Odoo ревалидира децата ПРЕДИ те самите да се обновят и
# гръмва с "Element ... account_bg_vat ... cannot be located in parent view".
#
# Тази pre-migration скрабва старата референция в arch_db на ВСИЧКИ view-та,
# преди config да зареди новия си arch. Токенът `account_bg_vat'` е еднозначен
# (следван от единична кавичка, а не от `_`), затова `account_bg_vat_entry'`
# НЕ се засяга. arch_db е jsonb (преводим) → касто към text + replace покрива
# всички езикови ключове наведнъж; единичните кавички в JSON стойностите не се
# escape-ват, така че LIKE/REPLACE работят коректно.


def migrate(cr, version):
    if not version:
        return

    cr.execute(
        r"""
        UPDATE ir_ui_view
        SET arch_db = REPLACE(
                arch_db::text,
                'account_bg_vat''',
                'account_bg_vat_entry'''
            )::jsonb
        WHERE arch_db::text LIKE '%account_bg_vat''%'
        """
    )
    _logger.info(
        "l10n_bg_config 8.6.8 pre-migrate: scrubbed stale 'account_bg_vat' "
        "group ref in %d view(s)",
        cr.rowcount,
    )
