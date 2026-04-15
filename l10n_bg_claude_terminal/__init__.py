# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models as _odoo_models

# Backport of Odoo 20.0 `_explanation` class attribute.
if not hasattr(_odoo_models.Model, "_explanation"):
    _odoo_models.Model._explanation = None

from . import models
from . import tests
