from odoo.tests import TransactionCase


class TestBulgarianReportCustomer(TransactionCase):
    
    
    def setup(self):
        pass
    
    def test_custom_options_initializer(self):
        pass
    
    def test_build_query(self):
        pass
    
    def test_vat_book_export_files_to_zip(self):
        pass
    
    def test_vat_book_get_txt_files(self):
        pass
    
    def test_vat_book_get_selected_tax_types(self):
        pass
    
    def test_vat_book_get_txt_invoices(self):
        pass
    
    def test_vat_book_get_REGINFO_SALES(self):
        pass 
    
    def test_vat_book_get_REGINFO_PURCHASE(self):
        pass 
    
    def test_vat_book_get_REGINFO_DECLARATION(self):
        pass
    
    def test_calculate_sales_invoice_totals(self):
        pass
    
    def test_calculate_sales_invoice_count(self):
        pass
    
    def test_calculate_amount_total(self):
        pass
    
    def test_calculate_purchase_invoice_count(self):
        pass
    
    def test_calculate_amount_for_different_purchases_taxes(self):
        pass
    
    def test_calculate_amount_for_different_sales_taxes(self):
        pass
    
    def test_filter_invoices_type_purchases(self):
        # Replace this with your test data and options
        test_options = {
            'date': {
                'date_from': '2023-01-01',
                'date_to': '2023-12-31',
            },
            # Add other required options
        }

        # Create test invoices of type 'in_invoice' and 'in_refund'
        test_invoices = self.env['account.move'].search([
            ('move_type', 'in', ['in_invoice', 'in_refund']),
            ('date', '>=', test_options['date']['date_from']),
            ('date', '<=', test_options['date']['date_to']),
        ])

        filtered_invoices = self.env['l10n_bg_tax_report_handler']. _filter_invoices_type_purchases(test_options, test_invoices)

        # Add assertions to check if the invoices are correctly filtered
        for invoice in filtered_invoices:
            self.assertIn(invoice.move_type, ['in_invoice', 'in_refund'])
    
    def test_filter_invoices_type_sales(self):
        # Replace this with your test data and options
        test_options = {
            'date': {
                'date_from': '2023-01-01',
                'date_to': '2023-12-31',
            },
            # Add other required options
        }

        # Create test invoices of type 'out_invoice' and 'out_refund'
        test_invoices = self.env['account.move'].search([
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('invoice_date', '>=', test_options['date']['date_from']),
            ('invoice_date', '<=', test_options['date']['date_to']),
        ])

        filtered_invoices = self.env['l10n_bg_tax_report_handler']. _filter_invoices_type_sales(test_options, test_invoices)

        # Add assertions to check if the invoices are correctly filtered
        for invoice in filtered_invoices:
            self.assertIn(invoice.move_type, ['out_invoice', 'out_refund'])
    
    def test_filter_invoices_by_date_range(self):
        options = {
            'date': {
                'date_from': '2023-01-01',
                'date_to': '2023-12-31',
            }
        }

        # Create test invoices with different invoice_date values
        invoice1 = self.env['account.move'].create({
            'name': 'Invoice 1',
            'invoice_date': '2023-03-15',
            # Add other required fields
        })

        invoice2 = self.env['account.move'].create({
            'name': 'Invoice 2',
            'invoice_date': '2023-06-20',
            # Add other required fields
        })

        # Call the method to be tested
        filtered_invoices = self._filter_invoices_by_date_range(options, self.env['account.move'])

        # Assertions
        self.assertIn(invoice1, filtered_invoices, "Invoice 1 should be included in the filtered invoices")
        self.assertIn(invoice2, filtered_invoices, "Invoice 2 should be included in the filtered invoices")

    
    def test_filter_invoices_by_date_range_purchases(self):
        options = {
            'date': {
                'date_from': '2023-01-01',
                'date_to': '2023-12-31',
            }
        }

        # Create test invoices with different invoice_date values
        vendor_bill_one = self.env['account.move'].create({
            'name': 'Vendor Bill 1',
            'date': '2023-03-15',
            # Add other required fields
        })

        vendor_bill_two = self.env['account.move'].create({
            'name': 'Vendor Bill 2',
            'date': '2023-06-20',
            # Add other required fields
        })

        # Call the method to be tested
        filtered_invoices = self._filter_invoices_by_date_range_purchases(options, self.env['account.move'])

        # Assertions
        self.assertIn(vendor_bill_one, filtered_invoices, "Vendor Bill 1 should be included in the filtered invoices")
        self.assertIn(vendor_bill_two, filtered_invoices, "Vendor Bill 2 should be included in the filtered invoices")
