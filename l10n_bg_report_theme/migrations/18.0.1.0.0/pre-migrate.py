# -*- coding: utf-8 -*-
import logging
import os

_logger = logging.getLogger(__name__)

OLD_MODULE_NAME = 'report_theme_sections'

# Вземи новото име от пътя на файла
NEW_MODULE_NAME = os.path.basename(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(__file__)
        )
    )
)


def migrate(cr, version):
    """
    Rename the module from report_theme_sections to the new module name (Odoo 18)
    """
    _logger.info(f'Migration running from module directory: {NEW_MODULE_NAME}')

    # Проверка дали старото и новото име са еднакви
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

    _logger.info(f'Found module {OLD_MODULE_NAME} (ID: {old_module[0]}, State: {old_module[2]})')

    # Проверка дали новият модул вече съществува
    cr.execute("""
               SELECT id, name
               FROM ir_module_module
               WHERE name = %s
               """, (NEW_MODULE_NAME,))

    new_module = cr.fetchone()

    if new_module:
        _logger.error(
            f'Module {NEW_MODULE_NAME} already exists (ID: {new_module[0]}). Cannot rename. Migration aborted.')
        return

    # Започни преименуване
    _logger.info(f'Starting module rename: {OLD_MODULE_NAME} → {NEW_MODULE_NAME}')

    # 1. Обнови името в ir_module_module
    cr.execute("""
               UPDATE ir_module_module
               SET name = %s
               WHERE name = %s
               """, (NEW_MODULE_NAME, OLD_MODULE_NAME))
    _logger.info(f'✓ Updated ir_module_module: {cr.rowcount} record(s)')

    # 2. Обнови external IDs (ir_model_data)
    cr.execute("""
               UPDATE ir_model_data
               SET module = %s
               WHERE module = %s
               """, (NEW_MODULE_NAME, OLD_MODULE_NAME))
    _logger.info(f'✓ Updated ir_model_data: {cr.rowcount} record(s)')

    # 3. Обнови зависимости в други модули
    cr.execute("""
               UPDATE ir_module_module_dependency
               SET name = %s
               WHERE name = %s
               """, (NEW_MODULE_NAME, OLD_MODULE_NAME))
    _logger.info(f'✓ Updated dependencies: {cr.rowcount} record(s)')

    # 4. Обнови constraints (ако има такава таблица в Odoo 18)
    cr.execute("""
               SELECT EXISTS (SELECT
                              FROM information_schema.tables
                              WHERE table_name = 'ir_model_constraint')
               """)
    if cr.fetchone()[0]:
        cr.execute("""
                   UPDATE ir_model_constraint
                   SET module = %s
                   WHERE module = %s
                   """, (NEW_MODULE_NAME, OLD_MODULE_NAME))
        _logger.info(f'✓ Updated constraints: {cr.rowcount} record(s)')

    # 5. Обнови automated actions (ir_cron) ако има записи от модула
    cr.execute("""
               SELECT EXISTS (SELECT
                              FROM information_schema.tables
                              WHERE table_name = 'ir_cron')
               """)
    if cr.fetchone()[0]:
        # Обнови external IDs вече ги обновихме, но проверяваме за директни референции
        _logger.info(f'✓ Automated actions will be updated via external IDs')

    _logger.info(f'✓ Module rename completed successfully: {OLD_MODULE_NAME} → {NEW_MODULE_NAME}')
