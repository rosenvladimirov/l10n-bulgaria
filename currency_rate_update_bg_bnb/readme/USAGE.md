This guide explains how to use the `currency_rate_update_bg_bnb` module to automatically update currency exchange rates in Odoo with official data from the Bulgarian National Bank (BNB).
## 1. Configuring the Module
### Step 1: Installation
- Ensure the `currency_rate_update_bg_bnb` module is installed in your Odoo instance.
- Make sure the `currency_rate_update` module is also installed, as it provides the base functionality for currency updates.

### Step 2: Activation
1. Go to **Settings** → **General Settings**.
2. Search for the **Currency Exchange Rate Update** section.
3. Select **Bulgarian National Bank (BNB)** as the provider for currency exchange rates.

### Step 3: Scheduler Setup
- The module can automatically update exchange rates on a daily or periodic basis through a scheduled action.

1. Navigate to **Settings** → **Technical** → **Automation** → **Scheduled Actions**.
2. Look for the action titled **Update Currency Rates**.
3. Confirm or adjust the frequency to ensure rates are updated automatically at your desired intervals.

## 2. Using the Module
### Automatic Updates
- Once properly configured, the module will fetch and update currency rates from the Bulgarian National Bank at the scheduled time.
- Currency rates will be reflected in all relevant areas, including invoices, payments, and multi-currency transactions.

### Manual Updates
1. Navigate to **Accounting** → **Configuration** → **Currencies**.
2. Open the desired currency (e.g., EUR, USD).
3. Click the **Update Rates** button to fetch the latest exchange rate immediately.

## 3. Verifying Exchange Rate Updates
- To confirm that currency rates have been updated:
    1. Go to **Accounting** → **Configuration** → **Currencies**.
    2. Check the column **Latest Rate**, which will display the most recent value fetched from BNB.

## 4. Multi-Currency Use Cases
- For businesses handling multi-currency transactions, the module ensures that conversions between the Bulgarian Lev (BGN) and other currencies are always up to date.
- The updated rates will:
    - Automatically apply to invoices, payments, and journal entries involving multiple currencies.
    - Reflect in financial reporting and reconciliation processes.

## 5. Error Handling and Notifications
- In case of issues while fetching rates (e.g., network errors or unavailable BNB service):
    - The system will log errors under **Settings** → **Technical** → **Logs**.
    - Review these logs to diagnose and resolve issues.

## Notes
- This module is ideal for businesses operating in Bulgaria or using the Bulgarian National Bank as their trusted source for exchange rate data.
- It ensures compliance with local regulations while reducing the need for manual updates.
- For advanced setups, such as multi-company environments, ensure that currency configurations are consistent across all companies to avoid discrepancies.
