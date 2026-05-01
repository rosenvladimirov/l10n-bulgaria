# Odoo discovers tests by importing this package and iterating its
# `test_*` submodules (see `odoo/tests/loader.py:_get_tests_modules`).
#
# After the proxy refactor, the driver-level tests live in the
# `Odoo.ErpNet.FP` repo. The Odoo addon only retains TransactionCase
# tests for ORM behaviour that doesn't depend on the proxy.
try:
    import odoo  # noqa: F401
except ImportError:
    pass
else:
    from . import test_orm_product_template
