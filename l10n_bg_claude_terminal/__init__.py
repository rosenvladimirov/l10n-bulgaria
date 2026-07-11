# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models as _odoo_models

# Backport of Odoo 20.0 `_explanation` class attribute.
if not hasattr(_odoo_models.Model, "_explanation"):
    _odoo_models.Model._explanation = None

from . import models
from . import wizards
from . import tests
