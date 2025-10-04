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
    Rename the module from report_theme_sections to the new module name (Odoo 18)
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

    # Проверка дали новият модул вече съществува
    cr.execute("""
        SELECT id, name
        FROM ir_module_module
        WHERE name = %s
    """, (NEW_MODULE_NAME,))

    new_module = cr.fetchone()

    if new_module:
        _logger.error(f'Module {NEW_MODULE_NAME} already exists (ID: {new_module[0]}). Cannot rename. Migration aborted.')
        return

    _logger.info(f'Starting module rename: {OLD_MODULE_NAME} → {NEW_MODULE_NAME}')

    # 1. Обнови името в ir_module_module
    cr.execute("""
        UPDATE ir_module_module
        SET name = %s
        WHERE name = %s
        RETURNING id
    """, (NEW_MODULE_NAME, OLD_MODULE_NAME))

    new_module_id = cr.fetchone()[0]
    _logger.info(f'✓ Updated ir_module_module: module renamed (ID: {new_module_id})')

    # 2. Обнови external IDs
    cr.execute("""
        UPDATE ir_model_data
        SET module = %s
        WHERE module = %s
    """, (NEW_MODULE_NAME, OLD_MODULE_NAME))
    _logger.info(f'✓ Updated ir_model_data: {cr.rowcount} record(s)')

    # 3. Обнови зависимости
    cr.execute("""
        UPDATE ir_module_module_dependency
        SET name = %s
        WHERE name = %s
    """, (NEW_MODULE_NAME, OLD_MODULE_NAME))
    _logger.info(f'✓ Updated dependencies: {cr.rowcount} record(s)')

    # 4. Обнови constraints (колоната е 'module', не 'module_id')
    cr.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = 'ir_model_constraint'
            AND column_name = 'module'
        )
    """)

    if cr.fetchone()[0]:
        cr.execute("""
            UPDATE ir_model_constraint
            SET module = %s
            WHERE module = %s
        """, (new_module_id, old_module_id))
        _logger.info(f'✓ Updated constraints: {cr.rowcount} record(s)')

    _logger.info(f'✓ Module rename completed successfully: {OLD_MODULE_NAME} → {NEW_MODULE_NAME}')
