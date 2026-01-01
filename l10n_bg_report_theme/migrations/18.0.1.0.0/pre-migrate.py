# -*- coding: utf-8 -*-
import logging
import os

_logger = logging.getLogger(__name__)

OLD_MODULE_NAME = 'report_theme_sections'

NEW_MODULE_NAME = os.path.basename(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(__file__)
        )
    )
)


def migrate(cr, version):
    """
    Migrate module data from OLD to NEW name, then delete the old module record (Odoo 19)
    """
    _logger.info(f'Migration running from module directory: {NEW_MODULE_NAME}')

    if OLD_MODULE_NAME == NEW_MODULE_NAME:
        _logger.warning(f'Old and new module names are the same ({OLD_MODULE_NAME}). Migration skipped.')
        return

    # Проверка дали старият модул съществува
    cr.execute("""
               SELECT id, name, state
               FROM ir_module_module
               WHERE name = %s
               """, (OLD_MODULE_NAME,))

    old_module = cr.fetchone()

    if not old_module:
        _logger.warning(f'Module {OLD_MODULE_NAME} not found in database. Migration skipped.')
        return

    old_module_id = old_module[0]
    _logger.info(f'Found module {OLD_MODULE_NAME} (ID: {old_module_id}, State: {old_module[2]})')
    _logger.info(f'Migrating data: {OLD_MODULE_NAME} → {NEW_MODULE_NAME}')

    # 1. Обнови external IDs
    cr.execute("SELECT COUNT(*) FROM ir_model_data WHERE module = %s", (OLD_MODULE_NAME,))
    count = cr.fetchone()[0]

    if count > 0:
        cr.execute("""
                   UPDATE ir_model_data
                   SET module = %s
                   WHERE module = %s
                   """, (NEW_MODULE_NAME, OLD_MODULE_NAME))
        _logger.info(f'✓ Updated ir_model_data: {cr.rowcount} record(s)')
    else:
        _logger.info(f'✓ No external IDs to update')

    # 2. Обнови зависимости в други модули
    cr.execute("SELECT COUNT(*) FROM ir_module_module_dependency WHERE name = %s", (OLD_MODULE_NAME,))
    count = cr.fetchone()[0]

    if count > 0:
        cr.execute("""
                   UPDATE ir_module_module_dependency
                   SET name = %s
                   WHERE name = %s
                   """, (NEW_MODULE_NAME, OLD_MODULE_NAME))
        _logger.info(f'✓ Updated dependencies: {cr.rowcount} record(s)')
    else:
        _logger.info(f'✓ No dependencies to update')

    # 3. Обнови constraints - трябва да остане старото ID докато не се изтрие модулът
    # Constraints се обновяват автоматично след като новият модул се зареди
    _logger.info(f'✓ Constraints will be updated when new module loads')

    # 4. ИЗТРИЙ стария модул запис
    cr.execute("""
               DELETE
               FROM ir_module_module
               WHERE id = %s
               """, (old_module_id,))
    _logger.info(f'✓ Deleted old module record: {OLD_MODULE_NAME} (ID: {old_module_id})')

    _logger.info(f'✓ Migration completed. Odoo will now load the new module: {NEW_MODULE_NAME}')
