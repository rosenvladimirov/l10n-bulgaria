## General Information
The **l10n_bg_tax_offices** module is part of the Odoo localization for Bulgaria and is designed to add **regional tax offices (Territorial Directorates of the National Revenue Agency - NRA)** as reference data into the system. It allows businesses to associate tax operations, documents, and company data with the specific tax authority they are registered with. This facilitates the automation of tax reporting processes and compliance with Bulgarian legislation.

## Main Idea
In Bulgaria, every company is associated with a specific territorial directorate (TD) of the National Revenue Agency (NRA). This module helps businesses using Odoo to register and associate tax offices in the system to correctly reflect their tax operations.

## Reason for the Module
Bulgarian legislation requires businesses to fill out their documentation properly, including specifying the relevant tax offices. The absence of centralized management of these data might complicate operations, especially for generating documents, reports, and statements.

## Purpose of the Module
The module is designed to provide:
1. **Predefined list of tax offices**:
   - All regional tax offices of the NRA are preloaded into the system.
2. **Association with companies and tax documents**:
   - Enables businesses to specify the tax office they are registered with.
3. **Integration with other Bulgarian localization modules**:
   - Works with other modules like **l10n_bg** (the main module for Bulgarian localization) and modules for VAT declarations or other tax reports.

## How Does It Add Value?
- **Document Automation**: Automatically includes tax office information in documents such as invoices, notes, protocols, and reports.
- **Compliance with NRA Standards**: Ensures synchronization with the requirements of the National Revenue Agency, preventing errors when submitting documents.
- **Simplified Tax Entity Management**: Allows categorization and association of different companies or warehouses with their respective tax office.

## Key Users
This module is designed for:
- Companies registered with the NRA.
- Organizations managing documents or submitting reports to Bulgarian tax authorities.
- Accountants preparing and processing tax data.

## Main Features
1. **Preloaded list of NRA Territorial Directorates**:
   - Sofia, Plovdiv, Varna, Burgas, and others (all active TDs across Bulgaria).
2. **Easy Integration**:
   - Can be used alongside any accounting modules in Odoo.
3. **Customization**:
   - Users can add or edit details for tax offices.

## Implementation Results
By using **l10n_bg_tax_offices**, businesses save time and resources by:
- Reducing the risk of errors when submitting reports to the NRA.
- Ensuring full transparency regarding the association with tax institutions.
- Increasing efficiency in document management.

## Integration with Other Modules
- **l10n_bg**: Core module for Bulgarian localization – provides a legal framework.
- **l10n_bg_reports_audit**: Connection with tax reports and audits.
- **account**, **invoicing**: Integration with modules for invoicing and accounting.
