# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models, _, Command

_logger = logging.getLogger(__name__)


class AccountTax(models.Model):
    _inherit = 'account.tax'

    amount_type = fields.Selection(selection_add=[
        ('customs_rate', 'Customs Rate'),
        ('private_rate', 'Private usage Rate')
    ], ondelete={'customs_rate': 'set default', 'private_rate': 'set default'})

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
        l10n_bg_customs_value_manual = load('l10n_bg_customs_value_manual', False)
        l10n_bg_currency_rate_manual = load('l10n_bg_currency_rate_manual', False)

        #  Използваме load за да извлечем кофицента който се прилага в/у данъчната основа при лично ползване
        l10n_bg_consumption_coefficient = load('l10n_bg_consumption_coefficient', 50.0)

        # Винаги добавяме тарифната ставка, ако е налична
        base_line['_l10n_bg_tariff_rate'] = l10n_bg_tariff_rate
        # Зареждаме типа на сделката според Българското законодателство за да я използваме в последствие
        base_line['_l10n_bg_move_type'] = l10n_bg_move_type

        # При митнически операции използваме митническата стойност само като база за ДДС,
        # без да променяме единичната цена.
        if l10n_bg_move_type == 'customs' and not l10n_bg_customs_value:
            _logger.warning("DEBUG VAT: customs mode but NO customs_value found for line %s", record.name if hasattr(record, 'name') else record)

        # Добавяме референция към митническата стойност в evaluation context
        base_line['_l10n_bg_customs_value'] = l10n_bg_customs_value
        base_line['_l10n_bg_customs_value_manual'] = l10n_bg_customs_value_manual
        base_line['_l10n_bg_currency_rate_manual'] = l10n_bg_currency_rate_manual

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
            # Ensure it is a decimal (e.g. 2.7 -> 0.027)
            if tariff_rate > 1:
                tariff_rate = tariff_rate / 100.0
            return raw_base * tariff_rate

        # Стандартно изчисление за другите типове
        return super()._eval_tax_amount_price_excluded(batch, raw_base, evaluation_context)

    @api.model
    def _add_tax_details_in_base_line(self, base_line, company, rounding_method=None):
        """ Override to calculate Bulgarian specific taxes and pass them as manual amounts. """

        price_unit_after_discount = base_line['price_unit'] * (1 - (base_line['discount'] / 100.0))
        raw_base = base_line['quantity'] * price_unit_after_discount

        use_customs_value = bool(base_line.get('_l10n_bg_customs_value_manual'))
        if base_line.get('_l10n_bg_currency_rate_manual'):
            use_customs_value = True

        if use_customs_value and base_line.get('_l10n_bg_customs_value'):
            raw_base = base_line.get('_l10n_bg_customs_value')

        # Подготвяме manual_tax_amounts ако не е зададен
        if base_line.get('manual_tax_amounts') is None:
            base_line['manual_tax_amounts'] = {}

        # ВАЖНО: Разгъваме групите от данъци!
        sorted_taxes, group_per_tax = base_line['tax_ids']._flatten_taxes_and_sort_them()

        _logger.info(f"DEBUG: After flatten: {len(sorted_taxes)} taxes, raw_base={raw_base}")

        # Намираме нашите специални данъци
        customs_rate_found = False
        # raw_base is used as the base for both customs and VAT taxes.
        for tax in sorted_taxes:
            if tax.amount_type == 'customs_rate':
                customs_rate_found = True

                # Взимаме тарифната ставка от base_line
                tariff_rate = base_line.get('_l10n_bg_tariff_rate', tax.amount)

                # Нормализираме ставката
                if tariff_rate > 1:
                    tariff_rate = tariff_rate / 100.0

                # Изчисляваме данъчната сума НА МИТОТО
                tax_amount = raw_base * tariff_rate

                # КРИТИЧНО: Задаваме И base_amount_currency
                # Това е ВАЖНО за зависимите данъци!
                base_line['manual_tax_amounts'][str(tax.id)] = {
                    'tax_amount_currency': tax_amount,
                    'base_amount_currency': raw_base,  # Базата ЗА МИТОТО
                }

                _logger.info(
                    f"DEBUG: customs_rate tax {tax.id}: rate={tariff_rate * 100}%, base={raw_base}, tax={tax_amount}")
                _logger.info(
                    f"DEBUG: customs_rate tax properties: include_base_amount={tax.include_base_amount}, is_base_affected={tax.is_base_affected}")

                # Проверка за зависимости
                # Ако митото има include_base_amount=True, следващите данъци ще се изчислят на base + мито
                if tax.include_base_amount:
                    _logger.info(
                        f"DEBUG: ⚠️ customs_rate tax AFFECTS subsequent taxes! They will compute on base={raw_base} + customs={tax_amount} = {raw_base + tax_amount}")
            elif use_customs_value and raw_base:
                if tax.price_include:
                    tax_amount = tax._eval_tax_amount_price_included(sorted_taxes, raw_base, base_line)
                else:
                    tax_amount = tax._eval_tax_amount_price_excluded(sorted_taxes, raw_base, base_line)
                base_line['manual_tax_amounts'][str(tax.id)] = {
                    'tax_amount_currency': tax_amount,
                    'base_amount_currency': raw_base,
                }

        if not customs_rate_found:
            _logger.warning(f"DEBUG: NO customs_rate tax found!")

        _logger.info(f"DEBUG: manual_tax_amounts={base_line.get('manual_tax_amounts')}")

        # ВАЖНО: Извикваме super() СЛЕД като сме задали manual_tax_amounts
        # Одоо автоматично ще използва ръчните суми и ще изчисли зависимите данъци правилно
        result = super()._add_tax_details_in_base_line(base_line, company, rounding_method)

        # ЛОГВАНЕ СЛЕД изчисляването
        if 'tax_details' in base_line:
            _logger.info(f"DEBUG: After super(), tax_details computed:")
            for tax_data in base_line['tax_details'].get('taxes_data', []):
                _logger.info(
                    f"  - Tax {tax_data['tax'].id} '{tax_data['tax'].name}': base={tax_data.get('raw_base_amount_currency', 0):.2f}, tax={tax_data.get('raw_tax_amount_currency', 0):.2f}")

        return result

    @api.model
    def _add_accounting_data_to_base_line_tax_details(self, base_line, company, include_caba_tags=False):
        """ Override to fix tag assignment for customs_rate taxes.

        Премахва таговете от reverse charge линията:
        - При invoice: -100% линия → БЕЗ тагове
        - При refund: +100% линия → БЕЗ тагове (ако е настроено така)
        """
        # Извикваме super метода първо
        super()._add_accounting_data_to_base_line_tax_details(base_line, company, include_caba_tags)

        is_refund = base_line['is_refund']
        taxes_data = base_line['tax_details']['taxes_data']

        # Коригираме таговете за customs_rate данъци
        for tax_data in taxes_data:
            tax = tax_data['tax']

            if tax.amount_type == 'customs_rate':
                # Обработваме repartition lines
                for tax_rep_data in tax_data.get('tax_reps_data', []):
                    factor = tax_rep_data['tax_rep'].factor

                    # Определяме коя линия е reverse charge според типа документ
                    # При invoice: -100% е reverse charge
                    # При refund: +100% е reverse charge (ако е огледална конфигурация)
                    is_reverse_charge = (factor < 0 and not is_refund) or (factor > 0 and is_refund)

                    if is_reverse_charge:
                        # Премахваме таговете от reverse charge линията
                        tax_rep_data['tax_tags'] = self.env['account.account.tag']

                        # Актуализираме grouping_key
                        if 'grouping_key' in tax_rep_data:
                            base_line_grouping_key = self._prepare_base_line_grouping_key(base_line)
                            tax_rep_data['grouping_key'] = self._prepare_base_line_tax_repartition_grouping_key(
                                base_line,
                                base_line_grouping_key,
                                tax_data,
                                tax_rep_data,
                            )

    def _eval_tax_amount_price_included(self, batch, raw_base, evaluation_context):
        """ Eval the tax amount for customs_rate type when price is included. """
        self.ensure_one()

        # Ако е customs_rate тип с price include
        if self.amount_type == 'customs_rate':
            tariff_rate = evaluation_context.get('_l10n_bg_tariff_rate', self.amount)

            # Изчисляваме общия процент от batch
            total_percentage = 0.0
            for tax in batch:
                if tax.amount_type == 'customs_rate':
                    t_rate = evaluation_context.get('_l10n_bg_tariff_rate', tax.amount)
                    total_percentage += t_rate
                else:
                    total_percentage += tax.amount

            if tariff_rate > 1:
                tariff_rate = tariff_rate / 100.0
            if total_percentage > 1:
                total_percentage = total_percentage / 100.0

            to_price_excluded_factor = 1 / (1 + total_percentage) if total_percentage != -1 else 0.0
            return raw_base * to_price_excluded_factor * tariff_rate

        # Стандартно изчисление за другите типове (включително private_rate,
        # тъй като неговата база е вече коригирана и стандартния процент ще работи правилно)
        return super()._eval_tax_amount_price_included(batch, raw_base, evaluation_context)
