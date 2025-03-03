## Overview
The **currency_rate_update_bg_bnb** module is designed to automate the process of updating currency exchange rates in Odoo, specifically using data provided by the **Bulgarian National Bank (BNB)**. It ensures that companies operating in Bulgaria or using BNB as their primary source for currency rates can maintain accurate and up-to-date exchange rates for seamless financial operations.
## Purpose of the Module
### Why is this Module Useful?
1. **Automated Currency Updates**:
    - Businesses that trade internationally or deal with multiple currencies need accurate exchange rates for financial reporting, invoice calculations, and tax compliance. Manually updating rates can be time-consuming and error-prone.

2. **Trusted Data Source**:
    - The module relies on the official exchange rates published by the Bulgarian National Bank (BNB), ensuring reliability and accuracy.

3. **Time-Saving for Businesses**:
    - Automating the process saves significant manual effort and reduces the risk of errors, especially for companies dealing with frequent or large-volume transactions across currencies.
## Module Dependencies and Related Features
### Dependencies:
- **base**: Required for the core currency and exchange rate functionality in Odoo.
- **currency_rate_update**: Provides the general framework for updating rates in Odoo. `currency_rate_update_bg_bnb` extends this framework to specifically retrieve rates from BNB.

### Related Modules:
1. **account**:
    - Works seamlessly with this module to align currency rates for accounting operations and journal entries.

2. **l10n_bg**:
    - For businesses using the Bulgarian localization, this module complements it by ensuring exchange rates align with local legal requirements.

### Suggested Setups:
- **Multi-Company**:
    - For businesses operating in Bulgaria with international branches, this module helps maintain consistency in exchange rates across companies.

- **Multi-Currency Environments**:
    - Essential in setups dealing with invoices, payments, or transactions in multiple currencies.
 This module is particularly valuable for businesses dealing with the Bulgarian market or requiring precise currency updates from trusted official sources such as the Bulgarian National Bank.
