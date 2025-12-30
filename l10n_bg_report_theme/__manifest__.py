# Copyright 2023 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Bulgaria - Report Theme Sections",
    "summary": """
            Professional report theme with modular section-based layout
            for Bulgarian business documents.""",
    "description": """
Bulgaria - Report Theme Sections
================================

This module provides a professional, customizable report theme specifically designed
for Bulgarian business documents, featuring a modular section-based layout system
with extensive customization options for headers, footers, backgrounds, and colors.

**Core Features**
-----------------

**Section-Based Layout Architecture**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Modular three-section design:
- **Header Section** - Company branding and contact information
- **Article Section** - Main document content area
- **Footer Section** - Page numbering and legal information
* Separate templates for portrait and landscape orientations
* Independent background images for each section
* Responsive design that adapts to different paper formats
* Clean separation of concerns for easy customization

**Dual Logo System**
~~~~~~~~~~~~~~~~~~~~
* **Standard Logo** - For screen display and digital documents
* **Print Logo** - Optimized for printed documents
* Automatic color extraction from logos for theme consistency
* Primary and secondary color detection from logo images
* Logo preview in document layout wizard
* Support for different logo sizes and formats

**Advanced Background System**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Portrait Orientation:**
* Header background (30mm x 210mm)
* Article/Content background (247mm x 210mm)
* Footer background (20mm x 210mm)

**Landscape Orientation:**
* Separate background images for landscape documents
* Automatic switching based on paper orientation
* Custom dimensions for landscape layouts
* Maintains design consistency across orientations

**Custom Background Layouts:**
* Built-in "Section" layout option
* Upload custom background images per section
* Geometric pattern support
* Full background customization per company

**Color Theme System**
~~~~~~~~~~~~~~~~~~~~~~
* Dynamic color extraction from company logos
* Customizable primary and secondary colors
* Selection theme colors with editable palette:
- Base colors from logo
- Custom color picker for fine-tuning
- Reset to logo colors functionality
* Color variables exposed via CSS custom properties
* Automatic contrast adjustment for readability
* Integration with webcolors library for color manipulation

**Typography Support**
~~~~~~~~~~~~~~~~~~~~~~
Enhanced font options including:
* **SF Text** - Apple's San Francisco font family
* **SF Pro Text** - Professional variant of SF font
* Standard Odoo fonts (Lato, Roboto, etc.)
* SCSS-based font loading system
* Consistent typography across all documents

**Document Templates**
~~~~~~~~~~~~~~~~~~~~~~

**Invoice Documents:**
* Enhanced invoice layout with Bulgarian specifications
* Deal date field display (l10n_bg_deal_date)
* Configurable visibility of:
- Due date (via security group)
- Delivery date (via security group)
- Deal date (via security group)
* Original/Copy designation
* Multiple invoice states: Draft, Posted, Cancelled
* Credit note and vendor bill layouts

**Sales Documents:**
* Quotation templates
* Sale order templates
* Pro-forma invoice layout
* Configurable delivery date display
* Salesperson visibility control (via security group)
* State-based document titles

**Purchase Documents:**
* Request for Quotation (RFQ) layout
* Purchase Order layout
* Cancelled PO handling
* Supplier information sections
* Delivery address management

**Partner Information Display**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Two Display Modes:**

1. **Deal Partner Mode** (default for Bulgarian documents)
 - Structured table layout with:
   * Company/Person names
   * Full addresses with city and country
   * Street addresses (line 1 and 2)
   * UIC (Unified Identification Code) numbers
   * VAT/TIN numbers
   * Representative/contact persons
 - Dual-column layout (SUPPLIER | CUSTOMER)
 - Labels: recipient vs sender
 - Conditional field display based on data availability

2. **No Deal Partner Mode** (traditional layout)
 - Classic "From" and "To" sections
 - Invoice and shipping addresses
 - Contact person details
 - Phone and mobile display
 - Attention line for specific recipients

**Document Header Information**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Document type and number display
* Dynamic document title based on state
* Date formatting with locale support
* "ORIGINAL" / "COPY" designation system
* Customizable labels and placeholders

**Signature Section**
~~~~~~~~~~~~~~~~~~~~~
* Dedicated signature area (via security group)
* Dual signature layout:
- Customer/Recipient signature
- Compiler/Sender signature
* Name and surname placeholders
* Configurable labels:
- recipient_name (CUSTOMER)
- sender_name (COMPILER)
- signature_placeholder
* Automatic current user name display
* Stamp area designation

**Company Contact Display**
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Enhanced header with:
* Company logo (print version)
* Phone and mobile numbers with icons
* Email address with icon
* Website URL with icon
* Alternative: company_details field
* Responsive layout (60% logo, 40% contact)

**Formatting Functions**
~~~~~~~~~~~~~~~~~~~~~~~~
Enhanced QWeb template functions:
* **format_date()** - Locale-aware date formatting
- Support for date and datetime objects
- Widget parameter for date-only display
- Fallback to strftime on errors
- Medium/short/long date format options
* **format_datetime()** - DateTime with timezone support
* **format_time()** - Time-only formatting
* **format_amount()** - Currency formatting
* **format_duration()** - Duration formatting

Safe date handling:
* Automatic detection of date vs datetime
* Graceful error handling with fallbacks
* Prevents crashes from format mismatches
* Locale-specific formatting

**Security Groups**
~~~~~~~~~~~~~~~~~~~
Configurable visibility control via groups:
* `group_control_due_date` - Show/hide due date
* `group_control_delivery_date` - Show/hide delivery date
* `group_control_sale_person` - Show/hide salesperson
* `l10n_bg_deal_date` - Show/hide Bulgarian deal date
* `group_control_represent_person` - Show/hide representatives
* `group_control_signatures` - Show/hide signature section

**SCSS/CSS Assets**
~~~~~~~~~~~~~~~~~~~
Organized stylesheet architecture:
* `sffont.scss` - SF font definitions
* `report_variable_colors.scss` - Color theme variables
* `report_variable_fonts.scss` - Font family variables
* `layout_background.scss` - Background image styles
* `layout_sections.scss` - Section-specific styles

CSS Custom Properties:
```scss
:root {
  --font-family: [Selected Font];
  --primary-color: [Primary Color];
  --secondary-color: [Secondary Color];
}
```

**Paper Format Support**
~~~~~~~~~~~~~~~~~~~~~~~~
* Custom paper format definitions
* A4 portrait and landscape
* Letter size support
* Custom margin configurations
* DPI settings for optimal print quality
* Header/footer space allocation

**Address Layout Enhancements**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* Extended address_layout template
* Show/hide address control via variable
* Flexible address formatting
* Multi-line address support
* Country-specific address formats

**Document Layout Wizard**
~~~~~~~~~~~~~~~~~~~~~~~~~~
Enhanced configuration interface:
* Visual logo preview (standard and print)
* Color picker with logo color extraction
* Separate sections for portrait/landscape backgrounds
* Upload interface for custom backgrounds:
- Header section images
- Article section images
- Footer section images
* Selection theme colors editor with editable list
* Mobile number display
* Reset to default colors button

**Template Activation System**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Intelligent template management:
* Automatic activation/deactivation of templates
* Based on selected external_report_layout_id
* Prevents template conflicts
* Clean switching between layout styles
* Maintains template state across updates

**Integration Points**
~~~~~~~~~~~~~~~~~~~~~~
Seamlessly integrates with:
* **l10n_bg_config** - Core Bulgarian localization
* **account** - Invoice and financial documents
* **sale** - Sales orders and quotations
* **purchase** - Purchase orders and RFQs
* **stock** - Delivery and picking documents
* All Bulgarian localization modules

**Use Cases**
~~~~~~~~~~~~~

**Professional Branding:**
- Consistent corporate identity across all documents
- Custom background images for brand reinforcement
- Logo-matched color schemes
- Professional typography

**Legal Compliance:**
- Bulgarian business document standards
- Required field display (UIC, VAT, representatives)
- Deal date tracking for legal purposes
- Proper document state indication

**Multi-company Operations:**
- Per-company customization
- Different themes for different entities
- Independent logo and color schemes
- Company-specific backgrounds

**Print Optimization:**
- Separate print logo for better quality
- Optimized backgrounds for printing
- Proper margins and spacing
- Page numbering in footer

**Technical Features**
~~~~~~~~~~~~~~~~~~~~~~
* Python 3.11+ required
* Odoo 18.0 compatible
* External dependency: `webcolors` library
* SCSS compilation support
* Image processing for logos
* Base64 encoding for embedded images
* Responsive CSS with media queries
* XPath-based template inheritance

**Data Files Included**
~~~~~~~~~~~~~~~~~~~~~~~
* report_layout.xml - Section layout definition
* report_paperformat_data.xml - Paper format configurations
* security.xml - Security groups definitions
* ir.model.access.csv - Access rights

**Customization Points**
~~~~~~~~~~~~~~~~~~~~~~~~
All templates support easy customization:
* XPath-based inheritance
* Variable-based configuration
* CSS custom properties
* Modular section design
* Override individual sections
* Add custom sections easily

**Benefits**
~~~~~~~~~~~~
* **Professional appearance** - Polished business documents
* **Bulgarian compliance** - Meets local business requirements
* **Brand consistency** - Unified look across all documents
* **Easy customization** - No code changes needed
* **Print ready** - Optimized for physical printing
* **Multi-language** - Supports translatable labels
* **Flexible** - Adapts to different business needs
* **Maintainable** - Clean code structure

**Note**: This module provides the visual foundation for all Bulgarian
business documents in Odoo, ensuring professional appearance while
maintaining compliance with Bulgarian business document standards.
  """,
    "version": "18.0.3.0.8",
    "development_status": "Production/Stable",
    "license": "AGPL-3",
    "author": "Rosen Vladimirov,Odoo Community Association (OCA)",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "depends": [
        "web",
        "sale",
        "account",
        "stock",
        "purchase",
        "l10n_bg_config",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "views/report_templates.xml",
        "data/report_layout.xml",
        "data/report_paperformat_data.xml",
        "views/res_company_views.xml",
        "views/base_document_layout_views.xml",
        "views/ir_action_report_templates.xml",
        "views/report_invoice.xml",
        "views/purchase_order_templates.xml",
        "views/purchase_quotation_templates.xml",
    ],
    'external_dependencies': {
        'python': ['webcolors'],
    },
    "demo": [],

    'images': [
        'static/description/banner.png',
    ],

    "assets": {
        "web.report_assets_common": [
            "l10n_bg_report_theme/static/src/webclient/actions/sffont.scss",
            "l10n_bg_report_theme/static/src/webclient/actions/reports/report_variable_colors.scss",
            "l10n_bg_report_theme/static/src/webclient/actions/reports/report_variable_fonts.scss",
        ],
    },
    'tags': ['localization', 'accounting', 'bulgaria', 'configuration'],

    # Version requirements
    'odoo_version': '18.0',
    'python_version': '>=3.11',
}
