This guide outlines the steps to install and set up the **currency_rate_update_bg_customs module** in your Odoo instance.
## Requirements
### Pre-Installation Checklist:
1. **Odoo Version**:
    - Ensure the module is compatible with your version of Odoo.

2. **Required Modules**:
    - The **currency_rate_update** module must be installed, as **currency_rate_update_bg_customs** extends its functionality.
    - Ensure basic accounting modules (`account`) are installed for proper functionality.

3. **Access Rights**:
    - You need administrative rights to install and configure this module.

4. **External Dependencies**:
    - Verify that your Odoo server has internet access to connect to the Customs Agency of Bulgaria for fetching rates.

## Installation Steps
### 1. Install the Module
1. Log into your Odoo instance with an admin account.
2. Go to **Apps** from the main menu.
3. Search for **currency_rate_update_bg_customs** in the app store.
4. Click **Install** to add the module to your system.

### 2. Enable Automatic Currency Updates
1. Navigate to **Settings** → **General Settings**.
2. Look for the section titled **Currency Exchange Rate Update**.
3. Activate the exchange rate update functionality by:
    - Selecting **Customs Agency of Bulgaria** as the provider.
    - Enabling the checkbox for **Automatic Updates** if required.
