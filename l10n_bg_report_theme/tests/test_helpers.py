# -*- coding: utf-8 -*-
# Copyright 2023 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

"""
Test utilities and helpers for l10n_bg_report_theme module.

Provides common fixtures, helper functions, and test data for report theme testing.
"""

import base64
import io
from PIL import Image


class TestImageGenerator:
    """Helper class to generate test images with specific properties"""

    @staticmethod
    def generate_transparent_png(width=1, height=1):
        """Generate a transparent PNG image"""
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue())

    @staticmethod
    def generate_colored_png(width=100, height=100, color='#FF0000'):
        """Generate a colored PNG image"""
        # Convert hex to RGB
        hex_color = color.lstrip('#')
        rgb = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

        img = Image.new('RGB', (width, height), rgb)
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue())

    @staticmethod
    def generate_gradient_png(width=100, height=100):
        """Generate a gradient PNG image for color extraction testing"""
        img = Image.new('RGB', (width, height))
        pixels = img.load()

        for y in range(height):
            for x in range(width):
                # Red gradient
                pixels[x, y] = (int(255 * x / width), 0, int(255 * y / height))

        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue())

    @staticmethod
    def get_sample_1x1_png():
        """Get the minimal 1x1 transparent PNG for quick tests"""
        return base64.b64encode(
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
            b'\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
            b'\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )


class SCSSTestHelper:
    """Helper class for SCSS-related testing"""

    @staticmethod
    def generate_scss_content(colors_dict):
        """
        Generate SCSS content from a dictionary of colors.

        Args:
            colors_dict: Dict like {'primary-color': 'rgb(255, 0, 0)'}

        Returns:
            str: SCSS file content
        """
        content = "/* colors */\n"
        for name, value in colors_dict.items():
            content += f"${name}: {value};\n"
        return content

    @staticmethod
    def parse_scss_content(content):
        """
        Parse SCSS content and extract color variables.

        Args:
            content: SCSS file content string

        Returns:
            dict: Dictionary of variable names to values
        """
        import re
        pattern = r'\$([a-zA-Z-]+):\s*(.+?);'
        matches = re.findall(pattern, content)
        return {name: value.strip() for name, value in matches}

    @staticmethod
    def hex_to_rgb_string(hex_color):
        """
        Convert HEX color to RGB string format.

        Args:
            hex_color: Color in #RRGGBB format

        Returns:
            str: Color in 'rgb(R, G, B)' format
        """
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
        return f'rgb({r}, {g}, {b})'


class PDFTestHelper:
    """Helper class for PDF-related testing"""

    @staticmethod
    def count_pdf_pages(pdf_content):
        """
        Count pages in PDF content.

        Args:
            pdf_content: Binary PDF data

        Returns:
            int: Number of pages
        """
        try:
            import PyPDF2
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
            return len(pdf_reader.pages)
        except ImportError:
            # Fallback: count /Type /Page occurrences
            return pdf_content.count(b'/Type /Page')

    @staticmethod
    def extract_pdf_text(pdf_content):
        """
        Extract text from PDF content.

        Args:
            pdf_content: Binary PDF data

        Returns:
            str: Extracted text
        """
        try:
            import PyPDF2
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
            text = ''
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
        except ImportError:
            return ''


class ReportTestData:
    """Common test data for report testing"""

    @staticmethod
    def get_partner_data():
        """Get sample partner data for testing"""
        return {
            'name': 'Test Partner БГ',
            'street': 'ул. Тестова 123',
            'city': 'София',
            'zip': '1000',
            'country_id': False,  # Set to Bulgaria in actual tests
            'vat': 'BG123456789',
            'phone': '+359 2 123 4567',
            'email': 'test@example.bg',
        }

    @staticmethod
    def get_invoice_data(partner_id):
        """Get sample invoice data for testing"""
        return {
            'move_type': 'out_invoice',
            'partner_id': partner_id,
            'invoice_date': '2023-12-25',
            'currency_id': False,  # Set in actual tests
        }

    @staticmethod
    def get_invoice_line_data(product_id):
        """Get sample invoice line data"""
        return {
            'product_id': product_id,
            'quantity': 10.0,
            'price_unit': 100.0,
            'name': 'Test Product',
        }

    @staticmethod
    def get_purchase_order_data(partner_id):
        """Get sample purchase order data"""
        return {
            'partner_id': partner_id,
            'date_order': '2023-12-25',
        }

    @staticmethod
    def get_sale_order_data(partner_id):
        """Get sample sale order data"""
        return {
            'partner_id': partner_id,
            'date_order': '2023-12-25',
        }


class LayoutTestHelper:
    """Helper for layout-related testing"""

    @staticmethod
    def is_bulgarian_theme_active(env):
        """Check if Bulgarian theme is currently active"""
        bg_layout = env.ref(
            'l10n_bg_report_theme.report_layout_sections',
            raise_if_not_found=False
        )
        return bg_layout and env.company.external_report_layout_id == bg_layout

    @staticmethod
    def activate_bulgarian_theme(env):
        """Activate Bulgarian theme for testing"""
        bg_layout = env.ref(
            'l10n_bg_report_theme.report_layout_sections',
            raise_if_not_found=False
        )
        if bg_layout:
            env.company.external_report_layout_id = bg_layout
            return True
        return False

    @staticmethod
    def deactivate_bulgarian_theme(env):
        """Deactivate Bulgarian theme (restore default)"""
        default_layout = env.ref('web.external_layout_standard')
        env.company.external_report_layout_id = default_layout


class MockFileHelper:
    """Helper for mocking file operations in tests"""

    @staticmethod
    def mock_scss_file_read(content):
        """
        Create a mock for reading SCSS file.

        Usage:
            with patch('builtins.open', MockFileHelper.mock_scss_file_read(content)):
                # Your test code
        """
        from unittest.mock import MagicMock, mock_open
        return mock_open(read_data=content)

    @staticmethod
    def mock_scss_file_write():
        """
        Create a mock for writing SCSS file.

        Usage:
            with patch('builtins.open', MockFileHelper.mock_scss_file_write()) as mock_file:
                # Your test code
                # Check: mock_file.return_value.write.called
        """
        from unittest.mock import MagicMock, mock_open
        mock_file = mock_open()
        return mock_file


# Test decorators
def skip_if_no_theme(test_func):
    """
    Decorator to skip test if Bulgarian theme is not available.

    Usage:
        @skip_if_no_theme
        def test_something(self):
            pass
    """

    def wrapper(self):
        bg_layout = self.env.ref(
            'l10n_bg_report_theme.report_layout_sections',
            raise_if_not_found=False
        )
        if not bg_layout:
            self.skipTest("Bulgarian theme not available")
        return test_func(self)

    return wrapper


def with_bulgarian_theme(test_func):
    """
    Decorator to run test with Bulgarian theme activated.

    Usage:
        @with_bulgarian_theme
        def test_something(self):
            pass
    """

    def wrapper(self):
        original_layout = self.env.company.external_report_layout_id
        try:
            LayoutTestHelper.activate_bulgarian_theme(self.env)
            return test_func(self)
        finally:
            self.env.company.external_report_layout_id = original_layout

    return wrapper
