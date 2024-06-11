import setuptools

setuptools.setup(
    name='odoo-addons-l10n-bulgaria',
    version='16.0',
    # ...any other setup() keyword
    setup_requires=['setuptools-odoo'],
    namespace_packages= ['odoo.addons'],
    odoo_addons=True,
)