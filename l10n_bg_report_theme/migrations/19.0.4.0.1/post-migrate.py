def migrate(cr, version):
    """Add a custom_scss_path column if it doesn't exist"""
    cr.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name='res_company'
        AND column_name='custom_scss_path'
    """)
    if not cr.fetchone():
        cr.execute("""
            ALTER TABLE res_company
            ADD COLUMN custom_scss_path VARCHAR
        """)
