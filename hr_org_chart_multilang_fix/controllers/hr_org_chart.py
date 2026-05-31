from odoo.addons.hr_org_chart.controllers.hr_org_chart import HrOrgChartController
from odoo.http import request

# Полета в _prepare_employee_data резултата, които идват от Char колони
# и могат да бъдат JSONB dict-ове при translate=True override.
_TRANSLATABLE_KEYS = ("name", "job_name", "job_title")


def _resolve_translatable(value, lang):
    """Resolve a value that may be a translatable JSONB dict to a plain string.

    Defensive: ако `value` вече е стринг (или None / друг тип), връща го непроменено.
    Ако е dict, опитва текущия `lang`, после `en_US`, после първата налична стойност.
    """
    if not isinstance(value, dict):
        return value
    if lang and lang in value:
        return value[lang]
    if "en_US" in value:
        return value["en_US"]
    return next(iter(value.values()), "")


class HrOrgChartControllerPatched(HrOrgChartController):

    def _prepare_employee_data(self, employee):
        data = super()._prepare_employee_data(employee)
        lang = request.env.context.get("lang") or request.env.user.lang or "en_US"
        for key in _TRANSLATABLE_KEYS:
            if key in data:
                data[key] = _resolve_translatable(data[key], lang)
        return data
