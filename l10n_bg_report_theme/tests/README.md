# Tests for l10n_bg_report_theme

## Overview

Comprehensive test suite for the Bulgarian Report Theme module, covering:
- Document layout customizations
- Company model extensions
- Report rendering
- Color management
- SCSS integration
- PDF generation

## Test Structure

```
tests/
├── __init__.py
├── test_l10n_bg_report_theme.py      # Main test suite
└── test_reports_override.py          # Override for base tests
```

## Test Classes

### 1. TestBaseDocumentLayout
Tests for `base.document.layout` customizations:
- Background images (portrait and landscape)
- Logo print functionality
- Color computation from logos
- Formatting functions availability
- Report layout activation/deactivation

### 2. TestResCompany
Tests for `res.company` extensions:
- Layout background selection
- Background images
- Logo print field
- Custom fonts (SF Text, SF Pro Text)

### 3. TestIrActionsReport
Tests for `ir.actions.report` customizations:
- Rendering context formatting functions
- Safe date/datetime formatting
- Handling of None values
- Widget-specific formatting

### 4. TestDocumentLayoutColors
Tests for `base.document.layout.colors`:
- HEX to RGB conversion
- Invalid color format handling
- SCSS file loading
- SCSS file saving
- Color onchange logic

### 5. TestReportRendering
Tests for PDF report generation:
- Invoice reports
- Purchase order reports
- Sale order reports
- Page overflow handling with custom theme

### 6. TestIntegration
Integration tests:
- Module installation
- View loading
- Report definitions
- Company theme usage

### 7. TestReportsRendering (Override)
Override for `base.tests.test_reports`:
- Skips page overflow test when Bulgarian theme is active
- Explains why pagination differs with custom layout

## Running Tests

### Run all tests for the module:
```bash
odoo -d your_database --test-enable --test-tags l10n_bg_report_theme --stop-after-init
```

### Run specific test class:
```bash
odoo -d your_database --test-enable --test-tags l10n_bg_report_theme.TestBaseDocumentLayout --stop-after-init
```

### Run with detailed logging:
```bash
odoo -d your_database --test-enable --test-tags l10n_bg_report_theme --log-level=test:INFO --stop-after-init
```

### Run only post-install tests:
```bash
odoo -d your_database --test-enable --test-tags post_install --stop-after-init
```

## Test Coverage

The test suite covers:

✅ **Model Extensions**
- All custom fields
- Computed fields
- Related fields
- Onchange methods

✅ **Rendering**
- PDF generation
- Formatting functions
- Date/datetime handling
- Template rendering

✅ **Colors**
- HEX to RGB conversion
- SCSS file operations
- Color computation from images
- Error handling

✅ **Integration**
- Module installation
- View loading
- Report activation
- Multi-company support

## Known Limitations

### Page Overflow Test
The standard `test_pdf_render_page_overflow` test expects specific pagination
with default Odoo layout. The Bulgarian theme uses:
- Custom margins
- Custom fonts
- Custom header/footer sizes
- Background images

This results in different page breaks. The test is **skipped** when Bulgarian
theme is active, with appropriate logging.

### SCSS File Operations
Tests for SCSS file operations use mocking to avoid file system dependencies.
Manual testing of actual SCSS generation is recommended.

### Image Processing
Tests use minimal 1x1 transparent PNG images. Real-world testing with actual
logos and backgrounds is recommended.

## Debugging Failed Tests

### Test fails with "AttributeError: 'dict' object has no attribute 'replace'"
**Cause**: Translate fields returning dicts
**Fix**: Ensure `ir_binary.py` override is properly loaded

### Test fails with "6 pages expected, got 2"
**Cause**: Page overflow test running with Bulgarian theme
**Fix**: Ensure `test_reports_override.py` is loaded and theme detection works

### Test fails with color conversion errors
**Cause**: Invalid color format or missing webcolors library
**Fix**: Check HEX color format is valid (#RRGGBB)

### Test fails to find SCSS file
**Cause**: Mocked file operations not set up correctly
**Fix**: Ensure `patch('builtins.open')` is properly configured

## CI/CD Integration

### GitLab CI Example:
```yaml
test:
  script:
    - odoo -d test_db --test-enable --test-tags l10n_bg_report_theme --stop-after-init
  coverage: '/TOTAL.*\s+(\d+%)$/'
```

### GitHub Actions Example:
```yaml
- name: Run tests
  run: |
    odoo -d test_db --test-enable --test-tags l10n_bg_report_theme --stop-after-init
```

## Contributing

When adding new features:
1. Add corresponding tests
2. Ensure all existing tests pass
3. Update this README if needed
4. Run tests with `--log-level=test:DEBUG` to verify

## License
AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)