# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
"""Чисти функции за кодовете по КН — без зависимост от ORM.

Един код на три нива:
    HS6     = КН8[:6]
    КН8     = код[:8]
    TARIC10 = кодът, ако е 10 цифри

Източникът на истината е полето на варианта: TARIC10, когато е известен,
иначе КН8. Нищо тук не „допълва“ код с нули — HS6 + „00“ или КН8 + „00“
не гарантират съществуващ код (виж REPORT.md, т. 1, извод 3).
"""
import re

# Разделители, които хората пишат в кода („4817 10 00“, „4817.10.00“) —
# махаме само тях; всичко друго прави кода невалиден, не се „поправя“.
_SEPARATORS_RE = re.compile(r"[\s. ]+")
_VALID_RE = re.compile(r"^(\d{8}|\d{10})$")

SAFT_SERVICE_CODE = "00000000"
SAFT_NOT_APPLICABLE_CODE = "0"


def normalize_commodity_code(value):
    """Маха интервалите и точките; не пипа нищо друго.

    Връща False за празна стойност, за да не се записва празен низ.
    """
    if not value:
        return False
    cleaned = _SEPARATORS_RE.sub("", str(value))
    return cleaned or False


def is_valid_commodity_code(value):
    """Само цифри и дължина точно 8 или 10."""
    return bool(value) and bool(_VALID_RE.match(value))


def split_commodity_code(value):
    """Връща (cn8, hs6, taric10) за валиден код или ('', '', '')."""
    if not is_valid_commodity_code(value):
        return "", "", ""
    cn8 = value[:8]
    return cn8, cn8[:6], value if len(value) == 10 else ""


def digits_candidate(value):
    """Цифрите на заварена стойност (миграция): връща ги само при 8 или 10.

    Използва се за заварени hs_code/taric_code, в които може да има
    интервали, точки или тирета. Ако след махането на всичко нецифрово
    остават 8 или 10 цифри — това е кандидат; иначе False.
    """
    if not value:
        return False
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return digits if len(digits) in (8, 10) else False
