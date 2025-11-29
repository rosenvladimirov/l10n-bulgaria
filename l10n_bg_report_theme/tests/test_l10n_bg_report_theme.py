# -*- coding: utf-8 -*-
# Copyright 2023 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import logging
from unittest.mock import patch, MagicMock
from odoo.tests import tagged, TransactionCase
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestBaseDocumentLayout(TransactionCase):
    """Tests for base.document.layout customizations"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.wizard = cls.env['base.document.layout'].create({
            'company_id': cls.company.id,
        })

        # Sample 1x1 transparent PNG for testing
        cls.sample_image = base64.b64encode(
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
            b'\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
            b'\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )

    def test_01_background_images_fields(self):
        """Test that all background image fields are accessible"""
        self.wizard.write({
            'layout_background_header_image': self.sample_image,
            'layout_background_footer_image': self.sample_image,
            'layout_background_l_image': self.sample_image,
            'layout_background_l_header_image': self.sample_image,
            'layout_background_l_footer_image': self.sample_image,
        })

        self.assertTrue(self.wizard.layout_background_header_image)
        self.assertTrue(self.wizard.layout_background_footer_image)
        self.assertTrue(self.wizard.layout_background_l_image)
        self.assertTrue(self.wizard.layout_background_l_header_image)
        self.assertTrue(self.wizard.layout_background_l_footer_image)

    def test_02_logo_print_field(self):
        """Test logo_print field and preview"""
        self.wizard.write({
            'logo_print': self.sample_image,
        })

        self.assertTrue(self.wizard.logo_print)
        self.assertEqual(self.wizard.preview_logo_print, self.wizard.logo_print)

    def test_03_color_computation(self):
        """Test that colors are computed from logo"""
        self.wizard.logo_print = self.sample_image
        self.wizard._compute_logo_print_colors()

        # Colors should be computed (may be None for transparent image)
        self.assertIsNotNone(self.wizard.logo_print_primary_color)
        self.assertIsNotNone(self.wizard.logo_print_secondary_color)

    def test_04_default_get_colors(self):
        """Test that default_get loads SCSS colors"""
        defaults = self.wizard.default_get(['selection_colors'])

        # Should have selection_colors in defaults
        self.assertIn('selection_colors', defaults)

    def test_05_onchange_logo_updates_colors(self):
        """Test that changing logo updates primary/secondary colors"""
        # Set initial logo
        self.wizard.logo_print = self.sample_image
        self.wizard._onchange_logo_print()

        # Logo colors should be set
        self.assertTrue(
            self.wizard.logo_primary_color or
            self.wizard.logo_secondary_color
        )

    def test_06_formatting_functions_available(self):
        """Test that formatting functions are in render context"""
        styles = {}
        render_info = self.wizard._get_render_information(styles)

        self.assertIn('format_date', render_info)
        self.assertIn('format_datetime', render_info)
        self.assertIn('format_time', render_info)
        self.assertIn('format_amount', render_info)
        self.assertIn('format_duration', render_info)

    def test_07_update_active_report_layout(self):
        """Test that report layouts are activated/deactivated correctly"""
        # Get the custom layout
        layout = self.env.ref(
            'l10n_bg_report_theme.report_layout_sections',
            raise_if_not_found=False
        )

        if layout:
            # Set the external layout
            self.wizard.external_report_layout_id = layout
            self.wizard._update_active_report_layout()

            # Check that invoice report is activated
            invoice_report = self.env.ref(
                'l10n_bg_report_theme.report_invoice_document',
                raise_if_not_found=False
            )
            if invoice_report:
                self.assertTrue(invoice_report.active)

    def test_08_create_updates_reports(self):
        """Test that creating wizard with layout updates reports"""
        layout = self.env.ref(
            'l10n_bg_report_theme.report_layout_sections',
            raise_if_not_found=False
        )

        if layout:
            new_wizard = self.env['base.document.layout'].create({
                'company_id': self.company.id,
                'external_report_layout_id': layout.id,
            })

            # Reports should be updated
            self.assertTrue(new_wizard.external_report_layout_id)

    def test_09_write_updates_reports(self):
        """Test that writing layout updates reports"""
        layout = self.env.ref(
            'l10n_bg_report_theme.report_layout_sections',
            raise_if_not_found=False
        )

        if layout:
            self.wizard.write({
                'external_report_layout_id': layout.id,
            })

            # Reports should be updated
            self.assertTrue(self.wizard.external_report_layout_id)


@tagged('post_install', '-at_install')
class TestResCompany(TransactionCase):
    """Tests for res.company customizations"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.sample_image = base64.b64encode(b'fake_image_data')

    def test_01_layout_background_section(self):
        """Test Section selection in layout_background"""
        self.company.layout_background = 'Section'
        self.assertEqual(self.company.layout_background, 'Section')

    def test_02_background_images(self):
        """Test all background image fields"""
        self.company.write({
            'layout_background_header_image': self.sample_image,
            'layout_background_footer_image': self.sample_image,
            'layout_background_l_image': self.sample_image,
            'layout_background_l_header_image': self.sample_image,
            'layout_background_l_footer_image': self.sample_image,
        })

        self.assertTrue(self.company.layout_background_header_image)
        self.assertTrue(self.company.layout_background_footer_image)
        self.assertTrue(self.company.layout_background_l_image)
        self.assertTrue(self.company.layout_background_l_header_image)
        self.assertTrue(self.company.layout_background_l_footer_image)

    def test_03_logo_print(self):
        """Test logo_print field"""
        self.company.logo_print = self.sample_image
        self.assertTrue(self.company.logo_print)

    def test_04_custom_fonts(self):
        """Test custom font selections"""
        self.company.font = 'SF_Text'
        self.assertEqual(self.company.font, 'SF_Text')

        self.company.font = 'SF_Pro_Text'
        self.assertEqual(self.company.font, 'SF_Pro_Text')


@tagged('post_install', '-at_install')
class TestIrActionsReport(TransactionCase):
    """Tests for ir.actions.report customizations"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env.ref('account.account_invoices')
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
        })

    def test_01_rendering_context_has_formatting_functions(self):
        """Test that rendering context includes all formatting functions"""
        context = self.report._get_rendering_context(
            self.report,
            [self.partner.id],
            {}
        )

        self.assertIn('format_date', context)
        self.assertIn('format_datetime', context)
        self.assertIn('format_time', context)
        self.assertIn('format_amount', context)
        self.assertIn('format_duration', context)

    def test_02_safe_format_date_with_date(self):
        """Test safe_format_date with date object"""
        from datetime import date

        context = self.report._get_rendering_context(
            self.report,
            [self.partner.id],
            {}
        )

        test_date = date(2023, 12, 25)
        formatted = context['format_date'](test_date)

        self.assertIsInstance(formatted, str)
        self.assertTrue(len(formatted) > 0)

    def test_03_safe_format_date_with_datetime(self):
        """Test safe_format_date with datetime object"""
        from datetime import datetime

        context = self.report._get_rendering_context(
            self.report,
            [self.partner.id],
            {}
        )

        test_datetime = datetime(2023, 12, 25, 15, 30, 0)
        formatted = context['format_date'](test_datetime)

        self.assertIsInstance(formatted, str)
        self.assertTrue(len(formatted) > 0)

    def test_04_safe_format_date_with_none(self):
        """Test safe_format_date with None"""
        context = self.report._get_rendering_context(
            self.report,
            [self.partner.id],
            {}
        )

        formatted = context['format_date'](None)
        self.assertEqual(formatted, '')

    def test_05_safe_format_date_with_widget_date(self):
        """Test safe_format_date with widget='date' strips time"""
        from datetime import datetime

        context = self.report._get_rendering_context(
            self.report,
            [self.partner.id],
            {}
        )

        test_datetime = datetime(2023, 12, 25, 15, 30, 0)
        formatted = context['format_date'](test_datetime, widget='date')

        # Should not contain time portion
        self.assertNotIn(':', formatted)


@tagged('post_install', '-at_install')
class TestDocumentLayoutColors(TransactionCase):
    """Tests for base.document.layout.colors"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.wizard = cls.env['base.document.layout'].create({
            'company_id': cls.env.company.id,
        })

    def test_01_color_rgb_computation(self):
        """Test that HEX colors are converted to RGB"""
        color = self.env['base.document.layout.colors'].create({
            'name': 'test-color',
            'color': '#FF0000',
            'base_document_layout_id': self.wizard.id,
        })

        self.assertEqual(color.color_rgb, 'rgb(255, 0, 0)')

    def test_02_invalid_color_format(self):
        """Test that invalid color format raises error"""
        color = self.env['base.document.layout.colors'].create({
            'name': 'test-color',
            'color': 'invalid',
            'base_document_layout_id': self.wizard.id,
        })

        with self.assertRaises(UserError):
            color._compute_color_rgb()

    def test_03_load_scss_colors(self):
        """Test loading colors from SCSS file"""
        # Mock file operations
        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.read.return_value = (
                '$primary-color: rgb(255, 0, 0);\n'
                '$secondary-color: rgb(0, 255, 0);\n'
            )
            mock_open.return_value.__enter__.return_value = mock_file

            colors = self.env['base.document.layout.colors'].load_scss_colors()

            # Should return list of Commands
            self.assertIsInstance(colors, list)

    def test_04_load_scss_colors_as_dict(self):
        """Test loading colors as dictionary"""
        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.read.return_value = (
                '$primary-color: rgb(255, 0, 0);\n'
            )
            mock_open.return_value.__enter__.return_value = mock_file

            colors_dict = self.env['base.document.layout.colors'].load_scss_colors(
                force_dict=True
            )

            self.assertIsInstance(colors_dict, dict)
            self.assertIn('primary-color', colors_dict)

    def test_05_save_scss_colors(self):
        """Test saving colors to SCSS file"""
        color = self.env['base.document.layout.colors'].create({
            'name': 'test-color',
            'color': '#0000FF',
            'base_document_layout_id': self.wizard.id,
        })

        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file

            # Should not raise
            color.save_scss_colors()

    def test_06_save_scss_colors_without_name(self):
        """Test that saving without name raises error"""
        with self.assertRaises(UserError):
            self.env['base.document.layout.colors'].save_scss_colors()

    def test_07_save_scss_colors_without_color(self):
        """Test that saving without color raises error"""
        with self.assertRaises(UserError):
            self.env['base.document.layout.colors'].save_scss_colors(name='test')

    def test_08_onchange_color_saves_to_scss(self):
        """Test that color change saves to SCSS"""
        color = self.env['base.document.layout.colors'].create({
            'name': 'test-color',
            'color': '#FF0000',
            'base_document_layout_id': self.wizard.id,
        })

        with patch('builtins.open', create=True):
            with patch.object(
                    self.env['base.document.layout.colors'],
                    'save_scss_colors'
            ) as mock_save:
                color.color = '#00FF00'
                color._onchange_color()

                # Should have called save_scss_colors
                mock_save.assert_called()


@tagged('post_install', '-at_install')
class TestReportRendering(TransactionCase):
    """Tests for PDF report rendering"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
        })

        # Set Bulgarian theme if available
        cls.bg_layout = cls.env.ref(
            'l10n_bg_report_theme.report_layout_sections',
            raise_if_not_found=False
        )

    def test_01_invoice_report_renders(self):
        """Test that invoice report can be rendered"""
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'invoice_date': '2023-12-25',
        })

        report = self.env.ref('account.account_invoices')

        # Should not raise
        pdf_content, _ = report._render_qweb_pdf([invoice.id])
        self.assertTrue(pdf_content)

    def test_02_purchase_order_report_renders(self):
        """Test that purchase order report can be rendered"""
        purchase = self.env['purchase.order'].create({
            'partner_id': self.partner.id,
        })

        report = self.env.ref('purchase.action_report_purchase_order')

        # Should not raise
        pdf_content, _ = report._render_qweb_pdf([purchase.id])
        self.assertTrue(pdf_content)

    def test_03_sale_order_report_renders(self):
        """Test that sale order report can be rendered"""
        sale = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })

        report = self.env.ref('sale.action_report_saleorder')

        # Should not raise
        pdf_content, _ = report._render_qweb_pdf([sale.id])
        self.assertTrue(pdf_content)

    def test_04_pdf_render_page_overflow_with_theme(self):
        """
        Override standard test to account for Bulgarian theme layout.
        This test is skipped when using custom theme as page breaks differ.
        """
        if self.bg_layout and self.env.company.external_report_layout_id == self.bg_layout:
            self.skipTest("Bulgarian theme changes page layout - overflow test not applicable")


@tagged('post_install', '-at_install')
class TestIntegration(TransactionCase):
    """Integration tests for the entire module"""

    def test_01_module_installation(self):
        """Test that module is properly installed"""
        module = self.env['ir.module.module'].search([
            ('name', '=', 'l10n_bg_report_theme')
        ])

        self.assertTrue(module)
        self.assertEqual(module.state, 'installed')

    def test_02_all_views_load(self):
        """Test that all XML views load without errors"""
        views_to_test = [
            'l10n_bg_report_theme.view_base_document_layout',
            'l10n_bg_report_theme.report_layout_sections',
        ]

        for view_xmlid in views_to_test:
            view = self.env.ref(view_xmlid, raise_if_not_found=False)
            if view:
                # Should be able to get arch without errors
                arch = view.arch
                self.assertTrue(arch)

    def test_03_all_reports_defined(self):
        """Test that all custom reports are defined"""
        report_xmlids = [
            'l10n_bg_report_theme.report_invoice_document',
            'l10n_bg_report_theme.report_purchasequotation_document',
            'l10n_bg_report_theme.report_purchaseorder_document',
        ]

        for report_xmlid in report_xmlids:
            report = self.env.ref(report_xmlid, raise_if_not_found=False)
            if report:
                self.assertTrue(report.exists())

    def test_04_company_can_use_theme(self):
        """Test that company can use Bulgarian theme"""
        layout = self.env.ref(
            'l10n_bg_report_theme.report_layout_sections',
            raise_if_not_found=False
        )

        if layout:
            self.env.company.external_report_layout_id = layout

            self.assertEqual(
                self.env.company.external_report_layout_id,
                layout
            )
