#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import logging
import xml.etree.ElementTree as ET

from odoo import api, fields, models
from odoo.addons.l10n_bg_reports_audit.models.l10n_bg_file_helper import get_l10n_bg_applicability
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountAccountSettingWizard(models.TransientModel):
    _name = 'account.settings.xml.file'
    _description = 'Upload setting xml file'

    l10n_bg_config_file = fields.Binary(string="Config xml File")

    def action_process_config_file(self):
        """Process the uploaded XML config file from the binary field."""
        if not self.l10n_bg_config_file:
            raise UserError("No configuration file uploaded.")

        # Decode the base64 binary content
        file_content = base64.b64decode(self.l10n_bg_config_file)
        self.env.company.xml_to_dict(file_content)
        return {'type': 'ir.actions.act_window_close'}
