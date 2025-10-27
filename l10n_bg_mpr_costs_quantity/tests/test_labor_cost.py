# -*- coding: utf-8 -*-
"""
Unit Tests for Manufacturing Labor Cost Module

Place this file in: tests/test_labor_cost.py
Don't forget to add __init__.py in tests/ folder with:
    from . import test_labor_cost
"""

from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install', 'labor_cost')
class TestLaborCost(TransactionCase):

    def setUp(self):
        super().setUp()

        # Create test workcenter
        self.workcenter = self.env['mrp.workcenter'].create({
            'name': 'Test Workcenter',
            'costs_hour': 50.0,  # 50 BGN per hour
            'labor_cost_method': 'workcenter',  # Start with workcenter method
        })

        # Create test employee
        self.employee = self.env['hr.employee'].create({
            'name': 'Test Worker',
            'hourly_cost': 30.0,  # 30 BGN per hour
        })

        # Create test product
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'type': 'product',
            'cost_method': 'average',
            'standard_price': 100.0,
        })

        # Create BOM
        self.bom = self.env['mrp.bom'].create({
            'product_id': self.product.id,
            'product_tmpl_id': self.product.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
        })

        # Add operation to BOM
        self.operation = self.env['mrp.bom.line'].create({
            'bom_id': self.bom.id,
            'workcenter_id': self.workcenter.id,
            'name': 'Test Operation',
            'time_cycle': 60,  # 60 minutes
        })

    def test_01_workcenter_cost_method(self):
        """Test that workcenter cost method uses workcenter.costs_hour"""

        # Create MO
        mo = self.env['mrp.production'].create({
            'product_id': self.product.id,
            'bom_id': self.bom.id,
            'product_qty': 10,
        })
        mo.action_confirm()

        # Get workorder
        workorder = mo.workorder_ids[0]
        workorder.employee_id = self.employee

        # Simulate 2 hours of work
        self.env['mrp.workcenter.productivity'].create({
            'workorder_id': workorder.id,
            'date_start': '2025-01-01 08:00:00',
            'date_end': '2025-01-01 10:00:00',
            'duration': 120,  # 120 minutes
        })

        # Calculate cost
        cost = workorder._cal_cost()

        # Should use workcenter.costs_hour (50 BGN/hour) × 2 hours = 100 BGN
        self.assertEqual(cost, 100.0,
                         f"Expected 100.0 but got {cost}. Should use workcenter rate.")

    def test_02_employee_cost_method(self):
        """Test that employee cost method uses employee.hourly_cost"""

        # Change workcenter to employee method
        self.workcenter.labor_cost_method = 'employee'

        # Create MO
        mo = self.env['mrp.production'].create({
            'product_id': self.product.id,
            'bom_id': self.bom.id,
            'product_qty': 10,
        })
        mo.action_confirm()

        # Get workorder
        workorder = mo.workorder_ids[0]
        workorder.employee_id = self.employee

        # Simulate 2 hours of work
        self.env['mrp.workcenter.productivity'].create({
            'workorder_id': workorder.id,
            'date_start': '2025-01-01 08:00:00',
            'date_end': '2025-01-01 10:00:00',
            'duration': 120,  # 120 minutes
        })

        # Calculate cost
        cost = workorder._cal_cost()

        # Should use employee.hourly_cost (30 BGN/hour) × 2 hours = 60 BGN
        self.assertEqual(cost, 60.0,
                         f"Expected 60.0 but got {cost}. Should use employee rate.")

    def test_03_total_labor_cost_computation(self):
        """Test that MO computes total_labor_cost correctly"""

        self.workcenter.labor_cost_method = 'employee'

        # Create MO
        mo = self.env['mrp.production'].create({
            'product_id': self.product.id,
            'bom_id': self.bom.id,
            'product_qty': 100,
        })
        mo.action_confirm()

        # Simulate work
        workorder = mo.workorder_ids[0]
        workorder.employee_id = self.employee

        self.env['mrp.workcenter.productivity'].create({
            'workorder_id': workorder.id,
            'date_start': '2025-01-01 08:00:00',
            'date_end': '2025-01-01 12:00:00',
            'duration': 240,  # 4 hours
        })

        # Trigger compute
        mo._compute_total_labor_cost()

        # Expected: 4 hours × 30 BGN/hour = 120 BGN
        self.assertEqual(mo.total_labor_cost, 120.0,
                         f"Expected 120.0 but got {mo.total_labor_cost}")

    def test_04_labor_cost_per_unit(self):
        """Test labor cost per unit calculation"""

        self.workcenter.labor_cost_method = 'employee'

        # Create MO
        mo = self.env['mrp.production'].create({
            'product_id': self.product.id,
            'bom_id': self.bom.id,
            'product_qty': 50,
        })
        mo.action_confirm()

        # Simulate work
        workorder = mo.workorder_ids[0]
        workorder.employee_id = self.employee

        self.env['mrp.workcenter.productivity'].create({
            'workorder_id': workorder.id,
            'date_start': '2025-01-01 08:00:00',
            'date_end': '2025-01-01 13:00:00',
            'duration': 300,  # 5 hours
        })

        # Mark some as produced
        mo.qty_producing = 50
        mo.qty_produced = 50

        # Trigger compute
        mo._compute_total_labor_cost()
        mo._compute_labor_cost_per_unit()

        # Expected: (5 hours × 30 BGN) / 50 units = 150 / 50 = 3 BGN/unit
        self.assertEqual(mo.labor_cost_per_unit, 3.0,
                         f"Expected 3.0 but got {mo.labor_cost_per_unit}")

    def test_05_svl_creation_on_done(self):
        """Test that new SVL records are created (not modified)"""

        self.workcenter.labor_cost_method = 'employee'

        # Setup company accounts
        expense_account = self.env['account.account'].create({
            'name': 'Labor Expense',
            'code': '602',
            'account_type': 'expense',
        })
        wip_account = self.env['account.account'].create({
            'name': 'WIP',
            'code': '331',
            'account_type': 'asset_current',
        })

        self.env.company.write({
            'labor_accounting_enabled': True,
            'labor_expense_account_id': expense_account.id,
            'wip_account_id': wip_account.id,
        })

        # Create MO
        mo = self.env['mrp.production'].create({
            'product_id': self.product.id,
            'bom_id': self.bom.id,
            'product_qty': 10,
        })
        mo.action_confirm()

        # Simulate work
        workorder = mo.workorder_ids[0]
        workorder.employee_id = self.employee

        self.env['mrp.workcenter.productivity'].create({
            'workorder_id': workorder.id,
            'date_start': '2025-01-01 08:00:00',
            'date_end': '2025-01-01 10:00:00',
            'duration': 120,
        })

        # Count SVL before
        svl_count_before = self.env['stock.valuation.layer'].search_count([
            ('product_id', '=', self.product.id)
        ])

        # Complete production
        mo.qty_producing = 10
        mo.button_mark_done()

        # Count SVL after
        svl_count_after = self.env['stock.valuation.layer'].search_count([
            ('product_id', '=', self.product.id)
        ])

        # Should have created NEW SVL records
        self.assertGreater(svl_count_after, svl_count_before,
                           "New SVL records should be created, not modified")

    def test_06_journal_entry_creation(self):
        """Test that journal entry is created when enabled"""

        # Setup accounts
        expense_account = self.env['account.account'].create({
            'name': 'Labor Expense',
            'code': '602',
            'account_type': 'expense',
        })
        wip_account = self.env['account.account'].create({
            'name': 'WIP',
            'code': '331',
            'account_type': 'asset_current',
        })

        self.env.company.write({
            'labor_accounting_enabled': True,
            'labor_expense_account_id': expense_account.id,
            'wip_account_id': wip_account.id,
        })

        self.workcenter.labor_cost_method = 'employee'

        # Create and complete MO
        mo = self.env['mrp.production'].create({
            'product_id': self.product.id,
            'bom_id': self.bom.id,
            'product_qty': 10,
        })
        mo.action_confirm()

        workorder = mo.workorder_ids[0]
        workorder.employee_id = self.employee

        self.env['mrp.workcenter.productivity'].create({
            'workorder_id': workorder.id,
            'date_start': '2025-01-01 08:00:00',
            'date_end': '2025-01-01 10:00:00',
            'duration': 120,
        })

        mo.qty_producing = 10
        mo.button_mark_done()

        # Check journal entry created
        self.assertTrue(mo.labor_journal_entry_id,
                        "Journal entry should be created")
        self.assertEqual(mo.labor_journal_entry_id.state, 'posted',
                         "Journal entry should be posted")

        # Check amounts
        debit_lines = mo.labor_journal_entry_id.line_ids.filtered(lambda l: l.debit > 0)
        credit_lines = mo.labor_journal_entry_id.line_ids.filtered(lambda l: l.credit > 0)

        self.assertEqual(len(debit_lines), 1, "Should have 1 debit line")
        self.assertEqual(len(credit_lines), 1, "Should have 1 credit line")

        # Expected: 2 hours × 30 BGN = 60 BGN
        self.assertEqual(debit_lines[0].debit, 60.0)
        self.assertEqual(credit_lines[0].credit, 60.0)

    def test_07_no_journal_entry_when_disabled(self):
        """Test that no journal entry created when disabled"""

        self.env.company.labor_accounting_enabled = False

        # Create and complete MO
        mo = self.env['mrp.production'].create({
            'product_id': self.product.id,
            'bom_id': self.bom.id,
            'product_qty': 10,
        })
        mo.action_confirm()

        workorder = mo.workorder_ids[0]
        self.env['mrp.workcenter.productivity'].create({
            'workorder_id': workorder.id,
            'date_start': '2025-01-01 08:00:00',
            'date_end': '2025-01-01 10:00:00',
            'duration': 120,
        })

        mo.qty_producing = 10
        mo.button_mark_done()

        # Check no journal entry
        self.assertFalse(mo.labor_journal_entry_id,
                         "No journal entry should be created when disabled")

    def test_08_error_when_accounts_not_configured(self):
        """Test that error raised when accounts not configured"""

        self.env.company.write({
            'labor_accounting_enabled': True,
            'labor_expense_account_id': False,
            'wip_account_id': False,
        })

        # Create and try to complete MO
        mo = self.env['mrp.production'].create({
            'product_id': self.product.id,
            'bom_id': self.bom.id,
            'product_qty': 10,
        })
        mo.action_confirm()

        workorder = mo.workorder_ids[0]
        self.env['mrp.workcenter.productivity'].create({
            'workorder_id': workorder.id,
            'date_start': '2025-01-01 08:00:00',
            'date_end': '2025-01-01 10:00:00',
            'duration': 120,
        })

        mo.qty_producing = 10

        # Should raise error
        with self.assertRaises(UserError):
            mo.button_mark_done()

# To run tests:
# odoo-bin -c odoo.conf -d your_db --test-tags labor_cost --stop-after-init
