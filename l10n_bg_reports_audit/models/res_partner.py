#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_bg_tax_tag_receivable_ids = fields.Many2many(
        string="NSI Receivable Account Tags",
        comodel_name='account.account.tag',
        relation='l10n_bg_partner_receivable_tag_rel',
        column1='partner_id',
        column2='account_tag_id',
        domain="[('applicability', '=', 'l10n_bg_partner')]",
        help='Default Tags for receivable in NSI reports like Reference to the claims and obligations allocated to institutional sectors'
    )

    l10n_bg_tax_tag_payable_ids = fields.Many2many(
        string="NSI Payable Account Tags",
        comodel_name='account.account.tag',
        relation='l10n_bg_partner_payable_tag_rel',
        column1='partner_id',
        column2='account_tag_id',
        domain="[('applicability', '=', 'l10n_bg_partner')]",
        help='Default Tags for payable in NSI reports like Reference to the claims and obligations allocated to institutional sectors'
    )
