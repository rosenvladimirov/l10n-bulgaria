# -*- coding: utf-8 -*-
import ast
import base64
from datetime import timedelta

from odoo import models, fields, api, _, tools
from odoo.exceptions import ValidationError
from lxml import etree
from odoo.tools.xml_utils import validate_xml_from_attachment

import logging

_logger = logging.getLogger(__name__)

ENCODING = "windows-1251"


class L10nBgNapExportHistory(models.Model):
    _name = 'l10n_bg.nap.export.history'
    _description = 'NAP Export History'
    _order = 'export_date desc, id desc'
    _rec_name = 'display_name'

    # Основни полета
    version_id = fields.Many2one(
        'hr.version',
        string='Contract',
        required=True,
        ondelete='cascade',
        help='Related contract'
    )

    contract_amendment_id = fields.Many2one(
        'l10n_bg.hr.version.amendment',
        string='Contract Amendment',
        help='The main employment contract this amendment relates to'
    )

    employee_id = fields.Many2one(
        related='version_id.employee_id',
        string='Employee',
        readonly=True,
        store=True
    )

    company_id = fields.Many2one(
        related='version_id.company_id',
        string='Company',
        readonly=True,
        store=True
    )

    type_correction = fields.Selection([
        ('0', 'Regular data'),
        ('1', 'Correction'),
        ('2', 'Cancel'),
    ], string='Type Correction',
        help='Type of correction operation')

    # Тип експорт
    export_type = fields.Selection([
        ('new_contract', 'New Contract'),
        ('contract_amendment', 'Contract Amendment'),
        ('contract_termination', 'Contract Termination'),
        ('correction', 'Correction'),
        ('cancellation', 'Cancellation'),
    ], string='Export Type',
        required=True,
        help='Type of export operation')

    # Статус на експорт
    status = fields.Selection([
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('error', 'Error'),
        ('cancelled', 'Cancelled'),
    ], string='Status',
        default='pending',
        required=True,
        help='Export status')

    # Дати
    export_date = fields.Datetime(
        string='Export Date',
        default=fields.Datetime.now,
        required=True,
        help='Date and time when export was initiated'
    )

    response_date = fields.Datetime(
        string='Response Date',
        help='Date and time when response was received from NAP'
    )

    # Данни за експорт
    export_data = fields.Text(
        string='Export Data',
        help='Original export data structure'
    )

    export_xml = fields.Text(
        string='Generated XML',
        help='XML content sent to NAP'
    )

    nap_reference = fields.Char(
        string='NAP Reference',
        help='NAP system reference number'
    )

    # Отговор от НАП
    response_message = fields.Text(
        string='Response Message',
        help='Response message from NAP system'
    )

    error_message = fields.Text(
        string='Error Message',
        help='Error message if export failed'
    )

    response_xml = fields.Text(
        string='Response XML',
        help='XML response from NAP system'
    )

    # Технически детайли
    file_name = fields.Char(
        string='File Name',
        help='Generated file name for export'
    )

    file_size = fields.Integer(
        string='File Size (bytes)',
        help='Size of generated export file'
    )

    attempt_number = fields.Integer(
        string='Attempt Number',
        default=1,
        help='Number of export attempt'
    )

    # Потребител
    user_id = fields.Many2one(
        'res.users',
        string='Exported By',
        default=lambda self: self.env.user,
        required=True,
        help='User who initiated the export'
    )

    export_file = fields.Binary(
        string='XML File',
        attachment=True,
        help='Binary XML file encoded in Windows-1251'
    )

    @api.depends('version_id.name', 'export_type', 'export_date')
    def _compute_display_name(self):
        for record in self:
            contract_name = record.version_id.name if record.version_id else 'Unknown'
            export_type_label = dict(self._fields['export_type'].selection).get(record.export_type, 'Unknown')
            date_str = record.export_date.strftime('%Y-%m-%d %H:%M') if record.export_date else 'No Date'
            record.display_name = f"{contract_name} - {export_type_label} ({date_str})"

    @api.onchange('response_date')
    def onchange_response_date(self):
        for record in self:
            record.status = 'success'

    def generate_nap_xml(self):
        """Генерира XML по структурата ETZEmploy + XSD валидация"""
        self.ensure_one()

        if not self.version_id:
            raise ValidationError(_("Contract is required to generate NAP XML"))

        try:
            # -------------------------------------------------------------
            # Данни за експорта
            # -------------------------------------------------------------
            if not self.export_data:
                export_data = self.version_id.generate_nap_export_data()
                self.export_data = str(export_data)
            else:
                try:
                    export_data = ast.literal_eval(self.export_data)
                except (ValueError, SyntaxError):
                    export_data = {}
            if self.type_correction:
                export_data.update({
                    'code_correction': self.type_correction,
                })

            # -------------------------------------------------------------
            # Създаване на XML
            # -------------------------------------------------------------
            E = etree.Element
            Sub = etree.SubElement

            root = E("etzemploy")
            Sub(root, "eik").text = export_data.get("employer_bulstat", "")

            contract = Sub(root, "contract")
            row = Sub(contract, "rowenum")

            mapping = {
                "employtype": "employ_type",
                "codecorrection": "code_correction",
                "documenttype": "document_type",
                "egn": "employee_egn",
                "egntype": "egn_type",
                "firstname": "first_name",
                "secondname": "second_name",
                "thirdname": "third_name",
                "contractdate": "contract_date",
                "contracttype": "contract_type_code",
                "begindate": "start_date",
                "salary": "wage_amount",
                "codenkpd": "profession_code",
                "codekid": "economic_activity_code",
                "codeekatte": "workplace_code",
                "codehours": "working_time_type",
                "workinghours": "daily_hours",
                "vacationdays": "basic_leave_days",
            }
            for xml_tag, data_key in mapping.items():
                Sub(row, xml_tag).text = str(export_data.get(data_key, ""))

            # -------------------------------------------------------------
            # Сериализация и почистване
            # -------------------------------------------------------------
            xml_bytes = etree.tostring(
                root,
                xml_declaration=True,
                encoding=ENCODING,
                pretty_print=True,
            )
            xml_content = xml_bytes.decode(ENCODING)

            # -------------------------------------------------------------
            # XSD валидация
            # -------------------------------------------------------------
            validate_xml_from_attachment(
                self.env,
                xml_bytes,
                "etz_employ_restrict.xsd",
                prefix="l10n_bg_hr_payroll",
            )

            # -------------------------------------------------------------
            # Запис
            # -------------------------------------------------------------
            self.write(
                {
                    "export_xml": xml_content,
                    "export_file": base64.b64encode(xml_bytes),
                    "file_name": f"nap_export_{self.version_id.name}_{self.export_date.strftime('%Y%m%d_%H%M%S')}.xml",
                    "file_size": len(xml_bytes),
                }
            )
            return xml_content

        except Exception as e:
            error_msg = _("Error generating NAP XML: %s") % str(e)
            self.write({"status": "error", "error_message": error_msg})
            _logger.exception("NAP XML generation failed for history record %s", self.id)
            raise ValidationError(error_msg)

    def action_retry_export(self):
        """Retry failed export"""
        self.ensure_one()

        if self.status not in ['error', 'cancelled']:
            raise ValidationError(_('Only failed or cancelled exports can be retried'))

        # Create new history record for retry
        new_record = self.copy({
            'attempt_number': self.attempt_number + 1,
            'status': 'pending',
            'export_date': fields.Datetime.now(),
            'response_date': False,
            'response_message': False,
            'error_message': False,
            'response_xml': False,
            'nap_reference': False,
        })

        # Trigger export on a new record
        return new_record.version_id.action_export_to_nap()

    def action_view_xml(self):
        """View generated XML"""
        self.ensure_one()

        if not self.export_xml:
            raise ValidationError(_('No XML content available'))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'l10n_bg.nap.export.history',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('l10n_bg_hr_payroll.view_nap_export_history_xml_form').id,
            'target': 'new',
            'context': {'show_xml_only': True}
        }

    def action_download_xml(self):
        """Download XML file"""
        self.ensure_one()

        if not self.export_xml:
            raise ValidationError(_('No XML content available'))
        self.status = 'processing'
        field = 'export_file' if self.export_file else 'export_xml'
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model=l10n_bg.nap.export.history&id={self.id}&field={field}&download=true&filename={self.file_name or "export.xml"}',
            'target': 'new',
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

        _logger.info(f"Cleaned up {count} old NAP export history records")
        return count

    # ---------------------------------------------------------------------
    # Override write ‒ когато текстът се редактира ръчно, обновяваме бинарния
    # ---------------------------------------------------------------------
    def write(self, vals):
        res = super().write(vals)
        if 'export_xml' in vals:
            for rec in self:
                # преобразуваме обратно към bytes, за да поддържаме енкодинга
                xml_text = rec.export_xml or ''
                xml_bytes = xml_text.encode(ENCODING, errors='ignore')
                rec.export_file = base64.b64encode(xml_bytes)
                rec.file_size = len(xml_bytes)
        return res

    def unlink(self):
        for record in self:
            record.version_id.l10n_bg_nap_export_status = 'not_exported'
        return super().unlink()
