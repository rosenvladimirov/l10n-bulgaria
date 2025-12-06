# Changelog - Integration with l10n_bg_config

## Version 18.0.1.1.3 - Consistent l10n_bg_ Naming + Representative Auto-population

### Changes

#### 1. Consistent Field Naming
**Renamed all custom fields to use l10n_bg_ prefix:**
- ✅ `bg_legal_form` → `l10n_bg_legal_form`
- ✅ `bg_registration_date` → `l10n_bg_registration_date`
- ✅ `bg_registration_court` → `l10n_bg_registration_court`
- ✅ `bg_activity_code` → `l10n_bg_activity_code`
- ✅ `bg_activity_description` → `l10n_bg_activity_description`
- ✅ `bg_registry_id` → `l10n_bg_registry_id`
- ✅ `bg_registry_last_sync` → `l10n_bg_registry_last_sync`

**Reasoning:**
- Consistency with `l10n_bg_config` module naming convention
- All Bulgarian localization fields now use `l10n_bg_` prefix
- Better namespace organization
- Follows Odoo localization best practices

#### 2. Representative Auto-population
**Added automatic creation/linking of company representative:**

New method: `_populate_representative_from_registry(company_data)`
- Automatically populates `l10n_bg_represent_contact_id` from registry data
- Searches for existing representative by name or EGN
- Creates new representative contact if not found
- Sets proper type='represent' and links to company

**Registry data fields used:**
- `representative_name` - Full name of representative
- `representative_egn` (optional) - Personal identification number

**Logic:**
1. Check if representative already exists for company
2. Search by EGN first (most precise)
3. Search by name in existing contacts
4. If not found, create new contact with type='represent'
5. Link to `l10n_bg_represent_contact_id` field

#### 3. Benefits

**Consistent naming:**
- All custom fields now use `l10n_bg_` prefix
- Matches naming convention of `l10n_bg_config`
- Clear distinction between core Odoo and localization fields

**Representative automation:**
- No manual creation of representative contacts needed
- Automatic linking from Trade Register data
- Reuses existing contacts when possible
- Proper EGN validation when available

### Migration from 18.0.1.1.2

```python
# Rename fields in database
cr.execute("""
    ALTER TABLE res_partner 
    RENAME COLUMN bg_legal_form TO l10n_bg_legal_form;
    
    ALTER TABLE res_partner 
    RENAME COLUMN bg_registration_date TO l10n_bg_registration_date;
    
    ALTER TABLE res_partner 
    RENAME COLUMN bg_registration_court TO l10n_bg_registration_court;
    
    ALTER TABLE res_partner 
    RENAME COLUMN bg_activity_code TO l10n_bg_activity_code;
    
    ALTER TABLE res_partner 
    RENAME COLUMN bg_activity_description TO l10n_bg_activity_description;
    
    ALTER TABLE res_partner 
    RENAME COLUMN bg_registry_id TO l10n_bg_registry_id;
    
    ALTER TABLE res_partner 
    RENAME COLUMN bg_registry_last_sync TO l10n_bg_registry_last_sync;
""")
cr.commit()
```

Or use Odoo's migration system in `migrations/18.0.1.1.3/pre-migrate.py`

---

## Version 18.0.1.1.2 - Use Standard company_registry Field

### Changes

#### 1. Removed Duplicate Field
**Removed:**
- ❌ `bg_registration_number` - Now uses standard `company_registry` field

**Leverages standard Odoo field:**
- ✅ `company_registry` - Standard Odoo field for company registration numbers
- ✅ `company_registry_label` - Country-specific label (computed field)
- ✅ Unique per country constraint
- ✅ Built-in validation

#### 2. Benefits
- No custom field needed for registration number
- Consistent with Odoo standards
- Country-specific label ("Company ID" in Bulgaria)
- Unique constraint across country already implemented
- Better integration with other Odoo modules

### Migration from 18.0.1.1.1

```python
# Copy data from bg_registration_number to company_registry
partners = env['res.partner'].search([('bg_registration_number', '!=', False)])
for partner in partners:
    partner.company_registry = partner.bg_registration_number
cr.commit()
```

---

## Version 18.0.1.1.1 - Multilingual Name Support

### Changes

#### 1. Simplified Name Handling
**Removed separate name fields:**
- ❌ `bg_company_name` - Now uses base `name` field (translate=True)
- ❌ `bg_company_name_en` - Now uses base `name` field with lang='en_US'

**Leverages res.transliterate.mixin:**
- ✓ Automatic language detection (Cyrillic → Bulgarian)
- ✓ Auto-transliteration to English (via transliterate/unidecode)
- ✓ JSONB storage: `{'bg_BG': 'СОФТУЕР ГРУП АД', 'en_US': 'SOFTWARE GROUP JSC'}`
- ✓ Official English names from registry override auto-transliteration

#### 2. Code Simplification
**res_partner.py:**
- Removed `_set_multilingual_name()` method
- Simplified `action_fetch_from_registry()` to directly set English name when available
- Mixin automatically handles Bulgarian → English transliteration

#### 3. Benefits
- No field duplication
- Automatic language detection
- Consistent with other l10n_bg_config multilingual fields (street, city, etc.)
- Official registry translations override auto-transliteration

### Migration from 18.0.1.1.0

No data migration needed - `name` field already exists. Module will automatically use it for both languages.

---

## Version 18.0.1.1.0 - l10n_bg_config Integration

### Major Changes

#### 1. Field Integration
**Removed duplicate fields:**
- ❌ `bg_eik` - Now uses `l10n_bg_uic` from l10n_bg_config
- ❌ `bg_bulstat` - Now uses `l10n_bg_uic` from l10n_bg_config

**Reused existing fields:**
- ✓ `l10n_bg_uic` - For storing EIK/BULSTAT
- ✓ `l10n_bg_uic_type` - For identifier type
- ✓ `vat` - For VAT with validation

**Added new complementary fields:**
- ✓ Uses `name` (translate=True) for multilingual company names
- ✓ `bg_registration_court` - Registration court

#### 2. Dependency Changes
**Added:**
```python
'depends': ['base', 'contacts', 'l10n_bg_config']
```

#### 3. Code Changes

**res_partner.py:**
- `@api.onchange('l10n_bg_uic')` instead of `@api.onchange('bg_eik')`
- `action_fetch_from_registry()` now checks `l10n_bg_uic`
- `_prepare_partner_vals_from_registry()` populates `l10n_bg_uic` and `l10n_bg_uic_type`

**views/res_partner_views.xml:**
- Removed `bg_eik` and `bg_bulstat` from form view
- Updated filters to use `l10n_bg_uic`
- Updated search domains

#### 4. Documentation Updates
- Added INTEGRATION.md - Complete integration guide
- Updated README.md - Prerequisites and installation
- Updated QUICK_REFERENCE.md - Field mapping
- Updated examples to use `l10n_bg_uic`

### Benefits

1. **No Duplication**: Uses existing localization fields
2. **Better Validation**: Leverages stdnum validation from l10n_bg_config
3. **Consistency**: All modules use same fields
4. **Type Safety**: Automatic detection of EGN vs EIK vs PNF

### Migration from v18.0.1.0.0

If you're upgrading from the standalone version:

```python
# Migrate existing data
partners = env['res.partner'].search([('bg_eik', '!=', False)])
for partner in partners:
    partner.with_context(block_validate=True).write({
        'l10n_bg_uic': partner.bg_eik,
        'l10n_bg_uic_type': 'bg_uic',
        'vat': f"BG{partner.bg_eik}" if not partner.vat else partner.vat,
    })
```

### Compatibility

| Component | Version | Notes |
|-----------|---------|-------|
| Odoo | 16.0, 17.0, 18.0, 19.0 | All supported |
| l10n_bg_config | 16.0+, 17.0+, 18.0+, 19.0+ | **Required** |
| Python | 3.8+ | Required |
| stdnum | Latest | Required by l10n_bg_config |

### Breaking Changes

⚠️ **Fields Removed:**
- `bg_eik` → Use `l10n_bg_uic`
- `bg_bulstat` → Use `l10n_bg_uic`

⚠️ **New Dependency:**
- Requires `l10n_bg_config` module

### Upgrade Instructions

1. **Backup your database**
2. Install `l10n_bg_config` if not already installed
3. Update `bg_company_registry` module
4. Run migration script (if upgrading from v18.0.1.0.0)
5. Test partner creation and data fetching

### Testing Checklist

- [ ] Create new partner with VAT = "BG131134023"
- [ ] Verify `l10n_bg_uic` is automatically set
- [ ] Click "Fetch from Registry" button
- [ ] Verify all fields populate correctly
- [ ] Search by EIK in partner search
- [ ] Test company search wizard

### Known Issues

**Issue 1: Module not found**
- **Cause**: l10n_bg_config not installed
- **Solution**: Install l10n_bg_config first

**Issue 2: Field doesn't exist**
- **Cause**: l10n_bg_config not updated
- **Solution**: Update l10n_bg_config module

### Future Plans

- Auto-sync with Trade Register updates
- Support for more UIC types
- Integration with accounting modules
- Enhanced address parsing

### Support

For issues:
1. Check INTEGRATION.md
2. Verify l10n_bg_config is installed and updated
3. Check Odoo logs
4. Contact module author

---

**Version**: 18.0.1.1.0  
**Date**: December 2024  
**Author**: Rosen Vladimirov
