#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models
from odoo.addons.l10n_bg_reports_audit.models.l10n_bg_file_helper import get_l10n_bg_applicability
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountAccountTagBulkEditWizard(models.TransientModel):
    _name = 'account.account.tag.bulk.edit.wizard'
    _description = 'Bulk Edit Account Tags'

    tag_ids = fields.Many2many('account.account.tag', string='Tags')
    l10n_bg_applicability = fields.Selection(
        selection="_get_l10n_bg_applicability", string="Use for"
    )

    def _get_l10n_bg_applicability(self):
        return get_l10n_bg_applicability(self)

    def action_apply(self):
        for tag in self.tag_ids:
            tag.l10n_bg_applicability = self.l10n_bg_applicability

