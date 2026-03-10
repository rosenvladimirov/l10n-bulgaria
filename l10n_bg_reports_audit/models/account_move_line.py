#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, models, tools

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _l10n_bg_apply_tax_tag(self, tag=False, partner=False, update_partner=True):
        _logger.info(
            "Start BG tax tag apply on %s lines (tag=%s, partner=%s, update_partner=%s)",
            len(self),
            tag.id if tag else False,
            partner.id if partner else False,
            update_partner,
        )
        # Applies tax tag to line when conditions are met
        for line in self:
            tax_line = line.tax_line_id
            tax_group = tax_line.tax_group_id if tax_line else False
            if not tax_group:
                tax_group = self.env["account.tax.group"].search(
                    [
                        "|",
                        ("tax_receivable_account_id", "=", line.account_id.id),
                        ("tax_payable_account_id", "=", line.account_id.id),
                    ],
                    limit=1,
                )
                if tax_group:
                    _logger.info(
                        "Fallback tax_group for line %s: matched by account_id=%s",
                        line.id,
                        line.account_id.id if line.account_id else False,
                    )
            if not tax_group:
                _logger.info("Skip line %s: missing tax_group", line.id)
                continue
            line_tag = tag or line.move_id.l10n_bg_tax_tag_id
            line_partner = partner
            if update_partner:
                line_partner = partner or (line_tag and line_tag.l10n_bg_tax_partner_id)
            if not tax_group or not line_tag:
                _logger.debug(
                    "Skip BG tax tag apply for line %s (tax_group=%s, tag=%s)",
                    line.id,
                    tax_group.id if tax_group else False,
                    line_tag.id if line_tag else False,
                )
                _logger.info(
                    "Skip line %s: tax_group=%s tag=%s",
                    line.id,
                    tax_group.id if tax_group else False,
                    line_tag.id if line_tag else False,
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
            if not (is_receivable or is_payable):
                _logger.info(
                    "Skip line %s: not receivable/payable (account_id=%s, balance=%s)",
                    line.id,
                    line.account_id.id if line.account_id else False,
                    line.balance,
                )
                continue
            _logger.info(
                "Apply BG tax tag %s to line %s (update_partner=%s, partner=%s)",
                line_tag.id,
                line.id,
                update_partner,
                line_partner.id if line_partner else False,
            )
            line_ctx = line.with_context(
                l10n_bg_skip_tax_tag_apply=True,
                l10n_bg_skip_tax_closing_check=True,
                check_move_validity=False,
            )
            line_ctx.tax_tag_ids = line_ctx.tax_tag_ids | line_tag
            if update_partner and line_partner:
                line_ctx.partner_id = line_partner

    def _l10n_bg_remove_tax_tag(self, tag, partner=False):
        for line in self:
            if tag in line.tax_tag_ids:
                line_ctx = line.with_context(
                    l10n_bg_skip_tax_tag_apply=True,
                    l10n_bg_skip_tax_closing_check=True,
                    check_move_validity=False,
                )
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
