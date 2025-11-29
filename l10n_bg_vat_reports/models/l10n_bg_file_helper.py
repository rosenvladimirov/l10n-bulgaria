#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import tempfile

from odoo import _, fields, models
from odoo.exceptions import UserError

try:
    import pyzipper
except ImportError:
    raise UserError("Please install Pyzipper: pip install pyzipper")

_logger = logging.getLogger(__name__)

class AuditExportFileHelper(models.AbstractModel):
    _inherit = "l10n.bg.export.file"

    def l10n_bg_export_csvs_zip(self, options=None):
        files_report = self.get_l10n_bg_csv(["declaration", "purchase", "sales", "vies"], options=options)
        zip_params = {
            'compression': pyzipper.ZIP_DEFLATED,
            'allowZip64': False
        }

        if options.get('password'):
            password = options.get('password')
            zip_params.update({
                'encryption': pyzipper.WZ_AES,
            })
        else:
            password = b''

        with tempfile.NamedTemporaryFile() as buf:
            with pyzipper.AESZipFile(
                buf,
                mode="w",
                **zip_params
            ) as zip_buffer:
                if password and password.strip():
                    zip_buffer.pwd = password
                for value in files_report.values():
                    for i, csv in enumerate(value["file_content"]):
                        zip_buffer.writestr(
                            value["file_name"], csv.encode("cp1251", errors="ignore")
                        )
            buf.seek(0)
            try:
                res = buf.read()
            except Exception as e:
                raise UserError(
                    _("An error occurred while generating the ZIP file. "
                      "Please check the report's encoding or file structure.")
                ) from e
        return {
            "file_name": 'vat_reports.zip',
            "file_content": res,
            "file_type": "zip",
        }
