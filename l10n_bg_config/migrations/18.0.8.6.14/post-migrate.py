import logging

_logger = logging.getLogger(__name__)

# Сметка 491 „Доверители" идва от ядрения `l10n_bg` с `reconcile = False`
# (`l10n_bg/data/template/account.account-bg.csv`). Докато не е сдвоима, по нея
# не може да се затваря разчет — а точно това ѝ е предназначението: пари, които
# трето лице държи от наше име (куриер при наложен платеж, fulfillment партньор,
# посредник) и после превежда. Без сдвояване салдото само расте и никой не може
# да каже кой превод коя пратка покрива.
#
# Темплейтът вече го дефинира като сдвоима, но темплейтът важи за НОВИ
# инсталации. Заварените бази се пипат само оттук — презареждането на
# сметкоплана НЕ е опция (то трие сметки).
#
# Пипаме само сметки, които още са `reconcile = False`: ако някой вече го е
# вдигнал ръчно, няма какво да правим.


def migrate(cr, version):
    if not version:
        return

    # Сметките от темплейт носят xmlid `<company_id>_l10n_bg_491` в модул
    # `account`. Търсим по суфикс, за да хванем всички фирми в базата.
    cr.execute(
        """
        UPDATE account_account
        SET reconcile = TRUE
        WHERE reconcile = FALSE
          AND id IN (
              SELECT res_id FROM ir_model_data
              WHERE model = 'account.account'
                AND name LIKE '%%\\_l10n\\_bg\\_491'
          )
        """
    )
    _logger.info(
        "l10n_bg_config 8.6.14: 491 Доверители → reconcile=True за %d сметка(и)",
        cr.rowcount,
    )
