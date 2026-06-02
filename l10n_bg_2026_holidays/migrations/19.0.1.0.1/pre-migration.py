def migrate(cr, version):
    """Свали noupdate=0 за записите на този модул преди презареждане на
    данните, за да се обновят празниците при upgrade (коригирани дати/имена).
    След презареждането post-migration връща noupdate=1."""
    cr.execute(
        "UPDATE ir_model_data SET noupdate = FALSE WHERE module = %s",
        ("l10n_bg_2026_holidays",),
    )
