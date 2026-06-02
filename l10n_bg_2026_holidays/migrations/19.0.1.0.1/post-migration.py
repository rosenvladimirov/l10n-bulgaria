def migrate(cr, version):
    """Върни noupdate=1 за записите на модула след презареждането на данните —
    защити празниците от случайно презаписване занапред (клиентски редакции)."""
    cr.execute(
        "UPDATE ir_model_data SET noupdate = TRUE WHERE module = %s",
        ("l10n_bg_2026_holidays",),
    )
