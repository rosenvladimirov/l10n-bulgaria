# Bulgarian Company Registry Integration for Odoo

Integration module for Odoo that connects to Bulgarian Open Data Portal (data.egov.bg) to fetch and populate company information from the Trade Register.

**⚠️ Important**: This module is designed to work with `l10n_bg_config` module which provides Bulgarian localization including UIC/EIK validation.

## Features

- **Search companies** by EIK (Bulgarian company ID) or company name
- **Auto-populate partner data** including:
  - Company name (Bulgarian and English)
  - EIK and BULSTAT numbers
  - VAT registration number
  - Full address in Bulgarian
  - Legal form
  - Registration date and number
  - Economic activity codes (NACE)
- **Bilingual support** - store both Bulgarian and English company names
- **Offline mode** - works with downloaded data dumps from data.egov.bg
- **Smart search** - fuzzy matching for company names

## Installation

### Prerequisites

```bash
pip install requests stdnum
```

**Required Modules:**
- `l10n_bg_config` - Bulgarian localization module (provides UIC/EIK fields and validation)

### Install Module

1. Ensure `l10n_bg_config` is installed first
2. Copy the `bg_company_registry` folder to your Odoo addons directory
3. Restart Odoo server
4. Update Apps List in Odoo
5. Install "Bulgarian Company Registry Integration" module

**Note**: If you don't have `l10n_bg_config`, contact your Odoo provider or see [INTEGRATION.md](INTEGRATION.md) for details.

## Data Import

### Step 1: Download Trade Register Data

Visit the Bulgarian Open Data Portal:
https://data.egov.bg/organisation/dataset/2df0c2af-e769-4397-be33-fcbe269806f3

Download the latest CSV file of the Trade Register. Files are organized by year and quarter.

### Step 2: Import Data into Odoo

#### Option A: Using Python Shell

```python
# Connect to Odoo using odoo-bin shell
./odoo-bin shell -d your_database

# Import data
from odoo.api import Environment

env = Environment(cr, SUPERUSER_ID, {})
registry_model = env['bg.company.registry']

# Import from CSV file
csv_path = '/path/to/downloaded/trade_register.csv'
count = registry_model.import_csv_data(csv_path)
print(f"Imported {count} companies")

# Commit the transaction
cr.commit()
```

#### Option B: Using Odoo Interface (Planned)

A future version will include an import wizard in the Odoo interface.

## Usage

### Search and Populate Partner Data

#### From Partner Form:

1. Open a partner record (existing or new)
2. Enter the company's EIK number in the "EIK" field
3. Click "Fetch from Registry" button
4. Company data will be automatically populated

#### Using Search Wizard:

1. Open a partner record
2. Click "Search Company Registry" button
3. Choose search type (by EIK or by name)
4. Enter search criteria
5. Click "Search"
6. Select a company from results
7. Click "Populate Partner"

### Create Partner from Registry:

1. Go to Contacts menu
2. Click "Create"
3. Click "Search Company Registry" button
4. Search for company
5. Select company
6. Click "Create New Partner"

### Browse Registry Data:

1. Go to Bulgarian Registry menu
2. View all imported companies
3. Filter by status, VAT registration, etc.
4. Create partners directly from registry records

## Data Structure

### Field Integration with l10n_bg_config

This module **reuses** existing Bulgarian localization fields:

| Data | Field | Source Module |
|------|-------|---------------|
| EIK | `l10n_bg_uic` | l10n_bg_config |
| UIC Type | `l10n_bg_uic_type` | l10n_bg_config |
| VAT | `vat` | base (validated by l10n_bg_config) |

### Additional Fields (Added by this module)

| Field | Description |
|-------|-------------|
| `name` | **Multilingual company name** (translate=True, BG/EN via res.transliterate.mixin) |
| `company_registry` | **Registration number** (standard Odoo field for company registration) |
| `bg_legal_form` | Legal form (ООД, ЕООД, АД, etc.) |
| `bg_registration_date` | Registration date |
| `bg_registration_court` | Registration court |
| `bg_activity_code` | NACE activity code |
| `bg_activity_description` | Activity description |
| `bg_registry_id` | Link to registry data |

**Note on standard Odoo fields:**
- `name` automatically stores both Bulgarian and English using `res.transliterate.mixin`
- `company_registry` is Odoo's standard field for registration numbers (unique per country)

### CSV Column Mapping

The module expects the following columns from data.egov.bg Trade Register CSV:

| CSV Column | Odoo Field | Description |
|------------|------------|-------------|
| EIK | eik | Company identification number |
| Firma | company_name_bg | Company name in Bulgarian |
| PravnaForma | legal_form_bg | Legal form (ООД, ЕООД, АД, etc.) |
| Sedal_Adres | address_full_bg | Full registered address |
| DatRegistr | registration_date | Registration date |
| status | status | Company status |

**Note:** Column names may vary. Check the actual CSV structure and adjust the `_map_csv_row_to_vals` method in `models/bg_company_registry.py` if needed.

## API Integration (Future Enhancement)

Currently, the module works with downloaded CSV files for offline operation. Future versions will include:

- Direct CKAN API integration with data.egov.bg
- Real-time company data updates
- Automatic synchronization
- Online search without data import

## Configuration

### Settings (Planned)

Future configuration options will include:
- Auto-update frequency
- API credentials (if required)
- Default language for company names
- Address formatting preferences

## Troubleshooting

### Common Issues

**Issue:** "No company data found for EIK"
- **Solution:** Make sure you have imported the Trade Register CSV data

**Issue:** CSV import fails
- **Solution:** Check CSV encoding (should be UTF-8) and column names

**Issue:** Address not populating correctly
- **Solution:** Address parsing from Bulgarian format may need adjustment

### Debug Mode

Enable debug mode to see detailed logs:

```python
import logging
_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)
```

## Data Updates

Trade Register data on data.egov.bg is updated periodically. To get the latest data:

1. Download the newest CSV dump from data.egov.bg
2. Run the import process again
3. Existing companies will be updated with new information

## Technical Details

### Module Structure

```
bg_company_registry/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── bg_company_registry.py  # Main registry model
│   └── res_partner.py           # Partner extensions
├── wizard/
│   ├── __init__.py
│   └── bg_company_search_wizard.py
├── views/
│   ├── bg_company_registry_views.xml
│   ├── res_partner_views.xml
│   └── bg_company_search_wizard_views.xml
├── security/
│   └── ir.model.access.csv
└── README.md
```

### Models

- `bg.company.registry` - Stores cached company data from Trade Register
- `res.partner` - Extended with Bulgarian company fields and methods

### Key Methods

- `search_company_by_eik(eik)` - Search company by EIK
- `search_company_by_name(name)` - Search companies by name
- `import_csv_data(csv_path)` - Import data from CSV file
- `action_fetch_from_registry()` - Populate partner from registry

## License

LGPL-3

## Author

Rosen Vladimirov

## Support

For issues and feature requests, please contact the author or create an issue in the repository.

## Roadmap

- [ ] Direct CKAN API integration
- [ ] Auto-update mechanism
- [ ] Import wizard UI
- [ ] Export company lists
- [ ] Advanced filtering and search
- [ ] Integration with Bulgarian address standards
- [ ] Multi-company support
- [ ] Historical data tracking

## Contributing

Contributions are welcome! Please ensure:
- Code follows Odoo coding guidelines
- All methods are documented
- Security access rights are properly configured
- XML views are properly structured

## Changelog

### Version 18.0.1.0.0
- Initial release
- Basic company search by EIK and name
- CSV data import
- Partner auto-population
- Bilingual support (Bulgarian/English)
