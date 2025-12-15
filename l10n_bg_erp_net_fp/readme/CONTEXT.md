## Business Need

In Bulgaria, all businesses using cash registers must comply with NAP (National Revenue Agency) regulations requiring fiscal printers for all cash transactions. Traditional fiscal printer integrations create backend bottlenecks in high-traffic retail environments.

This module addresses the need for:
- **Compliance** with Bulgarian fiscal regulations (Наредба Н-18)
- **Performance** in high-volume POS environments
- **Reliability** with automatic fallback mechanisms
- **Ease of use** with automatic tax mapping and minimal configuration

## Use Cases

This module is useful in:

1. **Retail stores** - High-frequency cash transactions requiring fast fiscal printing
2. **Restaurants** - Multiple POS terminals sharing fiscal printer resources
3. **Multi-location businesses** - Centralized fiscal printer management
4. **Seasonal businesses** - Automatic Z-reports for daily closing

## Approach

The module uses a **hybrid architecture**:

- **Frontend (JavaScript)**: Handles high-frequency fiscal receipt printing directly from browser to ErpNet.FP server, bypassing Odoo backend to avoid bottlenecks
- **Backend (Python)**: Manages administrative operations (Z/X reports, cash operations) where reliability is more important than speed

This approach provides the best of both worlds: performance for receipts and reliability for reports.

## Related Modules

**Dependencies:**
- `point_of_sale` - Odoo POS core functionality
- `account` - Tax group configuration

**Works well with:**
- `pos_restaurant` - Restaurant-specific POS features
- `pos_discount` - Discount handling (automatically included in fiscal receipt)
- Multi-company setups - Each POS can have its own fiscal printer

**External Requirements:**
- **ErpNet.FP Server** - Fiscal printer communication server
- **Supported fiscal printers**: Tremol, Datecs, Daisy, and other Bulgarian-certified devices

## Suggested Setup

- **Single location**: One ErpNet.FP server per location, multiple POS terminals sharing it
- **Multi-location**: One ErpNet.FP server per location, centralized configuration in Odoo
- **Development/Testing**: Use ErpNet.FP demo mode without physical printer
