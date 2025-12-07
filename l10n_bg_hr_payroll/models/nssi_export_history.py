# -*- coding: utf-8 -*-
import base64
from datetime import timedelta

from odoo import models, fields, api, _, tools
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

ENCODING = "windows-1251"


class HrNssiDeclarationHistory(models.Model):
    _name = 'hr.nssi.declaration.history'
    _description = 'NSSI Declaration Export History'
    _inherits = {'hr.payslip.nssi.declaration': 'declaration_id'}
    _order = 'export_date desc, id desc'

    # Link to original declaration
    declaration_id = fields.Many2one(
        'hr.payslip.nssi.declaration',
        string='Declaration',
        required=True,
        ondelete='cascade',
        help='Reference to the original declaration'
    )

    # Export metadata
    export_id = fields.Many2one(
        'hr.nssi.export.batch',
        string='Export Batch',
        ondelete='set null',
        help='Batch export this declaration was part of'
    )

    export_date = fields.Datetime(
        string='Export Date',
        default=fields.Datetime.now,
        required=True,
        help='Date and time when export was created'
    )

    export_status = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('exported', 'Exported'),
        ('error', 'Error'),
        ('cancelled', 'Cancelled'),
    ], string='Export Status',
        default='draft',
        required=True,
        help='Status of this export record'
    )

    error_message = fields.Text(
        string='Error Message',
        help='Error message if export failed'
    )

    user_id = fields.Many2one(
        'res.users',
        string='Exported By',
        default=lambda self: self.env.user,
        required=True,
        help='User who initiated the export'
    )

    @api.model
    def create_from_declaration(self, declaration, export_batch=None):
        """
        Create a history record from an existing declaration
        """
        if not declaration:
            return False

        # Create history record with all the same fields
        vals = {
            'declaration_id': declaration.id,
            'export_id': export_batch and export_batch.id or False,
            'export_status': export_batch and 'pending' or 'draft',
        }

        return self.create(vals)

    @api.model
    def cleanup_old_records(self, days=365):
        """Clean up old export history records"""
        cutoff_date = fields.Datetime.now() - timedelta(days=days)
        old_records = self.search([
            ('export_date', '<', cutoff_date),
            ('export_status', 'in', ['exported', 'error', 'cancelled'])
        ])

        count = len(old_records)
        old_records.unlink()

        _logger.info(f"Cleaned up {count} old NSSI declaration history records")
        return count


class HrNssiExportBatch(models.Model):
    _name = 'hr.nssi.export.batch'
    _description = 'NSSI Declaration Export Batch'
    _order = 'export_date desc, id desc'
    _rec_name = 'display_name'

    # Basic fields
    name = fields.Char(
        string='Reference',
        help='Reference for the export batch'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )

    # Export details
    month = fields.Integer(
        string='Month',
        required=True,
        help='Reporting Month (1-12)'
    )

    year = fields.Integer(
        string='Year',
        required=True,
        help='Reporting Year'
    )

    # Status
    status = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('error', 'Error'),
        ('cancelled', 'Cancelled'),
    ], string='Status',
        default='draft',
        required=True,
        help='Export status')

    # Dates
    export_date = fields.Datetime(
        string='Export Date',
        default=fields.Datetime.now,
        required=True,
        help='Date and time when export was initiated'
    )

    # Export data
    declaration_ids = fields.One2many(
        'hr.nssi.declaration.history',
        'export_id',
        string='Declaration History Records'
    )

    declaration_count = fields.Integer(
        string='Declarations Count',
        compute='_compute_declaration_count',
        store=True,
        help='Number of declarations included in this export'
    )

    # Technical details
    file_name = fields.Char(
        string='File Name',
        help='Generated file name for export',
        default='EMPL2021.TXT'
    )

    file_size = fields.Integer(
        string='File Size (bytes)',
        help='Size of generated export file'
    )

    # User
    user_id = fields.Many2one(
        'res.users',
        string='Exported By',
        default=lambda self: self.env.user,
        required=True,
        help='User who initiated the export'
    )

    export_file = fields.Binary(
        string='TXT File',
        attachment=True,
        help='Binary TXT file encoded in Windows-1251'
    )

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )

    @api.depends('declaration_ids')
    def _compute_declaration_count(self):
        for record in self:
            record.declaration_count = len(record.declaration_ids)

    @api.depends('company_id.name', 'month', 'year', 'export_date')
    def _compute_display_name(self):
        for record in self:
            company_name = record.company_id.name if record.company_id else 'Unknown'
            date_str = record.export_date.strftime('%Y-%m-%d %H:%M') if record.export_date else 'No Date'
            record.display_name = f"{company_name} - {record.month}/{record.year} ({date_str})"

    def action_collect_declarations(self):
        """Collect declarations for the selected period"""
        self.ensure_one()

        # Clear existing history records
        self.declaration_ids.unlink()

        # Find declarations for this period
        declarations = self.env['hr.payslip.nssi.declaration'].search([
            ('month', '=', self.month),
            ('year', '=', self.year),
            ('company_id', '=', self.company_id.id)
        ])

        if not declarations:
            raise ValidationError(_("No declarations found for period %s/%s") % (self.month, self.year))

        # Create history records for each declaration
        for declaration in declarations:
            self.env['hr.nssi.declaration.history'].create_from_declaration(
                declaration,
                export_batch=self
            )

        self.status = 'pending'
        return True

    def generate_nssi_file(self):
        """Generate text file in EMPL2021.TXT format"""
        self.ensure_one()

        if not self.declaration_ids:
            raise ValidationError(_("No declarations found for this export"))

        try:
            # Get all declaration history records
            lines = []

            for history in self.declaration_ids:
                # Format the data according to requirements
                declaration_values = [
                    str(history.month or 0),
                    str(history.year or 0),
                    history.company_uic or '',
                    history.employee_identification or '',
                    str(history.identification_type or '0'),
                    '"' + (history.family_name or '').upper() + '"',
                    '"' + (history.initials or '') + '"',
                    str(history.insurance_type or 0),
                    str(history.insurance_start_day_1 or 0),
                    str(history.insurance_end_day_1 or 0),
                    str(history.insurance_start_day_2 or 0),
                    str(history.insurance_end_day_2 or 0),
                    str(history.insurance_start_day_3 or 0),
                    str(history.insurance_end_day_3 or 0),
                    str(history.insurance_start_day_4 or 0),
                    str(history.insurance_end_day_4 or 0),
                    str(history.insurance_start_day_5 or 0),
                    str(history.insurance_end_day_5 or 0),
                    str(history.insured_days_total or 0),
                    str(history.worked_days_with_insurance or 0),
                    str(history.sick_leave_days or 0),
                    str(history.child_care_days or 0),
                    str(history.days_without_insurance or 0),
                    str(history.unpaid_leave_days or 0),
                    str(history.sick_leave_days_with_employer_salary or 0),
                    str(history.worked_hours_total or 0),
                    str(history.overtime_hours or 0),
                    str(history.qualification_group or 0),
                    history.economic_activity_code or '0000',
                    str(history.main_economic_activity or 0),
                    history.working_time_code or '0000',
                    str(history.health_insurance_income or 0),
                    str(history.health_insurance_rate_employer or 0),
                    str(history.insurance_income or 0),
                    str(history.doo_insurance_rate_employer or 0),
                    str(history.doo_insurance_rate_employee or 0),
                    str(history.health_insurance_rate_base_employer or 0),
                    str(history.health_insurance_rate_base_employee or 0),
                    str(history.tzpb_rate or 0),
                    str(history.teacher_pension_fund_rate or 0),
                    str(history.professional_pension_fund_rate or 0),
                    str(history.universal_pension_fund_rate_employer or 0),
                    str(history.universal_pension_fund_rate_employee or 0),
                    str(history.health_only_income or 0),
                    str(history.health_only_rate or 0),
                    str(history.gross_salary or 0),
                    str(history.guaranteed_fund_rate or 0),
                    str(history.taxable_income or 0),
                    str(history.monthly_tax or 0),
                    str(history.net_salary or 0),
                    str(history.insurance_fund_code or 0),
                    str(history.correction_code or '0'),
                    history.source_flag or history.company_uic or '',
                ]
                lines.append(','.join(declaration_values))

            # Join lines with CRLF
            content = '\r\n'.join(lines) + '\r\n\x1A'  # End with CTRL+Z marker

            # Encode content
            file_bytes = content.encode(ENCODING, errors='ignore')

            # Save export data
            self.write({
                'export_file': base64.b64encode(file_bytes),
                'file_size': len(file_bytes),
                'status': 'processing',
            })

            # Update history records
            for history in self.declaration_ids:
                history.write({
                    'export_status': 'exported'
                })

            return True

        except Exception as e:
            error_msg = _("Error generating NSSI file: %s") % str(e)
            self.write({"status": "error"})
            for history in self.declaration_ids:
                history.write({
                    'export_status': 'error',
                    'error_message': error_msg
                })
            _logger.exception("NSSI file generation failed for export record %s", self.id)
            raise ValidationError(error_msg)

    def action_download_file(self):
        """Download TXT file"""
        self.ensure_one()

        if not self.export_file:
            raise ValidationError(_('No file content available'))

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model=hr.nssi.export.batch&id={self.id}&field=export_file&download=true&filename={self.file_name}',
            'target': 'new',
        }

    def action_retry_export(self):
        """Retry failed export"""
        self.ensure_one()

        if self.status not in ['error', 'cancelled']:
            raise ValidationError(_('Only failed or cancelled exports can be retried'))

        # Create new batch record for retry
        new_record = self.copy({
            'status': 'draft',
            'export_date': fields.Datetime.now(),
            'export_file': False,
            'file_size': 0,
            'declaration_ids': False,
        })

        # Return view for new record
        return {
            'name': _('Retry NSSI Export'),
            'view_mode': 'form',
            'res_model': 'hr.nssi.export.batch',
            'res_id': new_record.id,
            'type': 'ir.actions.act_window',
        }

    @api.model
    def cleanup_old_records(self, days=365):
        """Clean up old export history records"""
        cutoff_date = fields.Datetime.now() - timedelta(days=days)
        old_records = self.search([
            ('export_date', '<', cutoff_date),
            ('status', 'in', ['success', 'error', 'cancelled'])
        ])

        count = len(old_records)
        old_records.unlink()

        _logger.info(f"Cleaned up {count} old NSSI export batch records")
        return count
