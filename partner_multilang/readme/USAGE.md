
To use this module, you need to:

**Basic Usage:**

1. Enable transliteration for desired languages in Settings → Translations → Languages
2. Create or edit a partner in a language with transliteration enabled
3. Enter the name and address in the original script (e.g., Cyrillic)
4. The module automatically creates a transliterated version in English

**Multi-Language Search:**

Search works across all language translations. You can search for partners using either the original or transliterated name.

**Extend to Custom Models:**

To add transliteration support to your custom models:

```python
from odoo import api, fields, models

class CustomModel(models.Model):
    _inherit = ['your.model', 'res.transliterate.mixin']
    _name = "your.model"

    name = fields.Char(translate=True)

    @api.model
    def _get_transliterate_fields(self):
        res = super()._get_transliterate_fields()
        return res + ['name']
```
