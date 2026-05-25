#!/usr/bin/env python3
# Copyright 2026 Rosen Vladimirov
# License AGPL-3 or later (https://www.gnu.org/licenses/agpl).
"""Помощен скрипт за генериране на пълния seed на отпадъчните кодове.

Изтегля Приложение 1 на Наредба №2/2014 от moew.government.bg, парсва PDF
текста и извежда XML-съвместим със seed на l10n_bg_waste_base.

Употреба
--------
    python3 fetch_full_seed.py > ../data/waste_code_data_full.xml

После: добави `data/waste_code_data_full.xml` в `__manifest__.py` `data`
списъка и направи `-u l10n_bg_waste_base` за да го импортираш. ЗАПАЗИ
текущите xml_id-та (`waste_code_XX_YY_ZZ`) за съвместимост.

Зависимости
-----------
- pdftotext (poppler-utils)
- requests или urllib (стандартна библиотека)

Status: скеле — реалното parsing-овото е TODO. moew.government.bg засега
върна HTML/anti-bot страница, не PDF. Алтернатива: ползвай European Waste
Catalogue (EWC) от eur-lex.europa.eu — структурата е идентична с
българската транспозиция в Наредба №2/2014.

EWC reference: Commission Decision 2000/532/EC consolidated.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_PDF_URL = (
    "https://www.moew.government.bg/static/media/ups/tiny/"
    + urllib.parse.quote(
        "НАРЕДБА 2 от 2014 г. за класификация на отпадъците.pdf",
        safe="/",
    )
)

CODE_RX = re.compile(r"^\s*([0-9]{2})\s+([0-9]{2})\s+([0-9]{2})(\*?)\s+(.+?)\s*$")


def fetch(url: str, dst: Path) -> None:
    """Изтегля URL към dst (с по-сериозен UA срещу basic anti-bot)."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        dst.write_bytes(r.read())


def pdftotext(pdf: Path, txt: Path) -> None:
    subprocess.run(["pdftotext", "-layout", str(pdf), str(txt)], check=True)


def parse_codes(txt: Path):
    """Връща списък от tuples (code_with_space, name, hazardous_bool).

    Очакван формат на ред (примерен): '15 01 02   Опаковки от пластмаси'.
    """
    results = []
    for line in txt.read_text(encoding="utf-8", errors="replace").splitlines():
        m = CODE_RX.match(line)
        if not m:
            continue
        a, b, c, star, name = m.groups()
        code = f"{a} {b} {c}{star}"
        results.append((code, name.strip(), bool(star)))
    return results


def to_xml(codes) -> str:
    """Превръща списък код→име в Odoo data XML формат."""
    out = ['<?xml version="1.0" encoding="UTF-8"?>', "<odoo noupdate=\"1\">"]
    for code, name, hazardous in codes:
        xmlid = "waste_code_" + code.replace(" ", "_").replace("*", "")
        out.append(f'    <record id="{xmlid}" model="l10n.bg.waste.code">')
        out.append(f'        <field name="code">{code}</field>')
        # XML-безопасно ескейпване на name
        safe = name.replace("&", "&amp;").replace("<", "&lt;")
        out.append(f'        <field name="name">{safe}</field>')
        if hazardous:
            out.append('        <field name="is_hazardous" eval="True"/>')
        out.append("    </record>")
    out.append("</odoo>")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate full waste code seed XML.")
    parser.add_argument("--url", default=DEFAULT_PDF_URL, help="PDF URL")
    parser.add_argument("--cache", default="/tmp/naredba2.pdf", help="local cache path")
    parser.add_argument("--out", default="-", help="output XML path (- = stdout)")
    args = parser.parse_args()

    cache = Path(args.cache)
    txt = cache.with_suffix(".txt")
    if not cache.exists():
        print(f"download {args.url} ...", file=sys.stderr)
        fetch(args.url, cache)
    print(f"pdftotext {cache} -> {txt}", file=sys.stderr)
    pdftotext(cache, txt)
    codes = parse_codes(txt)
    print(f"parsed {len(codes)} codes", file=sys.stderr)
    if not codes:
        print("WARNING: 0 codes parsed — adjust CODE_RX or check PDF format", file=sys.stderr)
        return 1
    xml = to_xml(codes)
    if args.out == "-":
        sys.stdout.write(xml)
    else:
        Path(args.out).write_text(xml, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
