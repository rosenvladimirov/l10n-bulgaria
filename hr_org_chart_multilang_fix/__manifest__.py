{
    "name": "HR Org Chart — Multilang Fix",
    "version": "19.0.1.0.0",
    "license": "AGPL-3",
    "category": "Human Resources",
    "author": "Rosen Vladimirov, Terraros Commerce Ltd.",
    "website": "https://github.com/OCA/l10n-bulgaria",
    "summary": "Resolve translatable JSONB employee names to plain strings "
               "before the hr_org_chart widget renders them.",
    "description": """
HR Org Chart — Multilang Fix
============================

When ``hr.employee.name``/``hr.job.name`` (or related Char fields) is made
translatable by a third-party module (e.g. ``partner_multilang`` + the
Bulgarian multilang stack), Odoo stores the value as a PostgreSQL JSONB column
(``{"en_US": "...", "bg_BG": "..."}``).

The Enterprise ``hr_org_chart`` widget pulls employee data through the
``/hr/get_org_chart`` JSON-RPC route, whose ``_prepare_employee_data``
controller method serialises ``employee.name``/``job.name`` directly into the
response payload. Under certain request contexts (no active ``lang``,
``prefetch_langs`` flag, sudo without lang propagation, etc.), the field
arrives at the JavaScript layer as the raw JSONB dict, and the OWL template
renders it as ``[object Object]``.

This patch module overrides ``_prepare_employee_data`` and resolves every
potentially translatable string field (``name``, ``job_name``, ``job_title``)
to a plain string for the active language, with a defensive fallback to the
first available translation. If the value is already a plain string, the
patch is a no-op.

The fix covers all three form views that mount the widget:
``hr.employee``, ``hr.employee.public``, ``res.users`` — they all share the
same controller endpoint.
""",
    "depends": [
        "hr_org_chart",
    ],
    "data": [],
    "installable": True,
    "auto_install": False,
}
