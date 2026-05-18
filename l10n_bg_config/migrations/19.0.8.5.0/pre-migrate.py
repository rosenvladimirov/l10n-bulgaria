# Pre-migrate за upgrade към l10n_bg_config 19.0.8.5.0.
#
# Адресира двата блокера при upgrade от <8.4.1-seed-нати бази:
#
# Bug #1 — res.company.l10n_bg_kid_codes (Char, въведено в 8.4.3) без
#   migration → core res_company._compute_address SELECT-ва липсващата
#   колона при upgrade registry-load преди модула. Idempotent
#   schema-only guard (без данни, без счетоводна логика).
#
# Bug #2 — смяна на КИД seed механиката в 8.4.1 (commit 5ca9927):
#   per-company @template → plain data/ CSV. Бази инсталирани на <8.4.1
#   имат 21-те `l10n.bg.kid` реда с xmlid-и `account.<cid>_kid_2025_<X>`
#   (template-prefix). 8.5.0 CSV очаква `l10n_bg_config.kid_2025_<X>`
#   → не match-ва → CREATE → @api.constrains _check_unique_code гърми
#   „КИД code 'X' already exists". Fix (одобрен от Rosen 2026-05-18,
#   FK-safe — пази res_id, само релейбълва ir_model_data): remap-ва
#   старите xmlid-и към 8.5.0 схемата, така че CSV `load` да UPDATE-не
#   съществуващите редове вместо да дублира. Localization КИД таксономия
#   НЕ се трие/импровизира — само reattach на external id-тата.
#   NOT EXISTS guard → идемпотентно, без колизия ако вече е приложено.


def migrate(cr, version):
    if not version:
        # Fresh install — CSV-то само създава xmlid-ите коректно.
        return

    # ── Bug #1: defensive schema guard (idempotent) ──────────────────
    cr.execute(
        "ALTER TABLE res_company "
        "ADD COLUMN IF NOT EXISTS l10n_bg_kid_codes varchar"
    )

    # ── Bug #2: FK-safe remap на pre-8.4.1 КИД external id-та ─────────
    cr.execute(
        """
        UPDATE ir_model_data imd
           SET module = 'l10n_bg_config',
               name   = regexp_replace(imd.name, '^[0-9]+_kid_', 'kid_')
         WHERE imd.model  = 'l10n.bg.kid'
           AND imd.module = 'account'
           AND imd.name   ~ '^[0-9]+_kid_2025_[A-Z]$'
           AND NOT EXISTS (
               SELECT 1
                 FROM ir_model_data x
                WHERE x.module = 'l10n_bg_config'
                  AND x.name   = regexp_replace(imd.name,
                                                '^[0-9]+_kid_', 'kid_')
           )
        """
    )
