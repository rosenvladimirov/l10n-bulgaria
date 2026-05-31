# Changelog

All notable changes to `hr_org_chart_multilang_fix` will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to Odoo module versioning
(`<odoo-major>.<odoo-minor>.<feature>.<fix>.<patch>`).

## [18.0.1.0.0] - 2026-05-13

### Added
- Initial release.
- Override `HrOrgChartController._prepare_employee_data` to resolve
  translatable JSONB dict values (`name`, `job_name`, `job_title`) to plain
  strings before they reach the OWL template, fixing the `[object Object]`
  rendering in the Organisation Chart widget when `hr.employee.name` is made
  translatable by `l10n_bg_multilang` / `partner_multilang`.
- Covers all three form views that mount the widget (`hr.employee`,
  `hr.employee.public`, `res.users`) via the shared controller endpoint.
