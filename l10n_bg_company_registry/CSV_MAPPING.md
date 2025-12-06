# CSV Column Mapping Configuration

This document explains how to configure the CSV column mapping if the actual data.egov.bg CSV structure differs from the default.

## Default Column Mapping

The module expects these columns from data.egov.bg Trade Register CSV:

| CSV Column | Odoo Field | Description | Required |
|------------|------------|-------------|----------|
| EIK | eik | Company identification number | Yes |
| Firma | company_name_bg | Company name (Bulgarian) | Yes |
| PravnaForma | legal_form_bg | Legal form (ООД, ЕООД, АД) | No |
| Sedal_Adres | address_full_bg | Full registered address | No |
| DatRegistr | registration_date | Registration date | No |

## Checking Actual CSV Structure

Before importing, check your CSV file structure:

```bash
# View first few lines
head -20 trade_register_2024_Q4.csv

# Or in Python
import pandas as pd
df = pd.read_csv('trade_register_2024_Q4.csv', nrows=5)
print(df.columns.tolist())
```

## Customizing Column Mapping

If your CSV has different column names, update the mapping in:
`models/bg_company_registry.py` in the `_map_csv_row_to_vals` method.

### Example: Different Column Names

If your CSV has these columns:
- `ЕИК` instead of `EIK`
- `Фирмено_Наименование` instead of `Firma`
- `Правна_Форма` instead of `PravnaForma`

Update the method like this:

```python
def _map_csv_row_to_vals(self, row):
    """Map CSV row to model values"""
    
    # Try multiple column name variations
    eik = (row.get('ЕИК') or row.get('EIK') or 
           row.get('eik') or '').strip()
    
    company_name = (row.get('Фирмено_Наименование') or 
                   row.get('Firma') or 
                   row.get('company_name') or '').strip()
    
    legal_form = (row.get('Правна_Форма') or 
                 row.get('PravnaForma') or 
                 row.get('legal_form') or '').strip()
    
    # ... rest of the method
```

## Common CSV Variations

### Variation 1: Cyrillic Column Names

```python
eik = row.get('ЕИК', '').strip()
company_name = row.get('Фирма', '').strip()
legal_form = row.get('Правна форма', '').strip()
address = row.get('Седалище', '').strip()
```

### Variation 2: English Column Names

```python
eik = row.get('company_id', '').strip()
company_name = row.get('company_name', '').strip()
legal_form = row.get('legal_form', '').strip()
address = row.get('registered_address', '').strip()
```

### Variation 3: Abbreviated Names

```python
eik = row.get('ID', '').strip()
company_name = row.get('Name', '').strip()
legal_form = row.get('Type', '').strip()
address = row.get('Addr', '').strip()
```

## Additional Field Mappings

### VAT Number Mapping

If CSV has explicit VAT column:

```python
vat = row.get('VAT_Number', '').strip()
vals['vat_number'] = vat if vat else f"BG{eik}"
vals['vat_registered'] = bool(vat)
```

### Status Field

If CSV has status information:

```python
status_map = {
    'Active': 'active',
    'Inactive': 'inactive',
    'Ликвидация': 'liquidation',
    'Заличена': 'deleted',
}
status_raw = row.get('Status', 'Active').strip()
vals['status'] = status_map.get(status_raw, 'active')
```

### English Name Field

If CSV contains English translations:

```python
company_name_en = row.get('Company_Name_EN', '').strip()
if company_name_en:
    vals['company_name_en'] = company_name_en
```

### Detailed Address Fields

If CSV has separate address components:

```python
city = row.get('City', '').strip()
street = row.get('Street', '').strip()
postal = row.get('Postal_Code', '').strip()

vals['city_bg'] = city
vals['street_bg'] = street
vals['postal_code'] = postal

# Construct full address
if city or street:
    vals['address_full_bg'] = f"{street}, {city} {postal}".strip()
```

## Date Format Handling

The module supports multiple date formats. If your CSV uses a different format:

```python
def _parse_date(self, date_str):
    """Parse date string to date object"""
    if not date_str:
        return False
    
    # Add your date format here
    date_formats = [
        '%Y-%m-%d',      # 2024-12-01
        '%d.%m.%Y',      # 01.12.2024
        '%d/%m/%Y',      # 01/12/2024
        '%Y%m%d',        # 20241201
        '%d-%m-%Y',      # 01-12-2024
        '%m/%d/%Y',      # 12/01/2024 (US format)
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(str(date_str), fmt).date()
        except (ValueError, TypeError):
            continue
    
    return False
```

## Testing Your Configuration

After updating the mapping, test with a small sample:

```python
# Create test CSV
cat > test_sample.csv << EOF
ЕИК,Фирма,Правна_Форма,Адрес
131134023,СОФТУЕР ГРУП АД,АД,гр. София ул. Витоша 1
EOF

# Import test file
python3 import_trade_register.py \
    --database test_db \
    --csv test_sample.csv

# Check results in Odoo
```

## Validation Rules

Add validation for your data:

```python
def _map_csv_row_to_vals(self, row):
    vals = {...}  # Your mapping
    
    # Validation
    if not vals.get('eik') or len(vals['eik']) < 9:
        raise ValueError(f"Invalid EIK: {vals.get('eik')}")
    
    if not vals.get('company_name_bg'):
        raise ValueError("Company name is required")
    
    return vals
```

## Encoding Issues

If you encounter encoding problems:

```python
# Try different encodings
encodings = ['utf-8', 'cp1251', 'windows-1251', 'iso-8859-5']

for encoding in encodings:
    try:
        with open(csv_file_path, 'r', encoding=encoding) as f:
            # Process file
            break
    except UnicodeDecodeError:
        continue
```

## Performance Optimization

For large CSV files:

```python
# Use csv.DictReader with specific fields
fieldnames = ['EIK', 'Firma', 'PravnaForma', 'Sedal_Adres']
reader = csv.DictReader(csvfile, fieldnames=fieldnames)

# Skip header if needed
next(reader)

# Process in larger batches
batch_size = 500  # Increase for better performance
```

## Delimiter Detection

Auto-detect CSV delimiter:

```python
import csv

with open(csv_file_path, 'r', encoding='utf-8') as f:
    sample = f.read(1024)
    sniffer = csv.Sniffer()
    delimiter = sniffer.sniff(sample).delimiter
    print(f"Detected delimiter: '{delimiter}'")
```

## Getting Help

If you need help configuring the mapping:

1. Share the first few lines of your CSV file
2. Describe which fields are available
3. Specify any special formatting requirements

Contact: Check README.md for support information
