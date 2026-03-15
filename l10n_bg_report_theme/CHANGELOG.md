# Changelog

All notable changes to the l10n_bg_report_theme module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [18.0.5.2.0] - 2026-03-14

### Removed
- Removed `address_layout` override that was suppressing the `address` variable in `web.address_layout`

## [18.0.5.1.0] - 2026-03-13

### Added
- Group-level control for signature sections across documents (invoices, sale orders, stock pickings, purchase orders)
- `partner_id` field to tax actions

### Changed
- License changed from AGPL-3 to LGPL-3
- Adjusted column widths in document title template for improved readability
- Enhanced report templates and documentation for localization standards
- Applied ESLint directives and optimized import order
- Moved group definition for signatures control to improve structure
- Refined report template title and date layout

### Removed
- Non-standard manifest keys (`odoo_version`, `python_version`, `tags`)

## [18.0.5.0.3] - 2026-01-28

### Changed
- Import `Command` in `base_document_layout`
- Refined report template title and date layout for readability
- Added subtle background color for subtotal rows in `layout_sections.scss`

## [18.0.5.0.2] - 2026-01-22

### Changed
- Simplified template logic and improved `t-options` for phone and mobile fields
- Enhanced layout handling with streamlined document structure
- Refined logo styling and reset opacity filter for layout consistency
- Adjusted z-index for pseudo-elements, ensured logo visibility

## [18.0.5.0.1] - 2026-01-16

### Added
- `t-if` condition for `layout_document_title` logic
- Inverse method for `color` field in layout wizard to synchronize changes

### Changed
- Refactored SCSS color handling and enhanced preview logic
- Refined group naming and reduced font sizes
- Removed unused privileges and category
- Enabled `force_save` for `color` and `color_rgb` fields
- Replaced `not is_l10n_bg_record` with layout-based conditions

## [18.0.5.0.0] - 2026-01-12

### Added
- Colors for header right and footer left sections
- Field invisibility logic improvements

### Changed
- Adjusted footer padding

## [18.0.4.0.6] - 2026-01-06

### Added
- `.deal-content-separator` class
- Alternating row background color for improved readability
- Specific classes for section headers and footers

### Changed
- Refined footer styles
- Adjusted background color for tables in report sections
- Enhanced company details layout and report styling consistency
- Refined address section condition and information section padding

## [18.0.4.0.4] - 2025-12-31

### Added
- `address_layout` to `REPORT_REFS`

## [18.0.4.0.3] - 2025-12-30

### Added
- Support for custom SCSS files in company settings
- SCSS files for variable colors and fonts in optional layout bundle
- `key` field to Sections layout and layout detection logic
- Methods for retrieving custom SCSS content
- Asset cache invalidation when updating SCSS colors

### Changed
- Refactored SCSS media queries and `sections` layout styles
- Improved company-specific class logic in report templates
- Enhanced SCSS border definitions and Sections layout detection
- Escaped SCSS content using `Markup` for safe rendering
- Simplified template logic by unifying `company` attribute handling

## [18.0.4.0.0] - 2025-12-29

### Added
- Optional layout bundle and conditional asset loading for 'sections' layout
- Test mode check in init file

### Changed
- Refactored SCSS handling to use user home directory for customization
- Updated copyright headers

## [18.0.3.0.7] - 2025-11-07

### Added
- Expanded module manifest with detailed description

### Changed
- Updated module versions and improved multilanguage support
- Simplified signature variables and streamlined layout structure
- Added support for user-specific signatures in reports
- Introduced font size variable for maintainability
- Set default report color schema

### Fixed
- Removed redundant tax totals template override in invoice report
- Fixed label assignments and report template formatting

## [18.0.3.0.4] - 2025-08-12

### Added
- Deal Date field to invoice reports
- Advanced access controls and signatures section
- Represent person control and color themes
- Security group for sale person details
- Raw and pro forma sale order report templates

### Changed
- Updated Bulgarian translations for invoice and account terminology
- Refactored templates for `l10n_bg_represent_contact_id` handling

### Fixed
- Fixed `no_deal_partner` value in report template
- Fixed conditional logic in report templates

## [18.0.3.0.0] - 2025-07-15

### Added
- Bulgarian stock report module integration
- Deal Date translation
- Bulgarian accounting features and configurations
- Views for product properties and related configurations

### Changed
- Refactored stock report layout and enhanced date formatting logic
- Improved fiscal positioning

## [18.0.2.0.0] - 2025-06-14

### Changed
- Refactored and cleaned up Bulgarian VAT reports and themes
- Extended localization with tax configuration and address management
- Improved HTML theme

## [18.0.1.0.0] - 2025-05-13

### Added
- Landscape layout features
- Wizards for configuration
- Report paper format definitions
- RGB color support for primary and secondary colors
- Additional formatting functions for document rendering
- Bulgarian translations for report theme

### Changed
- Refactored report theme assets and partner model init
- Improved layout customization
- Improved report templates and address handling

### Fixed
- Fixed CSS `var()` compatibility with wkhtmltopdf
- Fixed report template rendering
- Fixed pre-compile issues

## [18.0.0.1.0] - 2025-02-12

### Added
- Initial module release
- Section-based layout architecture (header, article, footer)
- Dual logo system (standard and print)
- Advanced background system for portrait and landscape
- Color theme system with logo color extraction
- Typography support (SF Text, SF Pro Text)
- Document templates for invoices, sales, and purchases
- Partner information display (deal partner and traditional modes)
- Signature section with dual signature layout
- Security groups for field visibility control
- SCSS/CSS asset architecture
- Paper format support
- Document layout wizard
- Multilanguage support
