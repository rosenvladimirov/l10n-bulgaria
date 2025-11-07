#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class AccountMove(models.Model):
    _inherit = ["account.move", "l10n.bg.config.mixin"]
    _name = "account.move"

    l10n_bg_name = fields.Char(
        "Number of locale document",
        compute='_compute_l10n_bg_name',
        inverse='_inverse_l10n_bg_name',
        search='_search_l10n_bg_name',
        store=True,
        index="trigram",
        tracking=True,
        copy=False
    )
    l10n_bg_name_value = fields.Char(
        "Number of locale document (stored)",
        copy=False
    )
    l10n_bg_date = fields.Date("Date of locale document", copy=False)
    l10n_bg_deal_date = fields.Date("Date of deal", copy=False, compute='_compute_l10n_bg_deal_date', store=True)

    @api.depends("name", "ref", "state")
    def _compute_l10n_bg_name(self):
        country_id = self.env.ref('base.bg')
        for move in self:
            if move.state == 'draft':
                # В режим драфт използваме съхранената стойност
                move.l10n_bg_name = move.l10n_bg_name_value
            else:
                # Форматираме name до 10 цифри
                formatted_name = move._format_l10n_bg_name(move.name)
                if move.partner_id and move.partner_id.country_id.id == country_id.id:
                    formatted_ref = move._format_l10n_bg_name(move.ref)
                else:
                    formatted_ref = move.ref

                # Проверяваме дали ръчно зададената стойност е различна от автоматичната
                if move.l10n_bg_name_value and (move.l10n_bg_name_value != formatted_ref or move.l10n_bg_name_value != formatted_name):
                    # Запазваме ръчно зададената стойност
                    move.l10n_bg_name = move.l10n_bg_name_value
                else:
                    # Използваме форматираното name или ref
                    move.l10n_bg_name = formatted_ref or formatted_name

    def _inverse_l10n_bg_name(self):
        for move in self:
            move.l10n_bg_name_value = move.l10n_bg_name

    def _search_l10n_bg_name(self, operator, value):
        return [('l10n_bg_name_value', operator, value)]

    def _format_l10n_bg_name(self, name):
        """
        Форматира номера до 10 цифри с попълване с нули в началото.
        Пример: INV/2025/00001 -> 0000000001
        """
        if not name:
            return ''

        # Извличаме само цифрите от name
        name = name.split('/')[-1] if '/' in name else name
        digits = ''.join(filter(str.isdigit, name))

        if not digits:
            return name

        # Попълваме с нули до 10 цифри
        return digits.zfill(10)

    @api.depends("invoice_date", "date", "delivery_date")
    def _compute_l10n_bg_deal_date(self):
        for move in self:
            move.l10n_bg_deal_date = move.delivery_date or move.invoice_date or move.date
