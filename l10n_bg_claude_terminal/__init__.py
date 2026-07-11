# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models as _odoo_models

# Backport of Odoo 20.0 `_explanation` class attribute to 16/17/18/19.
# Guard via hasattr so that on 20.0 (where Odoo SA defines it in orm/models.py)
# this becomes a no-op — zero conflict, forward-compatible.
if not hasattr(_odoo_models.Model, "_explanation"):
    _odoo_models.Model._explanation = None

from . import models
from . import wizards
