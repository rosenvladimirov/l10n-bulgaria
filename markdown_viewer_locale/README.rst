
=========================
Markdown Viewer Locale
=========================

.. |badge1| image:: https://img.shields.io/badge/licence-LGPL--3-blue.svg
    :target: http://www.gnu.org/licenses/lgpl-3.0-standalone.html
    :alt: License: LGPL-3

|badge1|

View localized Markdown files based on user language.

**Key Features:**

* Automatic loading of Markdown files according to user language
* Fallback to main file if localization is missing
* Integrated content search function
* Syntax highlighting for code blocks
* Full-screen modal window

Usage
=====

Method 1: Snippet Template
---------------------------

After installing the module, add the snippet to your views:

.. code-block:: xml

    <t t-call="markdown_viewer_locale.markdown_snippet">
        <t t-set="md_file" t-value="'readme.md'"/>
        <t t-set="md_module" t-value="'your_module_name'"/>
    </t>

Method 2: Direct Link
---------------------

Use a direct link with data attributes:

.. code-block:: xml

    <a href="#" class="o_show_markdown"
       data-md-file="readme.md"
       data-md-module="your_module_name"
       title="View Documentation">
        <i class="fa fa-book fa-lg"></i>
    </a>

Method 3: Icon in Form (Recommended)
-------------------------------------

To add a documentation icon to an Odoo form:

.. code-block:: xml

    <odoo>
        <record id="view_move_form_inherit_md_icon" model="ir.ui.view">
            <field name="name">account.move.form.md.icon</field>
            <field name="model">account.move</field>
            <field name="inherit_id" ref="account.view_move_form"/>
            <field name="arch" type="xml">
                <!-- Insert icon inside the form -->
                <xpath expr="//form" position="inside">
                    <div class="o_md_icon_container">
                        <i class="fa fa-book o_show_markdown"
                           title="Documentation"
                           data-md-file="l10n_bg_tax_admin_documentation.md"
                           data-md-module="l10n_bg_tax_admin"></i>
                    </div>
                </xpath>
            </field>
        </record>
    </odoo>

**Important:** Add CSS styles to position the icon:

.. code-block:: css

    .o_md_icon_container {
        position: absolute;
        top: 10px;
        right: 20px;
        z-index: 1000;
    }

    .o_md_icon_container .fa-book {
        font-size: 24px;
        color: #4caf50;
        cursor: pointer;
        transition: color 0.3s;
    }

    .o_md_icon_container .fa-book:hover {
        color: #45a049;
    }

File Structure
==============

Create Markdown files in the following structure:

.. code-block:: text

    your_module/
    └── static/
        └── src/
            └── md/
                ├── readme.md                              # Main file (fallback)
                ├── readme.bg.md                           # Bulgarian version
                ├── readme.en.md                           # English version
                ├── l10n_bg_tax_admin_documentation.md     # Documentation (fallback)
                ├── l10n_bg_tax_admin_documentation.bg.md  # Documentation (BG)
                └── l10n_bg_tax_admin_documentation.en.md  # Documentation (EN)

The module will automatically load the file according to the user's language (e.g., for ``bg_BG`` it will look for ``l10n_bg_tax_admin_documentation.bg.md``).

Functionality Check
===================

**Step 1: Check Files**

Make sure Markdown files are in the correct location:

.. code-block:: bash

    # Check file structure
    ls -la your_module/static/src/md/

You should see the files:

.. code-block:: text

    l10n_bg_tax_admin_documentation.md
    l10n_bg_tax_admin_documentation.bg.md
    l10n_bg_tax_admin_documentation.en.md

**Step 2: Restart Odoo**

.. code-block:: bash

    # Restart server and update module
    odoo-bin -u markdown_viewer_locale,l10n_bg_tax_admin

**Step 3: Clear Browser Cache**

Press ``Ctrl+Shift+R`` (or ``Cmd+Shift+R`` on Mac) to clear the cache.

**Step 4: Open Form**

Open an ``account.move`` form and look for the 📚 icon in the top right corner.

**Step 5: Testing**

1. Click on the 📚 icon
2. A modal window with documentation should open
3. Check if the correct language is loaded (according to ``bg_BG``, ``en_US``, etc.)
4. Test the search function

**Step 6: Check Browser Console**

Open Developer Tools (F12) and check for errors:

.. code-block:: javascript

    // You should see files loading
    // If there's a 404 error, check the paths

**Troubleshooting**

If the icon doesn't show:

1. **Check CSS styles** - Add ``.o_md_icon_container`` styles to CSS file
2. **Check XPath** - Make sure ``//form`` exists in the view
3. **Check class** - It should be ``.o_show_markdown``, not ``.o_show_markdown_dropdown``
4. **Check assets** - Make sure JS and CSS files are added to the manifest

If the modal doesn't open:

1. **Check console** - Look for JavaScript errors
2. **Check path** - Make sure ``data-md-module`` and ``data-md-file`` are correct
3. **Check files** - Make sure Markdown files exist

If you see a 404 error:

.. code-block:: text

    GET http://localhost:8069/l10n_bg_tax_admin/static/src/md/l10n_bg_tax_admin_documentation.bg.md 404

This means:

* The file is missing from the specified location
* The module name is incorrect in ``data-md-module``
* The file name is incorrect in ``data-md-file``

Supported Languages
===================

The module supports all languages, using the first part of the locale code:

* ``bg_BG`` → ``documentation.bg.md``
* ``en_US`` → ``documentation.en.md``
* ``de_DE`` → ``documentation.de.md``
* ``fr_FR`` → ``documentation.fr.md``
* etc.

Search Function
===============

The built-in search function allows users to quickly find information in the documentation.
Found texts are highlighted with a yellow background.

Requirements
============

* Odoo 16.0+
* Bootstrap 5
* marked.js library (included)
* highlight.js library (included)

Configuration
=============

No additional configuration required. The module works immediately after installation.

Bug Tracker
===========

If you find any issues, please report them in GitHub Issues.

Authors
=======

* Your company/name

Contents
========

* ``static/lib/marked.min.js``: Markdown parser
* ``static/lib/highlight.min.js``: Syntax highlighting for code
* ``static/src/js/markdown_popup.js``: JavaScript component
* ``static/src/css/markdown_popup.css``: Styles
* ``static/src/xml/markdown_popup.xml``: OWL template
* ``views/markdown_snippet.xml``: Snippet for adding to views

Sample Documentation
====================

Create ``l10n_bg_tax_admin_documentation.en.md``:

.. code-block:: markdown

    # Tax Administration Documentation

    ## Introduction

    This module provides functionality for working with the Tax Authority.

    ## Features

    * Generate XML files
    * Data validation
    * Submission to Tax Authority

    ## Sample Code

    ```python
    def generate_xml(self):
        # Generate XML
        return xml_content
    ```

License
=======

LGPL-3

Credits
=======

This module uses the following libraries:

* `marked.js <https://marked.js.org/>`_ - MIT License
* `highlight.js <https://highlightjs.org/>`_ - BSD License
