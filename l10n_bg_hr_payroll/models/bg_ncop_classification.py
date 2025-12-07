import logging

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class BGNCOPClassificationExtension(models.Model):
    _inherit = 'bg.hr.payroll.ncop.classification'

    # ===============================
    # COMPUTED RATE FIELDS
    # ===============================

    doo_emp_1959_rate = fields.Float(
        string='SSI Employee Rate after 1959 (%)',
        compute='_compute_contribution_rates',
        store=True,
        help='State Social Insurance fond employee contribution rate from parameter'
    )
    doo_emp_1960_rate = fields.Float(
        string='SSI Employee Rate before 1960 (%)',
        compute='_compute_contribution_rates',
        store=True,
        help='State Social Insurance fond employee contribution rate from parameter'
    )

    doo_er_1959_rate = fields.Float(
        string='SSI Employer Rate after 1959 (%)',
        compute='_compute_contribution_rates',
        store=True,
        help='State Social Insurance fond employer contribution rate from parameter'
    )
    doo_er_1960_rate = fields.Float(
        string='SSI Employer Rate before 1960 (%)',
        compute='_compute_contribution_rates',
        store=True,
        help='State Social Insurance fond employer contribution rate from parameter'
    )

    upf_er_rate = fields.Float(
        string='UPF Employer Rate (%)',
        compute='_compute_contribution_rates',
        store=True,
        help='Universal Pension Fund employer contribution rate from parameter'
    )

    upf_emp_rate = fields.Float(
        string='UPF Employee Rate (%)',
        compute='_compute_contribution_rates',
        store=True,
        help='Universal Pension Fund employee contribution rate from parameter'
    )

    tzbp_rate = fields.Float(
        string='OAD Rate (%)',
        compute='_compute_contribution_rates',
        store=True,
        help='Occupational Accident and Disease employer contribution rate from parameter'
    )

    zo_emp_rate = fields.Float(
        string='PHI Employee Rate (%)',
        compute='_compute_contribution_rates',
        store=True,
        help='Public Health Insurance employee contribution rate from parameter'
    )

    zo_er_rate = fields.Float(
        string='PHI Employer Rate (%)',
        compute='_compute_contribution_rates',
        store=True,
        help='Public Health Insurance employer contribution rate from parameter'
    )

    ppf_rate = fields.Float(
        string='PPF Employer Rate (%)',
        compute='_compute_contribution_rates',
        store=True,
        help='Professional Pension Fund Employer contribution rate from parameter'
    )

    # ===============================
    # PARAMETER REFERENCE FIELDS
    # ===============================

    doo_param_id = fields.Many2one(
        'hr.rule.parameter',
        string='SSI Parameter',
        compute='_compute_parameter_references',
        store=True,
        help='Parameter for State Social Insurance fond contribution rate'
    )

    upf_param_id = fields.Many2one(
        'hr.rule.parameter',
        string='UPF Parameter',
        compute='_compute_parameter_references',
        store=True,
        help='Parameter for Universal Pension Fund contribution rate'
    )

    zo_param_id = fields.Many2one(
        'hr.rule.parameter',
        string='PHI Parameter',
        compute='_compute_parameter_references',
        store=True,
        help='Parameter for Public Health Insurance Fund contribution rate'
    )

    tzbp_param_id = fields.Many2one(
        'hr.rule.parameter',
        string='OAD Parameter',
        compute='_compute_parameter_references',
        store=True,
        help='Parameter for Occupational Accident and Disease Prevention Fund contribution rate'
    )

    tzbp_param_value_code = fields.Selection([
        ('CAT1', 'First category'),
        ('CAT2_HI', 'Second category - high risk'),
        ('CAT2_MID', 'Second category - middle risk'),
        ('CAT2_LO', 'Second category - low risk'),
        ('CAT3_PROD', 'Third category - production'),
        ('CAT3_SRV', 'Third category - service'),
        ('CAT3_OFFICE', 'Third category - office'),
    ],
        string='OAD Parameter Value Code',
        compute='_compute_parameter_references',
        store=True,
        help='Code for OAD parameter value'
    )

    ppf_param_id = fields.Many2one(
        'hr.rule.parameter',
        string='PPF Parameter',
        compute='_compute_parameter_references',
        store=True,
        help='Parameter for Professional Pension Fund contribution rate'
    )

    ppf_param_value_code = fields.Selection([
        ('I', 'PPF rate employer I category'),
        ('II', 'PPF rate employer II category'),
        ('III', 'PPF rate employer III category'),
    ],
        string='PPF Parameter Value Code',
        compute='_compute_parameter_references',
        store=True,
        help='Code for PPF parameter value'
    )

    # ===============================
    # COMPUTED METHODS
    # ===============================

    @api.depends('parent_id')
    def _compute_parameter_references(self):
        """Compute parameter references from hierarchy"""
        for record in self:
            # Reset all parameters
            record.doo_param_id = False
            record.upf_param_id = False
            record.zo_param_id = False
            record.ppf_param_id = False
            record.tzbp_param_id = False

            # Try to find parameters in hierarchy
            for hierarchy_record in record._get_hierarchy_records():
                # Look for combined parameters first
                combined_param = self.env['hr.rule.parameter'].search([
                    ('code', 'in', ['BG_DOO_COMBINED_RATES', 'BG_UPF_COMBINED_RATES', 'BG_ZO_COMBINED_RATES', 'BG_PPF_COMBINED_RATES', 'BG_TZBP_COMBINED_RATES']),
                    ('country_id', '=', self.env.ref('base.bg', raise_if_not_found=False).id)
                ])

                if combined_param:
                    for param in combined_param:
                        if param.code == 'BG_DOO_COMBINED_RATES':
                            record.doo_param_id = param
                        elif param.code == 'BG_UPF_COMBINED_RATES':
                            record.upf_param_id = param
                        elif param.code == 'BG_PPF_COMBINED_RATES':
                            record.ppf_param_id = param
                        elif param.code == 'BG_ZO_COMBINED_RATES':
                            record.zo_param_id = param
                        elif param.code == 'BG_TZBP_COMBINED_RATES':
                            record.tzbp_param_id = param
                            # Set default TZBP code if isn't set
                            if not record.tzbp_param_value_code:
                                record.tzbp_param_value_code = 'CAT3_OFFICE'  # Default risk category
                        elif param.code == 'BG_PPF_COMBINED_RATES':
                            record.ppf_param_id = param
                            if not record.ppf_param_value_code:
                                record.ppf_param_value_code = 'III'
                break

    @api.depends('doo_param_id', 'upf_param_id', 'zo_param_id',
                 'tzbp_param_id', 'ppf_param_id', 'parent_id')
    def _compute_contribution_rates(self):
        """Compute contribution rates from hr.rule.parameter using _get_parameter_from_code"""
        for record in self:
            # DOO rates using combined parameters with lists
            record.doo_emp_1959_rate = record._get_combined_doo_rate('BG_DOO_EMP_RATE', 0)  # Index 0 for after 1959
            record.doo_emp_1960_rate = record._get_combined_doo_rate('BG_DOO_EMP_RATE', 1)  # Index 1 for before 1960
            record.doo_er_1959_rate = record._get_combined_doo_rate('BG_DOO_ER_RATE', 0)  # Index 0 for after 1959
            record.doo_er_1960_rate = record._get_combined_doo_rate('BG_DOO_ER_RATE', 1)  # Index 1 for before 1960

            # ZO rates using combined parameters with single values
            record.zo_emp_rate = record._get_combined_single_rate('BG_ZO_COMBINED_RATES', 'BG_ZO_EMP_RATE')
            record.zo_er_rate = record._get_combined_single_rate('BG_ZO_COMBINED_RATES', 'BG_ZO_ER_RATE')

            # UPF rates using combined parameters with single values
            record.upf_emp_rate = record._get_combined_single_rate('BG_UPF_COMBINED_RATES', 'BG_UPF_EMP_RATE')
            record.upf_er_rate = record._get_combined_single_rate('BG_UPF_COMBINED_RATES', 'BG_UPF_ER_RATE')

            # PPF rates special handling if needed
            record.ppf_rate = record._get_ppf_combined_rate()

            # TZBP rate - special handling if needed
            record.tzbp_rate = record._get_tzbp_combined_rate()

    def _get_combined_doo_rate(self, param_key, age_index):
        """
        Get DOO rate from combined parameter using list format

        Args:
            param_key (str): Parameter key ('BG_DOO_EMP_RATE' or 'BG_DOO_ER_RATE')
            age_index (int): Index in the list (0 for after 1959, 1 for before 1960)

        Returns:
            float: Rate value or 0.0 if not found
        """
        # Try to get from combined parameter first
        try:
            combined_data = self.env['hr.rule.parameter']._get_parameter_from_code(
                'BG_DOO_COMBINED_RATES',
                date=fields.Date.today(),
                raise_if_not_found=False
            )

            if combined_data and isinstance(combined_data, dict):
                rate_list = combined_data.get(param_key, [])
                if isinstance(rate_list, list) and len(rate_list) > age_index:
                    return float(rate_list[age_index])

        except Exception as e:
            _logger.debug(f"Could not get combined DOO rate for {param_key}[{age_index}]: {str(e)}")

        # Fallback to hierarchical search
        return self._get_parameter_value_hierarchical(param_key, age_index)

    def _get_combined_single_rate(self, combined_param_code, param_key):
        """
        Get single rate from combined parameter

        Args:
            combined_param_code (str): Combined parameter code
            param_key (str): Parameter key within the combined structure

        Returns:
            float: Rate value or 0.0 if not found
        """
        try:
            combined_data = self.env['hr.rule.parameter']._get_parameter_from_code(
                combined_param_code,
                date=fields.Date.today(),
                raise_if_not_found=False
            )

            if combined_data and isinstance(combined_data, dict):
                rate_value = combined_data.get(param_key, 0.0)
                return float(rate_value) if rate_value else 0.0

        except Exception as e:
            _logger.debug(f"Could not get combined single rate for {param_key}: {str(e)}")

        # Fallback to individual parameter lookup
        return self._get_individual_parameter_value(param_key)

    def _get_tzbp_combined_rate(self):
        """Get TZBP rate from combined parameter"""
        if not self.tzbp_param_value_code:
            return 0.0

        try:
            combined_data = self.env['hr.rule.parameter']._get_parameter_from_code(
                'BG_TZBP_COMBINED_RATES',
                date=fields.Date.today(),
                raise_if_not_found=False
            )

            if combined_data and isinstance(combined_data, dict):
                tzbp_key = f'BG_TZBP_RATE_{self.tzbp_param_value_code}'
                rate_value = combined_data.get(tzbp_key, 0.0)
                return float(rate_value) if rate_value else 0.0

        except Exception as e:
            _logger.debug(f"Could not get TZBP combined rate: {str(e)}")

        # Fallback to hierarchical search
        return self._get_tzbp_parameter_value_recursive()

    def _get_ppf_combined_rate(self):
        """Get PPF rate from combined parameter"""
        if not self.ppf_param_value_code:
            return 0.0

        try:
            combined_data = self.env['hr.rule.parameter']._get_parameter_from_code(
                'BG_PPF_COMBINED_RATES',
                date=fields.Date.today(),
                raise_if_not_found=False
            )

            if combined_data and isinstance(combined_data, dict):
                ppf_key = f'BG_PPF_ER_{self.ppf_param_value_code}_RATE'
                rate_value = combined_data.get(ppf_key, 0.0)
                return float(rate_value) if rate_value else 0.0

        except Exception as e:
            _logger.debug(f"Could not get TZBP combined rate: {str(e)}")

        # Fallback to hierarchical search
        return self._get_tzbp_parameter_value_recursive()

    def _get_parameter_value_hierarchical(self, param_key, list_index=None):
        """
        Get parameter value hierarchically with support for list indexes

        Args:
            param_key (str): Parameter key
            list_index (int, optional): Index for list-type parameters

        Returns:
            float: Parameter value or 0.0 if not found
        """
        for record in self._get_hierarchy_records():
            # Try individual parameter codes first (legacy support)
            legacy_codes = self._get_legacy_parameter_codes(param_key, list_index)

            for code in legacy_codes:
                try:
                    value = self.env['hr.rule.parameter']._get_parameter_from_code(
                        code,
                        date=fields.Date.today(),
                        raise_if_not_found=False
                    )
                    if value and float(value) > 0:
                        return float(value)
                except:
                    continue

        return 0.0

    def _get_individual_parameter_value(self, param_key):
        """
        Get individual parameter value (fallback for single values)

        Args:
            param_key (str): Parameter key

        Returns:
            float: Parameter value or 0.0 if not found
        """
        try:
            value = self.env['hr.rule.parameter']._get_parameter_from_code(
                param_key,
                date=fields.Date.today(),
                raise_if_not_found=False
            )
            return float(value) if value else 0.0
        except:
            return 0.0

    def _get_legacy_parameter_codes(self, param_key, list_index=None):
        """
        Get legacy parameter codes for backward compatibility

        Args:
            param_key (str): Parameter key
            list_index (int, optional): Index for list parameters

        Returns:
            list: List of legacy parameter codes to try
        """
        legacy_mapping = {
            'BG_DOO_EMP_RATE': {
                0: ['BG_DOO_EMP_RATE_AFTER_1959'],
                1: ['BG_DOO_EMP_RATE_BEFORE_1960']
            },
            'BG_DOO_ER_RATE': {
                0: ['BG_DOO_ER_RATE_AFTER_1959'],
                1: ['BG_DOO_ER_RATE_BEFORE_1960']
            },
            'BG_ZO_EMP_RATE': ['BG_ZO_EMP_RATE'],
            'BG_ZO_ER_RATE': ['BG_ZO_ER_RATE'],
            'BG_UPF_EMP_RATE': ['BG_UPF_EMP_RATE'],
            'BG_UPF_ER_RATE': ['BG_UPF_ER_RATE']
        }

        mapping = legacy_mapping.get(param_key, [])

        if isinstance(mapping, dict) and list_index is not None:
            return mapping.get(list_index, [])
        elif isinstance(mapping, list):
            return mapping
        else:
            return []

    # ===============================
    # INVERSE METHODS FOR CDATA PARAMETER SYNC
    # ===============================

    def _inverse_doo_emp_1959_rate(self):
        """Inverse method for doo_emp_1959_rate - updates DOO combined parameter"""
        for record in self:
            if record.doo_emp_1959_rate >= 0:  # Allow 0 values
                record._update_doo_combined_parameter()

    def _inverse_doo_emp_1960_rate(self):
        """Inverse method for doo_emp_1960_rate - updates DOO combined parameter"""
        for record in self:
            if record.doo_emp_1960_rate >= 0:  # Allow 0 values
                record._update_doo_combined_parameter()

    def _inverse_doo_er_1959_rate(self):
        """Inverse method for doo_er_1959_rate - updates DOO combined parameter"""
        for record in self:
            if record.doo_er_1959_rate >= 0:  # Allow 0 values
                record._update_doo_combined_parameter()

    def _inverse_doo_er_1960_rate(self):
        """Inverse method for doo_er_1960_rate - updates DOO combined parameter"""
        for record in self:
            if record.doo_er_1960_rate >= 0:  # Allow 0 values
                record._update_doo_combined_parameter()

    def _inverse_upf_emp_rate(self):
        """Inverse method for upf_emp_rate - updates UPF combined parameter"""
        for record in self:
            if record.upf_emp_rate >= 0:  # Allow 0 values
                record._update_upf_combined_parameter()

    def _inverse_tzbp_rate(self):
        """Inverse method for tzbp_rate - updates TZBP combined parameter"""
        for record in self:
            if record.tzbp_rate >= 0:  # Allow 0 values
                record._update_tzbp_combined_parameter()

    # ===============================
    # CDATA PARAMETER UPDATE METHODS
    # ===============================

    def _update_doo_combined_parameter(self):
        """Update or create DOO combined parameter from current rate values"""
        self.ensure_one()

        try:
            country_id = self.env.ref('base.bg', raise_if_not_found=False)
            if not country_id:
                return

            # Generate DOO parameter data
            doo_param_data = self.create_combined_doo_parameter()
            if not doo_param_data:
                return

            # Find or create the parameter
            param_code = 'BG_DOO_COMBINED_RATES'
            existing_param = self.env['hr.rule.parameter'].search([
                ('code', '=', param_code),
                ('country_id', '=', country_id.id)
            ], limit=1)

            if not existing_param:
                # Create new parameter
                existing_param = self.env['hr.rule.parameter'].create({
                    'name': f'ДОО Ставки Комбинирани - Auto Generated',
                    'code': param_code,
                    'country_id': country_id.id,
                    'description': f'Автоматично генериран от {self.display_name}'
                })

            # Update or create parameter value
            existing_value = self.env['hr.rule.parameter.value'].search([
                ('rule_parameter_id', '=', existing_param.id),
                ('date_from', '=', fields.Date.today())
            ], limit=1)

            cdata_value = f"<![CDATA[{doo_param_data['cdata_value']}]]>"

            if existing_value:
                existing_value.parameter_value = cdata_value
            else:
                self.env['hr.rule.parameter.value'].create({
                    'rule_parameter_id': existing_param.id,
                    'date_from': fields.Date.today(),
                    'parameter_value': cdata_value
                })

            _logger.info(f"Updated DOO combined parameter for {self.display_name}")

        except Exception as e:
            _logger.error(f"Error updating DOO combined parameter for {self.display_name}: {str(e)}")

    def _update_upf_combined_parameter(self):
        """Update or create UPF combined parameter from current rate values"""
        self.ensure_one()

        try:
            country_id = self.env.ref('base.bg', raise_if_not_found=False)
            if not country_id:
                return

            # Generate UPF parameter data
            upf_param_data = self.create_combined_upf_parameter()
            if not upf_param_data:
                return

            # Find or create the parameter
            param_code = 'BG_UPF_COMBINED_RATES'
            existing_param = self.env['hr.rule.parameter'].search([
                ('code', '=', param_code),
                ('country_id', '=', country_id.id)
            ], limit=1)

            if not existing_param:
                # Create new parameter
                existing_param = self.env['hr.rule.parameter'].create({
                    'name': f'УПФ Ставки Комбинирани - Auto Generated',
                    'code': param_code,
                    'country_id': country_id.id,
                    'description': f'Автоматично генериран от {self.display_name}'
                })

            # Update or create parameter value
            existing_value = self.env['hr.rule.parameter.value'].search([
                ('rule_parameter_id', '=', existing_param.id),
                ('date_from', '=', fields.Date.today())
            ], limit=1)

            cdata_value = f"<![CDATA[{upf_param_data['cdata_value']}]]>"

            if existing_value:
                existing_value.parameter_value = cdata_value
            else:
                self.env['hr.rule.parameter.value'].create({
                    'rule_parameter_id': existing_param.id,
                    'date_from': fields.Date.today(),
                    'parameter_value': cdata_value
                })

            _logger.info(f"Updated UPF combined parameter for {self.display_name}")

        except Exception as e:
            _logger.error(f"Error updating UPF combined parameter for {self.display_name}: {str(e)}")

    def _update_tzbp_combined_parameter(self):
        """Update or create TZBP combined parameter from current rate values"""
        self.ensure_one()

        try:
            country_id = self.env.ref('base.bg', raise_if_not_found=False)
            if not country_id:
                return

            # Generate TZBP parameter data
            tzbp_param_data = self.create_combined_tzbp_parameter()
            if not tzbp_param_data:
                return

            # Find or create the parameter
            param_code = 'BG_TZBP_COMBINED_RATES'
            existing_param = self.env['hr.rule.parameter'].search([
                ('code', '=', param_code),
                ('country_id', '=', country_id.id)
            ], limit=1)

            if not existing_param:
                # Create new parameter
                existing_param = self.env['hr.rule.parameter'].create({
                    'name': f'ТЗБП Ставки Комбинирани - Auto Generated',
                    'code': param_code,
                    'country_id': country_id.id,
                    'description': f'Автоматично генериран от {self.display_name}'
                })

            # Update or create parameter value
            existing_value = self.env['hr.rule.parameter.value'].search([
                ('rule_parameter_id', '=', existing_param.id),
                ('date_from', '=', fields.Date.today())
            ], limit=1)

            cdata_value = f"<![CDATA[{tzbp_param_data['cdata_value']}]]>"

            if existing_value:
                existing_value.parameter_value = cdata_value
            else:
                self.env['hr.rule.parameter.value'].create({
                    'rule_parameter_id': existing_param.id,
                    'date_from': fields.Date.today(),
                    'parameter_value': cdata_value
                })

            _logger.info(f"Updated TZBP combined parameter for {self.display_name}")

        except Exception as e:
            _logger.error(f"Error updating TZBP combined parameter for {self.display_name}: {str(e)}")

    # ===============================
    # CDATA PARAMETER BUILDER METHODS
    # ===============================

    def build_cdata_parameter_value(self, parameter_mapping, comments=None):
        """
        Build CDATA parameter value with proper format for different parameter types

        Args:
            parameter_mapping (dict): Mapping of parameter codes to values (can be lists or single values)
            comments (dict, optional): Optional comments for each parameter

        Returns:
            str: CDATA formatted parameter value
        """
        if not parameter_mapping:
            return "{}"

        # Build the dictionary structure
        comment_lines = []

        # Add each parameter with its value (list or single)
        for param_code, param_value in parameter_mapping.items():
            if param_value is not None:
                if isinstance(param_value, list):
                    # Handle list format for DOO parameters
                    if any(v > 0 for v in param_value):
                        value_str = str(param_value).replace("'", "")
                        comment = comments.get(param_code, '') if comments else ''
                        comment_lines.append(
                            f"    '{param_code}': {value_str},  // {comment}" if comment else f"    '{param_code}': {value_str},")
                else:
                    # Handle single values for ZO, UPF parameters
                    if param_value > 0:
                        comment = comments.get(param_code, '') if comments else ''
                        comment_lines.append(
                            f"    '{param_code}': {param_value},    // {comment}" if comment else f"    '{param_code}': {param_value},")

        # Format as CDATA content
        if comment_lines:
            cdata_content = "{\n" + "\n".join(comment_lines) + "\n}"
        else:
            cdata_content = "{}"

        return cdata_content

    def create_combined_doo_parameter(self):
        """
        Create combined DOO parameter from rate fields using list format

        Returns:
            dict: Parameter creation data or None if no rates available
        """
        self.ensure_one()

        # Collect DOO rates as lists [after_1959, before_1960]
        parameter_mapping = {}

        # DOO Employee rates
        emp_rates = [
            self.doo_emp_1959_rate if self.doo_emp_1959_rate > 0 else 0.0,
            self.doo_emp_1960_rate if self.doo_emp_1960_rate > 0 else 0.0
        ]

        # DOO Employer rates
        er_rates = [
            self.doo_er_1959_rate if self.doo_er_1959_rate > 0 else 0.0,
            self.doo_er_1960_rate if self.doo_er_1960_rate > 0 else 0.0
        ]

        # Only add if at least one rate is > 0
        if any(rate > 0 for rate in emp_rates):
            parameter_mapping['BG_DOO_EMP_RATE'] = emp_rates

        if any(rate > 0 for rate in er_rates):
            parameter_mapping['BG_DOO_ER_RATE'] = er_rates

        if not parameter_mapping:
            return None

        # Define comments
        comments = {
            'BG_DOO_EMP_RATE': 'ДОО ставки работник - след/преди 1960',
            'BG_DOO_ER_RATE': 'ДОО ставки работодател - след/преди 1960'
        }

        # Build CDATA parameter value
        cdata_value = self.build_cdata_parameter_value(parameter_mapping, comments)

        return {
            'parameter_code': 'BG_DOO_COMBINED_RATES',
            'parameter_name': f'ДОО Ставки Комбинирани - {self.name}',
            'cdata_value': cdata_value,
            'parameter_mapping': parameter_mapping
        }

    def create_combined_zo_parameter(self):
        """
        Create combined ZO parameter using single values

        Returns:
            dict: Parameter creation data or None if no rates available
        """
        self.ensure_one()

        # За ЗО използваме единични стойности
        parameter_mapping = {}

        # Get ZO rates from global parameters or defaults
        zo_emp_rate = self._get_individual_parameter_value('BG_ZO_EMP_RATE') or 0.032
        zo_er_rate = self._get_individual_parameter_value('BG_ZO_ER_RATE') or 0.048

        if zo_emp_rate > 0:
            parameter_mapping['BG_ZO_EMP_RATE'] = zo_emp_rate
        if zo_er_rate > 0:
            parameter_mapping['BG_ZO_ER_RATE'] = zo_er_rate

        if not parameter_mapping:
            return None

        # Define comments
        comments = {
            'BG_ZO_EMP_RATE': 'ЗО ставка работник - 3.2%',
            'BG_ZO_ER_RATE': 'ЗО ставка работодател - 4.8%'
        }

        # Build CDATA parameter value
        cdata_value = self.build_cdata_parameter_value(parameter_mapping, comments)

        return {
            'parameter_code': 'BG_ZO_COMBINED_RATES',
            'parameter_name': f'ЗО Ставки Комбинирани - {self.name}',
            'cdata_value': cdata_value,
            'parameter_mapping': parameter_mapping
        }

    def create_combined_upf_parameter(self):
        """
        Create combined UPF parameter using single values

        Returns:
            dict: Parameter creation data or None if no rates available
        """
        self.ensure_one()

        # За УПФ използваме единични стойности
        parameter_mapping = {}

        # Use UPF employee rate
        upf_er_rate = self._get_individual_parameter_value('BG_UPF_EMP_RATE') or 0.028
        if self.upf_emp_rate > 0:
            parameter_mapping['BG_UPF_EMP_RATE'] = self.upf_emp_rate

        # Get UPF employer rate from global parameters
        upf_er_rate = self._get_individual_parameter_value('BG_UPF_ER_RATE') or 0.028
        if upf_er_rate > 0:
            parameter_mapping['BG_UPF_ER_RATE'] = upf_er_rate

        if not parameter_mapping:
            return None

        # Define comments
        comments = {
            'BG_UPF_EMP_RATE': 'УПФ ставка работник - 2.2%',
            'BG_UPF_ER_RATE': 'УПФ ставка работодател - 2.8%'
        }

        # Build CDATA parameter value
        cdata_value = self.build_cdata_parameter_value(parameter_mapping, comments)

        return {
            'parameter_code': 'BG_UPF_COMBINED_RATES',
            'parameter_name': f'УПФ Ставки Комбинирани - {self.name}',
            'cdata_value': cdata_value,
            'parameter_mapping': parameter_mapping
        }

    def create_combined_tzbp_parameter(self):
        """
        Create combined TZBP parameter from current rate values

        Returns:
            dict: Parameter creation data or None if no rates available
        """
        self.ensure_one()

        if not self.tzbp_param_value_code or self.tzbp_rate <= 0:
            return None

        # За ТЗБП използваме специфичен ключ според кода
        parameter_mapping = {
            f'BG_TZBP_RATE_{self.tzbp_param_value_code}': self.tzbp_rate
        }

        # Define comments
        comments = {
            f'BG_TZBP_RATE_{self.tzbp_param_value_code}': f'ТЗБП ставка категория {self.tzbp_param_value_code}'
        }

        # Build CDATA parameter value
        cdata_value = self.build_cdata_parameter_value(parameter_mapping, comments)

        return {
            'parameter_code': 'BG_TZBP_COMBINED_RATES',
            'parameter_name': f'ТЗБП Ставки Комбинирани - {self.name}',
            'cdata_value': cdata_value,
            'parameter_mapping': parameter_mapping
        }

    # ===============================
    # HIERARCHY AND HELPER METHODS
    # ===============================

    def _get_hierarchy_records(self):
        """
        Get records in hierarchy order (self, parent, grandparent, etc.)

        Returns:
            list: List of records from current to root
        """
        records = []
        current = self

        # Prevent infinite loop
        seen_ids = set()

        while current and current.id not in seen_ids:
            records.append(current)
            seen_ids.add(current.id)
            current = current.parent_id

            # Safety check to prevent infinite loops
            if len(records) > 10:  # Max 10 levels in hierarchy
                break

        return records

    def _get_parameter_value(self, parameter_record):
        """
        Get parameter value from parameter record

        Args:
            parameter_record: hr.rule.parameter record

        Returns:
            float: Parameter value or 0.0 if not found
        """
        if not parameter_record:
            return 0.0

        try:
            # Get the current parameter value
            param_value = self.env['hr.rule.parameter']._get_parameter_from_code(
                parameter_record.code,
                date=fields.Date.today(),
                raise_if_not_found=False
            )

            if param_value:
                if isinstance(param_value, (int, float)):
                    return float(param_value)
                elif isinstance(param_value, str):
                    return float(param_value)
                elif isinstance(param_value, dict):
                    # For combined parameters, return the first valid value
                    for key, value in param_value.items():
                        if isinstance(value, (int, float)) and value > 0:
                            return float(value)
                        elif isinstance(value, list) and value:
                            return float(value[0]) if value[0] > 0 else 0.0

            return 0.0

        except Exception as e:
            _logger.debug(f"Error getting parameter value for {parameter_record.code}: {str(e)}")
            return 0.0

    def _get_parameter_value_by_code(self, parameter_record, value_code):
        """
        Get parameter value using specific code (for TZBP)

        Args:
            parameter_record: hr.rule.parameter record
            value_code (str): Specific value code to look for

        Returns:
            float: Parameter value or 0.0 if not found
        """
        if not parameter_record or not value_code:
            return 0.0

        try:
            # Get the parameter data
            param_data = self.env['hr.rule.parameter']._get_parameter_from_code(
                parameter_record.code,
                date=fields.Date.today(),
                raise_if_not_found=False
            )

            if param_data and isinstance(param_data, dict):
                # Look for specific key with value_code
                tzbp_key = f'BG_TZBP_RATE_{value_code}'
                if tzbp_key in param_data:
                    return float(param_data[tzbp_key]) if param_data[tzbp_key] else 0.0

                # Fallback: look for direct value_code key
                if value_code in param_data:
                    return float(param_data[value_code]) if param_data[value_code] else 0.0

            return 0.0

        except Exception as e:
            _logger.debug(f"Error getting parameter value by code {value_code}: {str(e)}")
            return 0.0

    def _get_tzbp_parameter_value_recursive(self):
        """
        Get TZBP parameter value recursively through hierarchy

        Returns:
            float: TZBP rate or 0.0 if not found
        """
        for record in self._get_hierarchy_records():
            if record.tzbp_param_id and record.tzbp_param_value_code:
                value = self._get_parameter_value_by_code(
                    record.tzbp_param_id,
                    f'BG_TZBP_RATE_{record.tzbp_param_value_code}'
                )
                if value > 0:
                    return value

        # Fallback: try to get default TZBP rate
        try:
            default_value = self.env['hr.rule.parameter']._get_parameter_from_code(
                'BG_TZBP_COMBINED_RATES',  # Default category A
                date=fields.Date.today(),
                raise_if_not_found=False
            )
            value = self._get_parameter_value_by_code(
                default_value,
                'BG_TZBP_RATE_CAT3_OFFICE'
            )
            return float(value) if value else 0.0
        except:
            return 0.0

    def _get_qualification_mapping_dict(self):
        """
        Get qualification group mapping dictionary

        Returns:
            dict: Mapping from class digit to a qualification group
        """
        return {
            '0': 'military',  # Клас 0 - Професии във въоръжените сили
            '1': 'manager',  # Клас 1 - Ръководители
            '2': 'specialist',  # Клас 2 - Специалисти
            '3': 'technician',  # Клас 3 - Техници
            '4': 'clerk',  # Клас 4 - Помощен административен персонал
            '5': 'service',  # Клас 5 - Работници, заети с услуги
            '6': 'skilled',  # Клас 6 - Квалифицирани работници в селското стопанство
            '7': 'skilled',  # Клас 7 - Квалифицирани работници и занаятчии
            '8': 'operator',  # Клас 8 - Машинисти и оператори
            '9': 'elementary'  # Клас 9 - Професии, неизискващи квалификация
        }

    # ===============================
    # ONCHANGE METHODS
    # ===============================

    @api.onchange('code')
    def _onchange_code_set_level(self):
        """Auto-determine level based on code length"""
        if not self.code:
            return

        code_length = len(self.code)
        level_mapping = {
            1: 'major_group',
            2: 'sub_major_group',
            4: 'minor_group'
        }

        if code_length >= 6:
            self.level = 'unit_group'
        else:
            self.level = level_mapping.get(code_length, 'occupation')

    @api.onchange('code')
    def _onchange_code_set_qualification_group(self):
        """Auto-set qualification group based on NKPD class (first digit)"""
        if not self.code or len(self.code) < 1:
            return

        class_digit = self.code[0]
        qualification_mapping = self._get_qualification_mapping_dict()
        self.qualification_group = qualification_mapping.get(class_digit)

    # ===============================
    # PUBLIC METHODS
    # ===============================

    def get_effective_contribution_rates(self):
        """
        Get all effective contribution rates for this classification

        Returns:
            dict: Dictionary with all contribution rates
        """
        self.ensure_one()
        return {
            'doo_employee_1959': self.doo_emp_1959_rate,
            'doo_employer_1959': self.doo_er_1959_rate,
            'doo_employee_1960': self.doo_emp_1960_rate,
            'doo_employer_1960': self.doo_er_1960_rate,
            'upf_employee': self.upf_emp_rate,
            'upf_employer': self.upf_er_rate,
            'tzbp': self.tzbp_rate
        }

    def get_parameter_sources(self):
        """
        Get the source records for each parameter (for debugging)

        Returns:
            dict: Dictionary showing which record provides each parameter
        """
        self.ensure_one()
        sources = {}

        parameter_fields = ['doo_param_id', 'upf_param_id', 'zo_param_id', 'tzbp_param_id', 'ppf_param_id']

        for param_field in parameter_fields:
            for record in self._get_hierarchy_records():
                if record[param_field]:
                    value = self._get_parameter_value(record[param_field])
                    if value > 0:
                        sources[param_field] = record
                        break

        # TZBP source
        for record in self._get_hierarchy_records():
            if record.tzbp_param_id and record.tzbp_param_value_code:
                value = self._get_parameter_value_by_code(
                    record.tzbp_param_id,
                    f'BG_TZBP_RATE_{record.tzbp_param_value_code}'
                )
                if value > 0:
                    sources['tzbp_param_id'] = record
                    break
        return sources


    # ===============================
    # ACTION METHODS
    # ===============================

    def action_sync_with_xml_parameters(self):
        """
        Sync current record with XML parameter definitions

        Returns:
            None
        """
        self.ensure_one()

        try:
            # Force recompute of parameter references
            self._compute_parameter_references()

            # Force recompute of contribution rates
            self._compute_contribution_rates()

            # Get current rate values for reporting
            rates = self.get_effective_contribution_rates()
            active_rates_count = sum(1 for rate in rates.values() if rate > 0)

            message = f"""Synchronization completed for '{self.display_name}':

🔧 PARAMETERS: Updated
📊 ACTIVE RATES: {active_rates_count} of {len(rates)}

Details:
• SSI Employee (>1959): {rates['doo_employee_1959']:.2%}
• SSI Employer (>1959): {rates['doo_employer_1959']:.2%}
• SSI Employee (<1960): {rates['doo_employee_1960']:.2%}
• SSI Employer (<1960): {rates['doo_employer_1960']:.2%}
• UPF Employee: {rates['upf_employee']:.2%}
• UPF Employer: {rates['upf_employer']:.2%}
• OAD: {rates['tzbp']:.2%}"""

            notification_type = 'success' if active_rates_count > 0 else 'warning'

            # Send bus notification
            self.env['bus.bus']._sendone(
                self.env.user.partner_id,
                'simple_notification',
                {
                    'title': _('Synchronization Completed'),
                    'message': message,
                    'type': notification_type,
                    'sticky': True,
                }
            )

        except Exception as e:
            error_message = _('Synchronization error: %s') % str(e)
            _logger.error(f"Error in action_sync_with_xml_parameters for {self.display_name}: {str(e)}")

            # Send error bus notification
            self.env['bus.bus']._sendone(
                self.env.user.partner_id,
                'simple_notification',
                {
                    'title': _('Synchronization Error'),
                    'message': error_message,
                    'type': 'danger',
                    'sticky': True,
                }
            )

    def action_update_parameter_references_from_xml(self):
        """
        Update parameter references based on combined XML parameter definitions

        Returns:
            dict: Action results with notification
        """
        try:
            updated_count = 0
            error_count = 0

            # Check for new combined parameters
            combined_parameter_codes = [
                'BG_DOO_COMBINED_RATES',
                'BG_ZO_COMBINED_RATES',
                'BG_UPF_COMBINED_RATES',
                'BG_PPF_COMBINED_RATES',
                'BG_TZBP_COMBINED_RATES'
            ]

            country_id = self.env.ref('base.bg', raise_if_not_found=False)

            # Check which combined parameters exist
            existing_combined_params = {}
            for code in combined_parameter_codes:
                try:
                    param_data = self.env['hr.rule.parameter']._get_parameter_from_code(
                        code,
                        date=fields.Date.today(),
                        raise_if_not_found=False
                    )
                    if param_data:
                        existing_combined_params[code] = param_data
                        _logger.info(f"Found combined parameter {code}: {param_data}")
                except Exception as e:
                    _logger.debug(f"Combined parameter {code} not found: {str(e)}")

            # Update all records to use combined parameters if available
            # all_records = self.search([('active', '=', True)])
            all_records = self.filtered(lambda r: r.active)

            for record in all_records:
                try:
                    record_updated = False

                    # Update DOO parameter references
                    if 'BG_DOO_COMBINED_RATES' in existing_combined_params:
                        combined_param = self.env['hr.rule.parameter'].search([
                            ('code', '=', 'BG_DOO_COMBINED_RATES'),
                            ('country_id', '=', country_id.id)
                        ], limit=1)

                        if combined_param and record.doo_param_id != combined_param:
                            record.doo_param_id = combined_param
                            record_updated = True

                    # Update ZO parameter references
                    if 'BG_ZO_COMBINED_RATES' in existing_combined_params:
                        combined_param = self.env['hr.rule.parameter'].search([
                            ('code', '=', 'BG_ZO_COMBINED_RATES'),
                            ('country_id', '=', country_id.id)
                        ], limit=1)

                        if combined_param and record.zo_param_id != combined_param:
                            record.zo_param_id = combined_param
                            record_updated = True

                    # Update UPF parameter references
                    if 'BG_UPF_COMBINED_RATES' in existing_combined_params:
                        combined_param = self.env['hr.rule.parameter'].search([
                            ('code', '=', 'BG_UPF_COMBINED_RATES'),
                            ('country_id', '=', country_id.id)
                        ], limit=1)

                        if combined_param and record.upf_param_id != combined_param:
                            record.upf_param_id = combined_param
                            record_updated = True

                    # Update PPF parameter references
                    if 'BG_PPF_COMBINED_RATES' in existing_combined_params:
                        combined_param = self.env['hr.rule.parameter'].search([
                            ('code', '=', 'BG_PPF_COMBINED_RATES'),
                            ('country_id', '=', country_id.id)
                        ], limit=1)

                        if combined_param and record.ppf_param_id != combined_param:
                            record.ppf_param_id = combined_param
                            # Set default PPF code if not set
                            if not record.ppf_param_value_code:
                                record.ppf_param_value_code = 'III'
                            record_updated = True

                    # Update TZBP parameter references
                    if 'BG_TZBP_COMBINED_RATES' in existing_combined_params:
                        combined_param = self.env['hr.rule.parameter'].search([
                            ('code', '=', 'BG_TZBP_COMBINED_RATES'),
                            ('country_id', '=', country_id.id)
                        ], limit=1)

                        if combined_param and record.tzbp_param_id != combined_param:
                            record.tzbp_param_id = combined_param
                            # Set default TZBP code if not set
                            if not record.tzbp_param_value_code:
                                record.tzbp_param_value_code = 'CAT3_OFFICE'
                            record_updated = True

                    # Force recomputation of rates with new parameters
                    if record_updated:
                        record._compute_contribution_rates()
                        updated_count += 1

                except Exception as e:
                    error_count += 1
                    _logger.warning(f"Error updating parameter references for record {record.id}: {str(e)}")

            # Prepare a result message
            if existing_combined_params:
                message_parts = [
                    f'Discover with {len(existing_combined_params)} combined parameters:',
                ]
                message_parts.extend([f'• {code}' for code in existing_combined_params.keys()])
                message_parts.append(f'\nThey are updated {updated_count} the record.')

                if error_count > 0:
                    message_parts.append(f'{error_count} update errors.')
                    notification_type = 'warning'
                else:
                    notification_type = 'success'

                message = '\n'.join(message_parts)
            else:
                message = 'No combined parameters found in the system. Individual parameters are used.'
                notification_type = 'info'

            # Send bus notification
            self.env['bus.bus']._sendone(
                self.env.user.partner_id,
                'simple_notification',
                {
                    'title': _('Update parameters'),
                    'message': message,
                    'type': notification_type,
                    'sticky': True,
                }
            )

        except Exception as e:
            error_message = _('Error updating parameters: %s') % str(e)
            _logger.error(f"Error in action_update_parameter_references_from_xml: {str(e)}")

            # Send error bus notification
            self.env['bus.bus']._sendone(
                self.env.user.partner_id,
                'simple_notification',
                {
                    'title': _('Error'),
                    'message': error_message,
                    'type': 'danger',
                    'sticky': True,
                }
            )

    def action_validate_parameter_setup(self):
        """
        Validate parameter setup with support for combined parameters

        Returns:
            None
        """
        self.ensure_one()

        validation_results = []
        warnings = []
        errors = []

        # Check for combined parameters first
        combined_params = [
            ('BG_DOO_COMBINED_RATES', 'SSI Combined Parameters'),
            ('BG_ZO_COMBINED_RATES', 'PHI Combined Parameters'),
            ('BG_UPF_COMBINED_RATES', 'UPF Combined Parameters'),
            ('BG_TZBP_COMBINED_RATES', 'OAD Combined Parameters'),
            ('BG_PPF_COMBINED_RATES', 'PPF Combined Parameters'),
        ]

        for param_code, param_label in combined_params:
            try:
                param_data = self.env['hr.rule.parameter']._get_parameter_from_code(
                    param_code,
                    date=fields.Date.today(),
                    raise_if_not_found=False
                )

                if param_data:
                    if isinstance(param_data, dict):
                        key_count = len(param_data.keys())
                        validation_results.append(f"✅ {param_label}: {key_count} keys")
                    else:
                        validation_results.append(f"✅ {param_label}: Found")
                else:
                    warnings.append(f"⚠️ {param_label}: Not found")

            except Exception as e:
                errors.append(f"❌ {param_label}: Validation error - {str(e)}")

        # Check computed rates
        rate_fields = [
            ('doo_emp_1959_rate', 'SSI Employee Rate (>1959)'),
            ('doo_emp_1960_rate', 'SSI Employee Rate (<1960)'),
            ('doo_er_1959_rate', 'SSI Employer Rate (>1959)'),
            ('doo_er_1960_rate', 'SSI Employer Rate (<1960)'),
            ('upf_emp_rate', 'UPF Employee Rate'),
            ('upf_er_rate', 'UPF Employer Rate'),
            ('tzbp_rate', 'OAD Rate')
        ]

        active_rates = []
        zero_rates = []

        for field_name, field_label in rate_fields:
            rate_value = getattr(self, field_name, 0)
            if rate_value > 0:
                active_rates.append(f"✅ {field_label}: {rate_value:.2%}")
            else:
                zero_rates.append(f"⚪ {field_label}: 0%")

        # Build report message
        message_parts = [f"Diagnostic for '{self.display_name}':", ""]

        if validation_results:
            message_parts.extend(["🔧 COMBINED PARAMETERS:"] + validation_results + [""])

        if active_rates:
            message_parts.extend(["📊 ACTIVE RATES:"] + active_rates + [""])

        if zero_rates:
            message_parts.extend(["📊 ZERO RATES:"] + zero_rates + [""])

        if warnings:
            message_parts.extend(["⚠️ WARNINGS:"] + warnings + [""])

        if errors:
            message_parts.extend(["❌ ERRORS:"] + errors)

        notification_type = 'danger' if errors else ('warning' if warnings else 'info')

        # Send bus notification
        self.env['bus.bus']._sendone(
            self.env.user.partner_id,
            'simple_notification',
            {
                'title': _('Parameter Diagnostics'),
                'message': '\n'.join(message_parts),
                'type': notification_type,
                'sticky': True,
            }
        )
