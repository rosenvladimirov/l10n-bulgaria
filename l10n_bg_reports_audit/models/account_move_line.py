#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, models, tools

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _l10n_bg_apply_tax_tag(self, tag=False, partner=False, update_partner=True):
        # Applies tax tag to line when conditions are met
        for line in self:
            tax_line = line.tax_line_id
            if not tax_line:
                continue
            tax_group = tax_line.tax_group_id
            tag = tag or line.move_id.l10n_bg_tax_tag_id
            if update_partner:
                partner = partner or line.move_id.l10n_bg_tax_partner_id
            if not tax_group or not tag:
                _logger.debug(
                    "Skip BG tax tag apply for line %s (tax_group=%s, tag=%s)",
                    line.id,
                    tax_group.id if tax_group else False,
                    tag.id if tag else False,
                )
                continue
            is_receivable = (
                tax_group.tax_receivable_account_id
                and line.account_id == tax_group.tax_receivable_account_id
                and line.balance > 0
            )
            is_payable = (
                tax_group.tax_payable_account_id
                and line.account_id == tax_group.tax_payable_account_id
                and line.balance < 0
            )
            if is_receivable or is_payable:
                is_negative = line.balance < 0
                is_match = (
                    (is_negative and (tag.tax_negate or (tag.name and tag.name.startswith("-"))))
                    or (not is_negative and (not tag.tax_negate and tag.name and tag.name.startswith("+")))
                )
                if is_match:
                    _logger.debug(
                        "Apply BG tax tag %s to line %s (update_partner=%s, partner=%s)",
                        tag.id,
                        line.id,
                        update_partner,
                        partner.id if partner else False,
                    )
                    line_ctx = line.with_context(l10n_bg_skip_tax_tag_apply=True)
                    line_ctx.tax_tag_ids = line_ctx.tax_tag_ids | tag
                    if update_partner and partner:
                        line_ctx.partner_id = partner

    def _l10n_bg_remove_tax_tag(self, tag, partner=False):
        for line in self:
            if tag in line.tax_tag_ids:
                line_ctx = line.with_context(l10n_bg_skip_tax_tag_apply=True)
                line_ctx.tax_tag_ids = line_ctx.tax_tag_ids - tag
                if partner and line_ctx.partner_id == partner:
                    line_ctx.partner_id = False

    def _l10n_bg_reset_tax_partner(self, tag, partner):
        for line in self:
            if tag in line.tax_tag_ids and line.partner_id != partner:
                line.with_context(l10n_bg_skip_tax_tag_apply=True).partner_id = partner

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        if not self.env.context.get('l10n_bg_skip_tax_tag_apply'):
            lines._l10n_bg_apply_tax_tag()
        return lines

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get('l10n_bg_skip_tax_tag_apply'):
            return res
        if {'tax_line_id', 'account_id', 'balance', 'move_id', 'tax_tag_ids'} & set(vals):
            self._l10n_bg_apply_tax_tag()
        return res

    def init(self):
        super().init()
        tools.create_index(
            self._cr,
            'account_move_line_account_date_idx',
            'account_move_line',
            ['account_id', 'date']
        )
