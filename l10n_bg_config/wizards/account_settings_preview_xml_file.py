#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import html
import json
import logging
import xmltodict

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

def convert_lists_to_string(data):
    if isinstance(data, dict):
        return {key: convert_lists_to_string(value) for key, value in data.items()}
    elif isinstance(data, list):
        return ','.join(map(str, data))
    return data


class AccountAccountSettingPreviewWizard(models.TransientModel):
    _name = 'account.settings.preview.xml.file'
    _description = 'Preview setting as xml file'

    l10n_bg_config_file = fields.Binary(string="Config xml File")
    l10n_bg_config_file_preview = fields.Html(string="XML Preview", sanitize=True, sanitize_tags=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        try:
            data_dict = self.env.company.l10n_bg_config_template and json.loads(self.env.company.l10n_bg_config_template) or {}
            xtml_content = xmltodict.unparse(data_dict, pretty=True, indent='  ').encode('utf-8')
            res['l10n_bg_config_file'] = base64.b64encode(xtml_content)

            processed_dict = convert_lists_to_string(data_dict)
            xml_content = xmltodict.unparse(processed_dict, pretty=True, indent='  ')
            escaped_content = html.escape(xml_content)
            html_content = f"<p>Current setting.<br/> Important: The downloaded file cannot be used directly for configuration. It serves only as a visual representation of the current configuration.</p><pre>{escaped_content}</pre>"
            res['l10n_bg_config_file_preview'] = html_content
        except Exception as e:
            res['l10n_bg_config_file_preview'] = f'<div class="alert alert-danger">Error by processing XML data: {str(e)}</div>'
        return res

    def _get_formatted_xml(self):
        """Helper method to get formatted XML from binary data"""
        try:
            xml_content = base64.b64decode(self.l10n_bg_config_file).decode('utf-8')
            data_dict = xmltodict.parse(xml_content)
            processed_dict = convert_lists_to_string(data_dict)
            return xmltodict.unparse(processed_dict, pretty=True, indent='  ')
        except Exception as e:
            raise UserError(f"Data processing error: {str(e)}")

    def save_xml(self):
        """Save formatted XML as a downloadable file"""
        formatted_xml = self._get_formatted_xml()

        attachment = self.env['ir.attachment'].create({
            'name': 'config_preview.xml',
            'type': 'binary',
            'datas': base64.b64encode(formatted_xml.encode('utf-8')),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/xml'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
