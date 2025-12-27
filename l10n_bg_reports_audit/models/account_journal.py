from odoo import models
from odoo.addons.l10n_bg_reports_audit.models.l10n_bg_file_helper import get_doc_type


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _l10n_bg_document_type_selection_values(self):
        return get_doc_type()
