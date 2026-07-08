from . import controllers
from . import models


# ─── Миграция: пре-таг на транспортните xmlid-и от l10n_bg_erp_net_fp ──
# Когато ядрото се изважда изпод вече внедрен `l10n_bg_erp_net_fp`,
# малкото транспортни записи (response views + response ACL) сменят
# модула-собственик. Този hook тече ПРЕДИ base да зареди своите данни
# (base е зависимост → инсталира се пръв в същата транзакция), затова
# UPDATE-ва съществуващите ir_model_data редове вместо да създава
# дубликати. На чист install (без стар _fp — напр. PoliGroup) UPDATE-ът
# match-ва 0 реда → no-op. Идемпотентно (втори `-u` не match-ва нищо).
def _pre_init_migrate_from_fp(env):
    moved = (
        # ir.model записи на изнесените модели — пре-таг преди base да ги
        # reflect-не, за да не се orphan-нат при -u на стария _fp.
        'model_fiscal_printer_device',
        'model_fiscal_printer_status',
        'model_fiscal_printer_response',
        # response view/action/ACL (изнесени изцяло в base)
        'view_fiscal_printer_response_list',
        'view_fiscal_printer_response_form',
        'action_fiscal_printer_response',
        'access_fiscal_printer_response_user',
        'access_fiscal_printer_response_manager',
        # status-cleanup крон (преместен в base) — иначе на фискален
        # клиент остава стар _fp крон + нов base крон = два дубликата.
        'ir_cron_cleanup_printer_status_history',
    )
    env.cr.execute(
        """
        UPDATE ir_model_data
           SET module = 'l10n_bg_erp_net_base'
         WHERE module = 'l10n_bg_erp_net_fp'
           AND name IN %s
        """,
        (moved,),
    )
