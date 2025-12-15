=================================
ErpNet.FP Fiscal Printer for Odoo
=================================

.. |badge1| image:: https://img.shields.io/badge/maturity-Beta-yellow.png
    :target: https://odoo-community.org/page/development-status
    :alt: Beta
.. |badge2| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3
.. |badge3| image:: https://img.shields.io/badge/odoo-18.0-blue.png
    :target: https://github.com/OCA/l10n-bulgaria
    :alt: Odoo 18.0

|badge1| |badge2| |badge3|

Full integration with Bulgarian fiscal printers through ErpNet.FP server for Odoo 18 Point of Sale.

This module provides:

- Direct browser-to-printer communication for fiscal receipts
- Backend support for administrative operations (Z/X reports, cash operations)
- Automatic Z-report generation on session closing
- Real-time printer status monitoring
- Bulgarian tax group mapping (А, Б, В, Г)
- Cash drawer operations

**Table of contents**

.. contents::
   :local:

Features
========

POS Frontend
------------

- Fiscal receipt printing - Direct communication from browser to ErpNet.FP server
- Automatic fallback - Falls back to standard printing on error
- Tax group mapping - Automatic mapping of Bulgarian tax groups
- Payment type detection - Automatic cash/card detection
- Receipt number tracking - Saves fiscal receipt number and fiscal memory serial

Backend Operations
------------------

- X Reports - Intermediate reports without resetting
- Z Reports - Daily reports with reset (mandatory before closing)
- Automatic Z reports - Scheduled Z reports via cron
- Cash operations - Deposit and Withdraw
- Additional operations - Duplicate receipts, journal info, status monitoring

POS Session Integration
-----------------------

- Session-level operations - X/Z reports directly from POS session
- Automatic Z on close - Optional automatic Z report when closing session
- Session validation - Prevents closing without Z report
- History tracking - Tracks all fiscal operations in session

Configuration
=============

ErpNet.FP Server Setup
----------------------

Install and configure ErpNet.FP server using Docker::

    docker run -d --name erpnetfp -p 8001:8001 -v /dev/usb:/dev/usb --privileged rosenvladimirov/erpnetfp:latest

Or download from: https://github.com/erpnet/ErpNet.FP

Odoo Configuration
------------------

Step 1: Configure Fiscal Printer Device
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Go to: Point of Sale > Configuration > Fiscal Printers > Devices

- Click Create
- Fill in:

  - Name: "Tremol FP-01"
  - Host: "http://localhost:8001"
  - Printer ID: "FP_12345"
  - SSL Verify: Disable for self-signed certificates
  - Timeout: 30 seconds
  - Retry Count: 3

Step 2: Configure Automatic Z Reports
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Enable Automatic Z Report
- Set Z Report Hour: 23
- Set Z Report Minute: 59

Step 3: Configure POS Terminal
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Go to: Point of Sale > Configuration > Point of Sale

- Select your POS
- Go to Devices tab
- Set Fiscal Printer
- Enable Automatic Z Report on Close

Step 4: Configure Tax Groups
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Go to: Accounting > Configuration > Tax Groups

Set Tax Group for Fiscal Printer:

- А = VAT 0%
- Б = VAT 20%
- В = VAT 20%
- Г = VAT 9%

Usage
=====

Fiscal Receipt Printing
------------------------

When completing a sale in POS:

1. Add products to cart
2. Click Payment
3. Select payment method
4. Click Validate
5. System automatically prints fiscal receipt

No manual intervention needed!

X Report
--------

During session (no reset):

- Go to: Point of Sale > Dashboard > Sessions
- Open your active session
- Click X Report button
- Report is printed on fiscal printer

Z Report
--------

Manual Z Report:

- Go to: Point of Sale > Dashboard > Sessions
- Open your session
- Click Z Report button
- Confirm the dialog
- Session can now be closed

Automatic Z Report:

- Configured in Fiscal Printer Device
- Runs via cron at specified time
- Or automatically on session close

Cash Operations
---------------

Deposit::

    Open session > Click Служебно въведени > Enter amount > Execute

Withdraw::

    Open session > Click Служебно изведени > Enter amount > Execute

Printer Status
--------------

View printer status and history:

- Go to: Point of Sale > Configuration > Fiscal Printers > Devices
- Open a device
- See Current Status and Status History
- Click Update Status to refresh

Technical Details
=================

Architecture
------------

Hybrid Approach:

- Receipts → JavaScript → ErpNet.FP (direct, no backend)
- Reports → Python → ErpNet.FP (backend operations)

Why?

- Receipts are high-frequency → Direct communication avoids backend bottleneck
- Reports are low-frequency → Backend provides better error handling

Data Flow
---------

Fiscal Receipt:

1. POS Frontend prepares receipt data
2. JavaScript sends POST to ErpNet.FP
3. ErpNet.FP prints on fiscal device
4. Returns receipt number
5. JavaScript saves to order
6. Backend persists on sync

Z Report:

1. User clicks Z Report in session
2. Python calls print_z_report()
3. Backend sends POST to ErpNet.FP
4. Returns result with fiscal data
5. Session marked as Z Report Printed

API Reference
-------------

Python Methods
~~~~~~~~~~~~~~

fiscal.printer.device:

- print_x_report() - X report
- print_z_report() - Z report
- print_withdraw(amount) - Cash withdraw
- print_deposit(amount) - Cash deposit
- print_duplicate() - Duplicate last receipt
- get_printer_status() - Get status
- open_cash_drawer() - Open drawer

pos.session:

- action_print_x_report() - X report from session
- action_print_z_report() - Z report from session
- action_fiscal_withdraw() - Open withdraw wizard
- action_fiscal_deposit() - Open deposit wizard

JavaScript Methods
~~~~~~~~~~~~~~~~~~

ReceiptScreen (patched):

- doFullPrint() - Overridden for fiscal printing
- _prepareFiscalReceiptData(order, pos) - Prepare receipt JSON
- _getTaxGroup(line, pos) - Map tax group
- _getPaymentType(payment) - Detect payment type
- _sendToFiscalPrinter(url, printerId, data) - Send to ErpNet.FP

Known Issues
============

- CORS may block requests if ErpNet.FP not on same domain
- Self-signed SSL certificates require ssl_verify=False
- Browser console shows fetch errors on printer offline

Roadmap
=======

- Add support for refund receipts
- Implement duplicate receipt from POS UI
- Add printer status widget in POS interface
- Support for multiple printers per POS
- Fiscal memory download functionality

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/rosenvladimirov/l10n-bulgaria/issues>`_.

In case of trouble, please check there if your issue has already been reported.

Credits
=======

Authors
-------

- Rosen Vladimirov
- Terraros Commerce Ltd.

Contributors
------------

- Rosen Vladimirov <vladimirov.rosen@gmail.com>

Maintainers
-----------

This module is maintained by the OCA.

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

This module is part of the `OCA/l10n-bulgaria <https://github.com/OCA/l10n-bulgaria>`_ project on GitHub.

You are welcome to contribute.
