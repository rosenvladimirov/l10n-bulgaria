# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # =========================================================================
    # RELATED ПОЛЕТА ОТ АКТИВНИЯ ДОГОВОР
    # =========================================================================
    l10n_bg_contract_wage = fields.Monetary(
        related='version_id.wage',
        readonly=True,
        currency_field='currency_id'
    )

    # Клас полета от активния договор
    l10n_bg_current_class_period = fields.Char(
        string='Current class period (YY:MM:DD)',
        related='version_id.l10n_bg_current_class_period',
        readonly=True,
        help='Current class period of the active contract'
    )

    l10n_bg_initial_class_period = fields.Char(
        string='Starting Class Period (YY:MM:DD)',
        related='version_id.l10n_bg_initial_class_period',
        readonly=True,
        help='Initial class period of the active contract'
    )

    l10n_bg_auto_class_increment = fields.Boolean(
        string='Automatic class increase',
        related='version_id.l10n_bg_auto_class_increment',
        readonly=True,
        help='Automatic increase in class from active contract'
    )

    # Полета за трудов стаж от активния договор
    l10n_bg_seniority_allowance_rate = fields.Float(
        string='Percentage for work experience (%)',
        related='version_id.l10n_bg_seniority_allowance_rate',
        readonly=True,
        help='Percentage for work experience from the active contract'
    )

    l10n_bg_seniority_years = fields.Float(
        string='Years of work experience',
        related='version_id.l10n_bg_seniority_years',
        readonly=True,
        help='Years of work experience from the active contract'
    )

    l10n_bg_computed_seniority_allowance = fields.Monetary(
        string='A calculated internship supplement',
        related='version_id.l10n_bg_computed_seniority_allowance',
        readonly=True,
        help='Calculated Additional Active Contract Extension Supplement'
    )

    # =========================================================================
    # COMPUTED ПОЛЕТА ЗА КЛАСГОДИНИ (БАЗИРАНИ НА АКТИВНИЯ ДОГОВОР) - STORED
    # =========================================================================

    l10n_bg_class_years_integer = fields.Integer(
        string='Class Year (Aims)',
        compute='_compute_class_years_from_contract',
        store=True,  # Make it stored so it can be searched
        help='Class Years as an integer of the active contract'
    )

    l10n_bg_class_years_decimal = fields.Float(
        string='Class years (decimal)',
        compute='_compute_class_years_from_contract',
        store=True,  # Make it stored so it can be searched
        help='Class of years in decimal format from the active contract'
    )

    # =========================================================================
    # COMPUTED METHODS
    # =========================================================================

    @api.depends('version_id.l10n_bg_current_class_period')
    def _compute_class_years_from_contract(self):
        """Изчисли класгодини от активния договор"""
        for employee in self:
            if employee.version_id:
                employee.l10n_bg_class_years_integer = employee.version_id.l10n_bg_class_years_integer
                employee.l10n_bg_class_years_decimal = employee.version_id.l10n_bg_class_years_decimal
            else:
                employee.l10n_bg_class_years_integer = 0
                employee.l10n_bg_class_years_decimal = 0.0

    # =========================================================================
    # BUSINESS METHODS
    # =========================================================================

    def get_class_info_from_contract(self):
        """Вземи информация за класа от активния договор"""
        self.ensure_one()
        if self.version_id:
            return self.version_id.get_class_info()
        return {
            'initial_class_period': '',
            'current_class_period': '',
            'class_years_integer': 0,
            'class_years_decimal': 0.0,
            'auto_increment': False,
            'seniority_years': 0.0,
        }

    def get_total_compensation_from_contract(self):
        """Изчисли общото възнаграждение от активния договор"""
        self.ensure_one()
        if self.version_id:
            return self.version_id.get_total_compensation()
        return 0.0

    def get_mod_info_from_contract(self):
        """Вземи MOD информация от активния договор"""
        self.ensure_one()
        if self.version_id:
            return self.version_id.get_mod_info()
        return {
            'computed_mod': 0.0,
            'manual_override': 0.0,
            'effective_mod': 0.0,
            'tzpb_rate': 0.0,
            'qualification_group': False,
            'economic_activity': False,
            'ncop_position': False,
        }
