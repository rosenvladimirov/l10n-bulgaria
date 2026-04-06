# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class Job(models.Model):
    _inherit = "hr.job"

    l10n_bg_ncop_position_id = fields.Many2one(
        'bg.hr.payroll.ncop.classification',
        string='NCOP Position',
        help='NCOP Position',
        ondelete='restrict'
    )
    l10n_bg_ncop_description_html = fields.Html(
        string="NCOP Hierarchy & Requirements",
        compute="_compute_l10n_bg_ncop_description_html",
        store=True,
        readonly=True,
        sanitize=True,
        help="Read-only summary of the selected NCOP position's hierarchy "
             "and qualification requirements. Computed from "
             "l10n_bg_ncop_position_id — does NOT overwrite the regular "
             "job description.",
    )

    @api.depends("l10n_bg_ncop_position_id")
    def _compute_l10n_bg_ncop_description_html(self):
        for job in self:
            if job.l10n_bg_ncop_position_id:
                job.l10n_bg_ncop_description_html = self._build_ncop_html(
                    job.l10n_bg_ncop_position_id,
                )
            else:
                job.l10n_bg_ncop_description_html = False

    @api.model
    def _build_ncop_html(self, ncop):
        """Build the HTML hierarchy + requirements block for an NCOP position."""
        path = ncop.get_hierarchy_path()

        html = '<div class="ncop-hierarchy" style="font-family: Arial, sans-serif;">'
        html += '<h4 style="color: #2c3e50; margin-bottom: 10px;">Йерархия НКПД:</h4>'
        html += '<ul style="list-style-type: none; padding-left: 0; margin-bottom: 20px;">'

        for i, record in enumerate(path):
            indent = '&nbsp;' * (i * 4)
            level_label = dict(
                record._fields['level'].selection
            ).get(record.level, '')
            html += f'<li style="padding: 5px 0;">{indent}'
            html += (
                f'<strong>[{record.code}]</strong> {record.name} '
                f'<em>({level_label})</em></li>'
            )

        html += '</ul>'

        # Изисквания
        html += '<h4 style="color: #2c3e50; margin-bottom: 10px;">Изисквания към професията:</h4>'
        html += '<ul style="padding-left: 20px;">'

        if ncop.qualification_group:
            qual_group_label = dict(
                ncop._fields['qualification_group'].selection
            ).get(ncop.qualification_group, '')
            html += f'<li><strong>Квалификационна група:</strong> {qual_group_label}</li>'

        if ncop.education_level:
            edu_level_label = dict(
                ncop._fields['education_level'].selection
            ).get(ncop.education_level, '')
            html += f'<li><strong>Образователно ниво:</strong> {edu_level_label}</li>'

        if ncop.skill_level:
            html += f'<li><strong>Ниво на умения:</strong> {ncop.skill_level}</li>'

        if ncop.experience_years:
            html += f'<li><strong>Изискван опит:</strong> {ncop.experience_years} години</li>'

        if ncop.skills_requirements:
            html += f'<li><strong>Изисквания за умения:</strong> {ncop.skills_requirements}</li>'

        html += '</ul></div>'

        return html
