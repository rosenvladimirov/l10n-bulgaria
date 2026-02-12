#  Part of Odoo. See LICENSE file for full copyright and licensing details.
"""
Monkey-patch ``dict`` with every public ``str`` method so that
translated-field dicts (e.g. {"en_US": "John", "bg_BG": "Иван"})
behave like strings when Odoo code calls ``.lower()``, ``.upper()``, etc.

Each patched method applies the corresponding ``str`` method to every
string value in the dict and returns a **new dict** with the results.
Non-string values are passed through unchanged.
"""

import ctypes
import gc
import logging

_logger = logging.getLogger(__name__)


# ── internal helpers ─────────────────────────────────────────────────

def _get_type_dict(typ):
    """Return the real ``dict`` behind a built-in type's ``mappingproxy``."""
    for ref in gc.get_referents(typ.__dict__):
        if type(ref) is dict:
            return ref
    raise TypeError(f"Cannot access internal dict of {typ!r}")


def _curse(klass, attr, value):
    """Force-set *attr* on a built-in (C-level) type."""
    _get_type_dict(klass)[attr] = value
    ctypes.pythonapi.PyType_Modified(ctypes.py_object(klass))


# ── str-method wrapper factory ───────────────────────────────────────

def _make_dict_str_method(method_name):
    """Return a wrapper that applies ``str.<method_name>`` to every
    string value of *self* and returns a new dict with the results."""

    def wrapper(self, *args, **kwargs):
        return {
            key: getattr(value, method_name)(*args, **kwargs)
            if isinstance(value, str) else value
            for key, value in self.items()
        }

    wrapper.__name__ = wrapper.__qualname__ = method_name
    wrapper.__doc__ = (
        f"Apply ``str.{method_name}()`` to every string value "
        f"and return a new dict with the results."
    )
    return wrapper


# ── apply the patch ──────────────────────────────────────────────────

# Never shadow an existing dict attribute.
_SKIP = frozenset(dir(dict))

_STR_PUBLIC_METHODS = [
    name for name in sorted(dir(str))
    if not name.startswith("_")
    and callable(getattr(str, name))
    and name not in _SKIP
]


def patch_dict():
    """Add every public ``str`` method that ``dict`` doesn't already have."""
    for name in _STR_PUBLIC_METHODS:
        _curse(dict, name, _make_dict_str_method(name))
    _logger.debug(
        "dict monkey-patched with %d str methods: %s",
        len(_STR_PUBLIC_METHODS),
        ", ".join(_STR_PUBLIC_METHODS),
    )


patch_dict()
