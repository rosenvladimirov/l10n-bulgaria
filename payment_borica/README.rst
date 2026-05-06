============================
Payment Provider: Borica APGW
============================

.. |badge1| image:: https://img.shields.io/badge/maturity-Alpha-red.png
    :alt: Alpha
.. |badge2| image:: https://img.shields.io/badge/licence-LGPL--3-blue.png
    :alt: License: LGPL-3

|badge1| |badge2|

This module integrates the **Borica APGW e-Gateway** (CGI/WWW Forms,
P-OM-41 v4.0) as an Odoo ``payment.provider``. Implements the
**MAC_GENERAL** signing scheme and EMV 3DS 2.x (v2.1 / v2.2) authentication.

**Table of contents**

.. contents::
   :local:

Features
========

* HTML form-redirect flow (TRTYPE=1 — Sale)
* MAC_GENERAL request signing per spec §5.7 (length-prefixed UTF-8 concat,
  RSA-SHA256, hex-encoded P_SIGN)
* MAC_GENERAL response verification per §5.8
* 32-char uppercase-hex NONCE generation
* Sandbox + production endpoint switching via provider state

Configuration
=============

#. Generate an RSA-2048 private key + CSR (per spec §5.2 / §5.3):

   .. code-block:: bash

      openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out merchant.key
      openssl req -new -key merchant.key -out merchant.csr -subj \
        "/C=BG/ST=Sofia/L=Sofia/O=YourCompany/OU=V1800001/CN=yourdomain.bg"

#. ZIP the CSR as ``VNNNNNNN_YYYYMMDD_T.zip`` and submit to your bank.
#. Receive the signed certificate (CER) + Borica public cert from the bank.
#. Install ``payment_borica`` and configure under
   **Accounting → Configuration → Payment Providers → Borica APGW**:

   * Terminal (TID) — 8 chars, e.g. ``V1800001``
   * Merchant ID — 10 chars
   * Merchant Name, URL, Email, Country, GMT, Lang
   * Private Key — paste PEM contents of ``merchant.key``
   * Public Certificate — paste PEM contents of Borica public cert
#. Set state to *Test* for the sandbox terminal, *Enabled* for production.

Sandbox endpoints
-----------------

* Test: ``https://3dsgate-dev.borica.bg/cgi-bin/cgi_link``
* Prod: ``https://3dsgate.borica.bg/cgi-bin/cgi_link``

Sandbox credentials are issued per merchant — there are no public test creds
(unlike myPOS). You need a signed ZIP from your acquirer bank to test.

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/l10n-bulgaria/issues>`_.

Credits
=======

Authors
~~~~~~~

* Rosen Vladimirov

Maintainers
~~~~~~~~~~~

This module is maintained by the OCA.
