# Copyright 2026 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""CFX message extractors — малки плъгове по CFX message type.

Старият ipc-cfx SDK (proton-amqp `lib.cfx`) вече превръща всяко CFX-IPC
съобщение в Python клас (UnitsInspected, StationStateChanged, …) и дава
`content_dict` — пълния парснат JSON. Проксито го форуърдва към Odoo
като `event["data"]` (целият CFX MessageBody).

Тук извличаме РЕАЛНИТЕ данни от този dict в структуриран вид, готов за
инжектиране в cfx.machine.stat + child таблиците (cfx.inspection.*), за
да се виждат в справката/dashboard-а — а не да тлеят в payload_json.

Дизайн = plugin registry: всеки extractor е малка функция, регистрирана
по CFX message name чрез @cfx_extractor(...). Добавяне на нова машина/
съобщение = още една малка функция, БЕЗ да пипаме controller-а. Всеки
extractor приема CFX body dict и връща `ExtractResult`:

    summary  — dict с полета за cfx.machine.stat (плоски скалари)
    units    — list от dict-ове за cfx.inspection.unit; всеки носи
               вложени `defects` и `measurements` за child create-ите

Всичко е permissive (CFX field-сетовете варират по машина) — липсващо
поле дава None/0, не грешка.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

# ─── Registry ──────────────────────────────────────────────────────
# message_name → extractor callable. Пълни се от декоратора при import.
CFX_EXTRACTORS: dict[str, Callable[[dict], "ExtractResult"]] = {}


def cfx_extractor(*message_names: str):
    """Регистрирай функция като extractor за един/повече CFX message-а."""
    def deco(fn):
        for name in message_names:
            CFX_EXTRACTORS[name] = fn
        return fn
    return deco


class ExtractResult:
    """Структуриран резултат от extractor: summary + inspection units."""
    __slots__ = ("summary", "units")

    def __init__(self, summary: Optional[dict] = None,
                 units: Optional[list] = None):
        self.summary: dict = summary or {}
        self.units: list = units or []


def extract(message_name: str, data: dict) -> Optional[ExtractResult]:
    """Пусни регистрирания extractor за `message_name`, ако има такъв."""
    fn = CFX_EXTRACTORS.get(message_name)
    if not fn or not isinstance(data, dict):
        return None
    return fn(data)


# ─── Помощни (permissive key access) ───────────────────────────────

def _get(d: dict, *keys, default=None):
    """Върни първата налична (не-None) стойност измежду `keys`."""
    if not isinstance(d, dict):
        return default
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def _flt(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _int(v) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _operator(inspector: dict) -> str:
    """Човеко-четимо име на инспектора от CFX Operator структурата."""
    if not isinstance(inspector, dict):
        return ""
    first = _get(inspector, "FirstName", "firstName", default="") or ""
    last = _get(inspector, "LastName", "lastName", default="") or ""
    name = (f"{first} {last}").strip()
    return name or _get(
        inspector, "OperatorIdentifier", "operatorIdentifier",
        "LoginName", default="") or ""


# ─── Measurement $type → нормализиран тип ──────────────────────────
_MEAS_TYPE_MAP = {
    "SolderPasteMeasurement": "spi_paste",
    "InspectionMeasurementLean": "spi_lean",
    "OffsetMeasurement": "offset",
}


def _measurement_type(raw_type: str) -> str:
    """`CFX.Structures.SolderPasteInspection.SolderPasteMeasurement, CFX`
    → `spi_paste`. Fallback = последният сегмент преди запетаята."""
    if not raw_type:
        return "generic"
    core = str(raw_type).split(",", 1)[0].rsplit(".", 1)[-1].strip()
    return _MEAS_TYPE_MAP.get(core, core or "generic")


def _parse_measurement(m: dict, inspection_name: str) -> dict:
    """CFX Measurement структура → cfx.inspection.measurement vals.

    Покрива SolderPasteMeasurement (SPI), OffsetMeasurement (AOI offset)
    и InspectionMeasurementLean — общите числови оси в няколко колони,
    останалото в raw. Vol/DX/DY се мапват еднакво за трите типа.
    """
    return {
        "inspection_name": inspection_name or "",
        "meas_type": _measurement_type(_get(m, "$type", "type", default="")),
        "measurement_name": _get(m, "MeasurementName", "measurementName",
                                 default="") or "",
        "crds": _get(m, "CRDs", "crds", default="") or "",
        "result": (_get(m, "Result", "result", default="") or "").lower(),
        "pos_x": _flt(_get(m, "X", "x")),
        "pos_y": _flt(_get(m, "Y", "y")),
        "pos_z": _flt(_get(m, "Z", "z")),
        "dev_x": _flt(_get(m, "DX", "dx")),
        "dev_y": _flt(_get(m, "DY", "dy")),
        "volume": _flt(_get(m, "Vol", "vol", "Volume")),
    }


def _parse_defect(d: dict, inspection_name: str) -> dict:
    """CFX Defect структура → cfx.inspection.defect vals."""
    comp = _get(d, "ComponentOfInterest", "componentOfInterest", default={}) or {}
    return {
        "inspection_name": inspection_name or "",
        "defect_code": _get(d, "DefectCode", "defectCode", default="") or "",
        "defect_category": _get(d, "DefectCategory", "defectCategory",
                                default="") or "",
        "description": _get(d, "Description", "description", default="") or "",
        "reference_designator": _get(
            comp, "ReferenceDesignator", "referenceDesignator", default="") or "",
        "part_number": _get(comp, "PartNumber", "partNumber", default="") or "",
        "priority": _int(_get(d, "Priority", "priority")),
        "confidence_level": _flt(_get(d, "ConfidenceLevel", "confidenceLevel")),
    }


def _parse_unit(unit: dict, is_panel: bool = False) -> dict:
    """CFX InspectedUnit / InspectedPanel → cfx.inspection.unit vals с
    вложени `defects` + `measurements` (flatten през всички Inspections).
    """
    inspections = _get(unit, "Inspections", "inspections", default=[]) or []
    defects: list[dict] = []
    measurements: list[dict] = []
    passed = failed = 0
    for insp in inspections:
        if not isinstance(insp, dict):
            continue
        iname = _get(insp, "InspectionName", "inspectionName", default="") or ""
        result = (_get(insp, "Result", "result", default="") or "").lower()
        if result == "passed":
            passed += 1
        elif result == "failed":
            failed += 1
        for d in _get(insp, "DefectsFound", "defectsFound", default=[]) or []:
            if isinstance(d, dict):
                defects.append(_parse_defect(d, iname))
        for m in _get(insp, "Measurements", "measurements", default=[]) or []:
            if isinstance(m, dict):
                measurements.append(_parse_measurement(m, iname))
    overall = (_get(unit, "OverallResult", "overallResult", default="")
               or "").lower()
    return {
        "unit_identifier": _get(unit, "UnitIdentifier", "unitIdentifier",
                                default="") or "",
        "unit_position": _int(_get(unit, "UnitPositionNumber",
                                   "unitPositionNumber")),
        "overall_result": overall or ("passed" if not failed else "failed"),
        "is_panel": is_panel,
        "inspection_count": len(inspections),
        "inspections_passed": passed,
        "inspections_failed": failed,
        "defects": defects,
        "measurements": measurements,
    }


# ─── AOI / SPI: UnitsInspected ─────────────────────────────────────

@cfx_extractor("UnitsInspected")
def extract_units_inspected(data: dict) -> ExtractResult:
    """PARMI SPI/AOI `UnitsInspected` → пълни inspection данни.

    Покрива и трите CFX варианта: InspectedUnits[] (unit-level), плюс
    InspectedPanel (panel-level с Fiducials/PCBVariant). Извлича метод,
    рецепта, инспектор + всеки unit с неговите defects и measurements.
    """
    units_raw = _get(data, "InspectedUnits", "inspectedUnits", default=[]) or []
    units: list[dict] = [
        _parse_unit(u) for u in units_raw if isinstance(u, dict)]

    # Panel-level инспекция (AOI на цял панел) → един "panel" unit.
    panel = _get(data, "InspectedPanel", "inspectedPanel", default=None)
    if isinstance(panel, dict):
        units.append(_parse_unit(panel, is_panel=True))

    units_total = len(units)
    units_passed = sum(1 for u in units if u["overall_result"] == "passed")
    units_failed = sum(1 for u in units if u["overall_result"] == "failed")
    defects_total = sum(len(u["defects"]) for u in units)
    meas_total = sum(len(u["measurements"]) for u in units)

    summary = {
        "inspection_method": _get(data, "InspectionMethod", "inspectionMethod",
                                  default="") or "",
        "recipe_name": _get(data, "RecipeName", "recipeName", default="") or "",
        "recipe_revision": _get(data, "RecipeRevision", "recipeRevision",
                                default="") or "",
        "operator_name": _operator(
            _get(data, "Inspector", "inspector", default={})),
        "units_total": units_total,
        "units_passed": units_passed,
        "units_failed": units_failed,
        "defects_total": defects_total,
        "measurements_total": meas_total,
        # Общите числови метрики на cfx.machine.stat (за pivot-ите):
        "quantity": float(units_total),
        "defect_count": defects_total,
    }
    return ExtractResult(summary=summary, units=units)


# ─── Station state (ресурс) ────────────────────────────────────────

@cfx_extractor("StationStateChanged")
def extract_station_state(data: dict) -> ExtractResult:
    """StationStateChanged → station state в summary (без child редове)."""
    new_state = _get(data, "NewState", "newState", "State", "state", default={})
    if isinstance(new_state, dict):
        state_txt = _get(new_state, "State", "state",
                         "WorkStationState", default="") or ""
    else:
        state_txt = str(new_state or "")
    return ExtractResult(summary={
        "station_state": state_txt,
        "measured_value": _flt(_get(data, "OverallEquipmentEffectiveness",
                                    "oee")),
        "unit": "%" if _get(data, "OverallEquipmentEffectiveness") else "",
    })
