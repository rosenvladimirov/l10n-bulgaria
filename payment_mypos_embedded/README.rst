=====================================
Payment Provider: myPOS — Embedded
=====================================

.. |badge1| image:: https://img.shields.io/badge/maturity-Alpha-red.png
    :alt: Alpha
.. |badge2| image:: https://img.shields.io/badge/licence-LGPL--3-blue.png
    :alt: License: LGPL-3

|badge1| |badge2|

Complementary on-site checkout flow for ``payment_mypos``. Instead of
redirecting the shopper to the myPOS hosted page, the myPOS Embedded
SDK mounts a branded iFrame directly in the Odoo checkout.

**Table of contents**

.. contents::
   :local:

How it differs from the redirect flow
=====================================

* **No client-side RSA signature.** The Embedded SDK only carries
  ``sid`` / ``walletNumber`` / ``keyIndex``. Security comes entirely
  from the signed server-to-server ``urlNotify`` callback, which
  ``payment_mypos`` already verifies (``/payment/mypos/notify`` +
  ``_mypos_verify``).
* **Schemes:** Visa, Visa Electron, Mastercard, Maestro. Apple Pay /
  Google Pay are **not** available in Embedded checkout.
* **Conversion:** the shopper never leaves the site.

Configuration
=============

#. Install ``payment_mypos_embedded`` (pulls in ``payment_mypos``)
#. Open the myPOS payment provider
#. Set **myPOS Checkout Flow** = *Embedded iFrame (on-site)*

All other configuration (Store ID, Wallet, Key Index, Application /
Partner ID, wallet credentials) is inherited from ``payment_mypos``.

Testing
=======

Server-side parameter building is unit-tested
(``tests/test_embedded_params.py``). The iFrame mount itself can only
be validated end-to-end in a real browser against the myPOS sandbox —
unit tests deliberately do not fake the SDK.

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/OCA/l10n-bulgaria/issues>`_.

Credits
=======

Authors: Rosen Vladimirov. Maintained by the OCA.
