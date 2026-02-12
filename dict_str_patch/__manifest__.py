{
    "name": "Dict String Methods Patch",
    "version": "19.0.1.0.0",
    "license": "AGPL-3",
    "category": "Technical",
    "author": "Rosen Vladimirov, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/partner-contact",
    "summary": "Monkey-patch dict with all public str methods for translated JSONB fields.",
    "description": """
Dict String Methods Patch
=========================

Monkey-patches Python's built-in ``dict`` type with every public ``str``
method (``lower``, ``upper``, ``replace``, ``strip``, etc.).

When called on a dict, each method applies the corresponding string
operation to every string value and returns a new dict with the results.
Non-string values are passed through unchanged.

This is essential for Odoo 19's ``translate=True`` Char/Text fields that
store values as JSONB dicts (e.g. ``{"en_US": "John", "bg_BG": "Иван"}``).
Without this patch, any code that calls string methods on those field
values will crash with ``AttributeError``.

**Example**::

    d = {"en_US": "Hello World", "bg_BG": "Здравей Свят"}
    d.lower()   # → {"en_US": "hello world", "bg_BG": "здравей свят"}
    d.upper()   # → {"en_US": "HELLO WORLD", "bg_BG": "ЗДРАВЕЙ СВЯТ"}
    d.replace("Hello", "Hi")  # → {"en_US": "Hi World", "bg_BG": "Здравей Свят"}

Chaining works naturally::

    d.lower().strip()  # → {"en_US": "hello world", "bg_BG": "здравей свят"}
    """,
    "depends": [
        "base",
    ],
    "data": [],
    "demo": [],
    "installable": True,
    "auto_install": False,
}
