# L10n BG Project Multilang

[![Lint Status](https://github.com/rosenvladimirov/l10n-bulgaria/workflows/pre-commit/badge.svg?branch=18.0)](https://github.com/rosenvladimirov/l10n-bulgaria/actions?query=workflow%3Apre-commit+branch%3A18.0)
[![Build Status](https://github.com/rosenvladimirov/l10n-bulgaria/workflows/test/badge.svg?branch=18.0)](https://github.com/rosenvladimirov/l10n-bulgaria/actions?query=workflow%3Atest+branch%3A18.0)
[![License: AGPL-3](https://img.shields.io/badge/licence-AGPL--3-blue.svg)](http://www.gnu.org/licenses/agpl-3.0-standalone.html)
[![OCA/l10n-bulgaria](https://img.shields.io/badge/github-OCA%2Fl10n--bulgaria-lightgray.png?logo=github)](https://github.com/rosenvladimirov/l10n-bulgaria/tree/18.0/l10n_bg_project_multilang)

Add multilingual support for project task fields in Bulgarian localization

## Description

This module extends the project management functionality in Odoo to provide multilingual support for project task fields in the Bulgarian localization.

The module allows Bulgarian companies to manage their project tasks in Bulgarian language while maintaining the ability to translate to other languages. This is especially useful for international companies based in Bulgaria that work with multinational teams.

The functionality includes multilingual support for task names, descriptions, and other key fields, integrated with the partner multilingual system for consistent translation management.

## Context

**BUSINESS NEED:**

In Bulgaria, many companies work with international partners and clients, which requires project management in multiple languages. The standard project module in Odoo does not provide sufficient multilingual support, especially for the Bulgarian business context.

Main challenges include:
- Need to maintain project documentation in Bulgarian and foreign languages
- Working with multinational teams that require task localization
- Compliance with Bulgarian business standards for documentation

**APPROACH:**

This module solves the problem by extending the standard `project.task` model with multilingual functionality, using established translation patterns from the `partner_multilang` module.

**USEFUL INFORMATION:**

**Related modules:**
- `project`: Core project management module
- `partner_multilang`: Provides multilingual infrastructure for partners
- `l10n_bg`: Bulgarian localization

**Recommended setups:**
- Multi-company environments with Bulgarian localization
- International projects with Bulgarian participation
- Companies working with foreign clients from Bulgaria

## Installation

To install this module, you need to:

1. **Prerequisites:**
   - Odoo 18.0 or newer version
   - Installed `project` module
   - Installed `partner_multilang` module

2. **Installation procedure:**
   - Copy the module to the Odoo addons directory
   - Restart the Odoo server
   - Activate developer mode
   - Go to *Apps* > *Update Apps List*
   - Search for "L10n Bg Project Multilang" and install

3. **Installation verification:**
   - Go to *Project* > *Tasks*
   - When editing a task, you should see translation options for fields

**Important notes:**
- The module requires activated Bulgarian localization
- It's recommended to create a backup before installation
- For installation issues, check Odoo logs for errors

## Configuration

To configure this module, you need to:

1. **Module Installation:**
   - Go to *Apps* > search for "L10n Bg Project Multilang"
   - Click *Install*

2. **Language Activation:**
   - Go to *Settings* > *Users & Companies* > *Languages*
   - Activate desired languages (e.g., English, German, etc.)

3. **Project Configuration:**
   - Go to *Project* > *Configuration* > *Settings*
   - Activate necessary multilingual features

4. **User Permissions Setup:**
   - Go to *Settings* > *Users & Companies* > *Users*
   - Ensure users have project management rights
   - Set preferred language for each user

**Important:** The module requires prior installation of `project` and `partner_multilang` modules.

## Usage

To use this module, you need to:

1. **Creating multilingual tasks:**
   - Go to *Project* > *Tasks*
   - Create a new task or edit an existing one
   - In the task name field, enter the text in Bulgarian
   - Use the translation button next to the field to add translations to other languages

2. **Managing descriptions:**
   - In the *Description* field of the task, enter the detailed description in Bulgarian
   - Add translations for other languages through the translation feature

3. **Viewing in different languages:**
   - Change the user interface language from the top right corner
   - Tasks and their descriptions will be displayed in the selected language
   - If no translation exists, the original text will be shown

4. **Working with teams:**
   - Set different languages for different team members
   - Each user will see tasks in their preferred language
   - Translations are automatically saved when editing

**Note:** The module does not impact the user interface beyond adding translation features to existing task fields.

## Known Issues / Roadmap

Known limitations and future improvements:

**Planned features for next versions:**

- Support for multilingual project stages
- Integration with reporting system for multilingual reports
- Support for multilingual task templates
- Automatic language detection based on client settings
- Integration with web portal for multilingual client access

**Known limitations:**

- Translations are managed manually - no automatic translation
- Some complex fields may not support full multilingual functionality
- Requires developer mode activation for initial setup

**Improvement suggestions:**

- Tools for bulk translation of existing tasks
- Integration with external translation services
- Better support for RTL languages
- Support for multilingual attachments

## Bug Tracker

Bugs are tracked on [GitHub Issues](https://github.com/rosenvladimirov/l10n-bulgaria/issues).
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and welcomed
[feedback](https://github.com/rosenvladimirov/l10n-bulgaria/issues/new?body=module:%20l10n_bg_project_multilang%0Aversion:%2018.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**).

Do not contact contributors directly about support or help with technical issues.

## Credits

### Authors

* Rosen Vladimirov

### Contributors

- Rosen Vladimirov <rosenvladimirov@gmail.com> (https://github.com/rosenvladimirov)

### Financial Support

The development of this module has been financially supported by:

- Bulgarian Odoo user community
- OCA Bulgarian localization project participants

Special thanks to:
- The OCA (Odoo Community Association) team for the infrastructure
- Bulgarian Odoo community for testing and feedback
- Authors of the `partner_multilang` module for the core multilingual architecture

### Maintainers

This module is maintained by Rosen Vladimirov.

[![Rosen Vladimirov](https://avatars0.githubusercontent.com/u/rosenvladimirov?s=80&v=4)](https://github.com/rosenvladimirov)

This module is part of the [l10n-bulgaria](https://github.com/rosenvladimirov/l10n-bulgaria) project.

## History

## 18.0.1.0.0 (2025-09-07)

- [ADD] Initial version of the module for multilingual support of project tasks
- [ADD] Integration with partner_multilang for consistent translation management
- [ADD] Support for multilingual task names
- [ADD] Support for multilingual task descriptions
- [ADD] Bulgarian localization for project tasks
- [ADD] OCA compatibility and standards
