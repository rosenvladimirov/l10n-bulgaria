# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Bulgaria - Employee Certifications",
    "summary": """
        Certification skill types required by Bulgarian regulations: electrical
        safety qualification groups, welding competence and ISO 9606 welder
        qualification, forklift operator competence.""",
    "description": """
Bulgaria - Employee Certifications
==================================

Ships three certification skill types (Employees › Training › Certifications),
each with its own skills and levels, following the Bulgarian regulations:

* **Electrical Safety** — qualification group I–V under the Health and Safety
  Rules for Work on Electrical Equipment up to 1000 V (Art. 11, Art. 27).
* **Welding** — welding competence certificate under Ordinance No. 7/2002
  (degrees: fillet welds, plate, pipe) and welder qualification under
  BDS EN ISO 9606-1 / 9606-2.
* **Forklift Trucks** — operator competence under Ordinance No. 1/2006
  (groups I–III).

Without a skill type flagged as a certification, the "New" button on the
Certifications list saves an employee skill without a skill and the database
rejects it. The records are ``noupdate``: once installed they belong to the
company and an upgrade does not overwrite local changes.
    """,
    "version": "19.0.1.0.0",
    "development_status": "Beta",
    "category": "Human Resources/Employees",
    "license": "LGPL-3",
    "author": "Rosen Vladimirov, Terraros Commerce Ltd., Odoo Community Association (OCA)",
    "website": "https://github.com/rosenvladimirov/l10n-bulgaria",
    "depends": [
        "hr_skills",
    ],
    "data": [
        "data/hr_skill_certification_data.xml",
    ],
    "demo": [],
    "installable": True,
    "auto_install": False,
    "application": False,
    "maintainers": ["rosenvladimirov"],
    "tags": ["localization", "hr", "bulgaria", "skills", "certification"],
    "odoo_version": "19.0",
    "python_version": ">=3.11",
    "countries": ["BG"],
}
