#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import logging
import xml.etree.ElementTree as ET

from odoo import api, fields, models
from odoo.addons.l10n_bg_reports_audit.models.l10n_bg_file_helper import get_l10n_bg_applicability
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountAccountTagBulkEditWizard(models.TransientModel):
    _name = 'account.account.tag.bulk.edit.wizard'
    _description = 'Bulk Edit Account Tags'

    tag_ids = fields.Many2many('account.account.tag', string='Tags')
    l10n_bg_applicability = fields.Selection(
        selection=get_l10n_bg_applicability(), string="Use for"
    )
    l10n_bg_config_file = fields.Binary(string="Config File")

    def action_apply(self):
        for tag in self.tag_ids:
            tag.l10n_bg_applicability = self.l10n_bg_applicability

    def action_process_config_file(self):
        """Process the uploaded XML config file from the binary field."""
        if not self.l10n_bg_config_file:
            raise UserError("No configuration file uploaded.")

        file_content_json = {}
        # Decode the base64 binary content
        file_content = base64.b64decode(self.l10n_bg_config_file)

        try:
            # Parse the XML file
            root = ET.fromstring(file_content)
            # Example: Loop through XML elements
            for child in root:
                _logger.info(f"Tag: {child.tag}, Attributes: {child.attrib}, Text: {child.text}")
                if child.tag == "settings" and child.attrib.get('name'):
                    file_content_json[child.attrib['name']] = child.text
        except ET.ParseError as e:
            raise UserError(f"Invalid XML file: {e}")

        if file_content_json:
            self.env['res.company'].write({'l10n_bg_config_template': file_content_json})
            for key, value in file_content_json.items():
                tag_id = self.env['account.account.tag'].search([('name', '=', key)])
                if tag_id:
                    tag_id.l10n_bg_applicability = value
            return {'type': 'ir.actions.act_window_close'}
        else:
            raise UserError("No settings found in the XML file.")
