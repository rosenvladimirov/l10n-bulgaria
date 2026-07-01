from . import models


# ─── Миграция: пре-таг на barcode-rule xmlid-ите от l10n_bg_erp_net_fp ──
# Когато reader-ът се изважда изпод вече внедрен `l10n_bg_erp_net_fp`,
# barcode.rule view-то, target-ACL редовете и (при -u) техните
# ir_model_data редове сменят модула-собственик. Виж коментара в
# l10n_bg_erp_net_base/__init__.py за защо е pre_init (преди data load).
# На чист install (без стар _fp) UPDATE-ът match-ва 0 реда → no-op.
def _pre_init_migrate_from_fp(env):
    moved = (
        'view_barcode_rule_form_l10n_bg_route',
        'access_l10n_bg_barcode_rule_target_user',
        'access_l10n_bg_barcode_rule_target_manager',
        # ir.model запис на изнесения модел — иначе orphan при -u на _fp
        'model_l10n_bg_barcode_rule_target',
    )
    env.cr.execute(
        """
        UPDATE ir_model_data
           SET module = 'l10n_bg_erp_net_reader'
         WHERE module = 'l10n_bg_erp_net_fp'
           AND name IN %s
        """,
        (moved,),
    )
