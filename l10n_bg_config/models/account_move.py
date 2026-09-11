#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class AccountMove(models.Model):
    _inherit = ["account.move", "l10n.bg.config.mixin"]
    _name = "account.move"

    # === Override на l10n_bg_document_number с логиката от l10n_bg_name ===
    l10n_bg_document_number = fields.Char(
        string="Document Number (BG)",
        compute='_compute_l10n_bg_document_number',
        inverse='_inverse_l10n_bg_document_number',
        search='_search_l10n_bg_document_number',
        store=True,
        index="trigram",
        tracking=True,
        copy=False,
    )

    # === l10n_bg_name като related на l10n_bg_document_number ===
    l10n_bg_name = fields.Char(
        string="Number of locale document",
        related='l10n_bg_document_number',
        store=True,
        readonly=False,
    )
    l10n_bg_name_value = fields.Char(
        "Number of locale document (stored)",
        copy=False
    )
    l10n_bg_date = fields.Date("Date of locale document", copy=False)
    l10n_bg_deal_date = fields.Date("Date of deal", copy=False, compute='_compute_l10n_bg_deal_date', store=True)

    # === Override на compute за l10n_bg_document_number ===
    @api.depends("name", "ref", "state", "l10n_bg_name_value")
    def _compute_l10n_bg_document_number(self):
        country_bg = self.env.ref('base.bg')
        for move in self:
            if move.state == 'draft':
                move.l10n_bg_document_number = move.l10n_bg_name_value
            else:
                formatted_name = move._format_l10n_bg_name(move.name)
                if move.partner_id and move.partner_id.country_id.id == country_bg.id:
                    formatted_ref = move._format_l10n_bg_name(move.ref)
                else:
                    formatted_ref = move.ref

                if move.l10n_bg_name_value and (
                    move.l10n_bg_name_value != formatted_ref or
                    move.l10n_bg_name_value != formatted_name
                ):
                    move.l10n_bg_document_number = move.l10n_bg_name_value
                elif move._l10n_bg_allow_ref_fallback():
                    move.l10n_bg_document_number = formatted_ref or formatted_name
                else:
                    # Документът няма СВОЙ локален номер: този на контрагента
                    # живее в `ref`, а `name` е нашата вътрешна номерация.
                    # Нито едното не е „номер на локален документ", затова
                    # полето остава празно вместо да преписва чужд номер.
                    move.l10n_bg_document_number = False

    def _l10n_bg_allow_ref_fallback(self):
        """Може ли `l10n_bg_document_number` да падне на `ref`/`name`.

        Тук — винаги да: ядрото не знае кои документи носят СВОЙ локален
        номер. Слоевете, които знаят (протоколи по чл. 117, митнически
        декларации), стесняват това през override.
        """
        self.ensure_one()
        return True

    def _inverse_l10n_bg_document_number(self):
        for move in self:
            move.l10n_bg_name_value = move.l10n_bg_document_number

    def _search_l10n_bg_document_number(self, operator, value):
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
