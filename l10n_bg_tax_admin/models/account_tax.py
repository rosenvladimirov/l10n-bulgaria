# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, Command


class AccountTax(models.Model):
    _inherit = 'account.tax'

    amount_type = fields.Selection(selection_add=[
        ('customs_rate', 'Customs Rate'),
        ('private_rate', 'Private usage Rate')
    ], ondelete={'customs_rate': 'set default'})

    @api.model
    def _prepare_base_line_for_taxes_computation(self, record, **kwargs):
        """ Override to use l10n_bg_customs_value as the base for tax computation
        for customs declaration lines.
        """

        def load(field, fallback, from_base_line=False):
            return self._get_base_line_field_value_from_record(record, field, kwargs, fallback,
                                                               from_base_line=from_base_line)

        # Извикваме parent метода
        base_line = super()._prepare_base_line_for_taxes_computation(record, **kwargs)
        l10n_bg_move_type = load('l10n_bg_move_type', 'standard')

        # Използваме load() за да извлечем митническата стойност и тарифната ставка
        l10n_bg_customs_value = load('l10n_bg_customs_value', 0.0)
        l10n_bg_tariff_rate = load('l10n_bg_tariff_rate', 0.0)
        #  Използваме load за да извлечем кофицента който се прилага в/у данъчната основа при лично ползване
        l10n_bg_consumption_coefficient = load('l10n_bg_consumption_coefficient', 50.0)

        # Зареждаме типа на сделката според Българското законодателство за да я използваме в последствие
        base_line['_l10n_bg_move_type'] = l10n_bg_move_type

        # Ако има митническа стойност, презаписваме price_unit
        if l10n_bg_move_type == 'customs' and l10n_bg_customs_value and base_line['quantity']:
            base_line['price_unit'] = l10n_bg_customs_value / base_line['quantity']

            # Добавяме референция към customs полетата в evaluation context
            # за да можем да ги достъпим в _eval_tax_amount_*
            base_line['_l10n_bg_tariff_rate'] = l10n_bg_tariff_rate
            base_line['_l10n_bg_customs_value'] = l10n_bg_customs_value

        # Ако има коефицент и е сделка за лично ползване прзаписваме данъчната основа
        if l10n_bg_move_type == 'private' and l10n_bg_consumption_coefficient != 0.0:
            base_line['price_unit'] = base_line['price_unit'] * l10n_bg_consumption_coefficient / 100.0
            base_line['_l10n_bg_consumption_coefficient'] = l10n_bg_consumption_coefficient
        return base_line

    def _eval_tax_amount_price_excluded(self, batch, raw_base, evaluation_context):
        """ Eval the tax amount for the customs_rate type using l10n_bg_tariff_rate from the line. """
        self.ensure_one()

        # Ако е customs_rate тип, използваме тарифната ставка
        if self.amount_type == 'customs_rate':
            tariff_rate = evaluation_context.get('_l10n_bg_tariff_rate', self.amount)
            return raw_base * tariff_rate / 100.0

        # Стандартно изчисление за другите типове
        return super()._eval_tax_amount_price_excluded(batch, raw_base, evaluation_context)

    def _eval_tax_amount_price_included(self, batch, raw_base, evaluation_context):
        """ Eval the tax amount for customs_rate type when price is included. """
        self.ensure_one()

        # Ако е customs_rate тип с price include
        if self.amount_type == 'customs_rate':
            tariff_rate = evaluation_context.get('_l10n_bg_tariff_rate', self.amount)

            # Изчисляваме общия процент от batch
            total_percentage = sum(
                evaluation_context.get('_l10n_bg_tariff_rate',
                                       tax.amount) if tax.amount_type == 'customs_rate' else tax.amount
                for tax in batch
            ) / 100.0

            to_price_excluded_factor = 1 / (1 + total_percentage) if total_percentage != -1 else 0.0
            return raw_base * to_price_excluded_factor * tariff_rate / 100.0

        # Ако е private_rate тип с price include
        if self.amount_type == 'private_rate':
            move_type = evaluation_context.get('_l10n_bg_move_type', 'standard')
            if move_type == 'private':
                coefficient = evaluation_context.get('_l10n_bg_consumption_coefficient', 50.0)

                # Изчисляваме общия процент от batch с приложен коефициент
                total_percentage = sum(
                    (tax.amount * (coefficient / 100.0)) if tax.amount_type == 'private_rate' else tax.amount
                    for tax in batch
                ) / 100.0

                to_price_excluded_factor = 1 / (1 + total_percentage) if total_percentage != -1 else 0.0
                return raw_base * to_price_excluded_factor * self.amount * (coefficient / 100.0) / 100.0
            return 0.0

        # Стандартно изчисление за другите типове
        return super()._eval_tax_amount_price_included(batch, raw_base, evaluation_context)
