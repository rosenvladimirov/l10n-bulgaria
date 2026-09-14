# Bulgaria — Employee Certifications

LGPL-3 · part of `l10n-bulgaria` · depends on `hr_skills`.

## What it does

Adds three skill types flagged as *Certification* for Employees › Training ›
Certifications, each with its own skills and levels:

| Type | Skills | Levels |
|---|---|---|
| Electrical Safety | Electrical Safety Qualification Group (up to 1000 V) | Group I–V |
| Welding | Welding Competence Certificate (Ordinance No. 7/2002) · Welder Qualification BDS EN ISO 9606-1 (steel) · … 9606-2 (aluminium) | fillet welds · plate · pipe |
| Forklift Trucks | Forklift Operator Competence Certificate (Ordinance No. 1/2006) | Group I–III |

Without a skill type flagged as a certification, the "New" button on the
Certifications list saves an employee skill without a skill and the database
rejects it ("Missing required value for the field 'Skill' (skill_id)").

The records are `noupdate`: once installed they belong to the company and an
upgrade does not overwrite local changes.

## What to enter in "Valid to"

| Certificate | Validity | Basis |
|---|---|---|
| Electrical qualification group | re-examined within the period in the job description, but **at most 2 years** for operating staff and **3 years** for managers | Rules for work on electrical equipment up to 1000 V, Art. 27(4) |
| Welding competence certificate | no validity period found in the ordinance | Ordinance No. 7/2002 |
| ISO 9606-1 welder qualification | **3 years**, confirmed by the employer every **6 months** | per the certification bodies (TÜV and others) |
| Forklift competence certificate | no expiry; refresher training every **5 years** — enter the last training date + 5 years | Ordinance No. 1/2006 |

## Note

Level names are in Bulgarian: in Odoo 19 the level name (`hr.skill.level.name`)
is not a translatable field, and these are the terms of the regulations. Skill
type and skill names are translatable (English in the data, Bulgarian in
`i18n/bg.po`). Sources: see `README.bg.md`.
