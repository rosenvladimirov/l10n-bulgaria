from odoo import models, fields, api, _


class HrNssiDeclaration(models.Model):
    _name = 'hr.payslip.nssi.declaration'
    _description = 'NSSI Declaration Form 1'
    _order = 'year desc, month desc, create_date desc'

    # Relationships
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade'
    )
    payslip_id = fields.Many2one(
        'hr.payslip',
        string='Payslip',
        ondelete='restrict'
    )
    version_id = fields.Many2one(
        'hr.version',
        string='Contract',
        related='payslip_id.version_id',
        store=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='version_id.company_id',
        store=True
    )

    # Basic declaration data
    month = fields.Integer(
        string='Month',
        required=True,
        help='From 1 to 12'
    )
    year = fields.Integer(
        string='Year',
        required=True
    )
    correction_code = fields.Selection(
        [('0', 'Regular data'),
         ('1', 'Corrective data'),
         ('8', 'Deletion data')],
        string='Correction Code',
        default='0',
        required=True
    )

    # Insurer and insured person data
    company_uic = fields.Char(
        string='Company UIC',
        related='company_id.l10n_bg_uic',
        store=True
    )
    employee_identification = fields.Char(
        string='ID Number (PIN/FN/FNN/Service number)',
        related='employee_id.identification_id',
        store=True
    )
    identification_type = fields.Selection(
        [('0', 'PIN'),
         ('2', 'FNN, FN or Service number from NAP'),
         ('3', 'Individual with Bulstat')],
        string='Identification Type',
        default='0',
        required=True
    )
    family_name = fields.Char(
        string='Family Name',
        compute='_compute_family_name',
        store=True
    )
    initials = fields.Char(
        string='Initials',
        compute='_compute_initials',
        store=True
    )

    # Insurance data
    insurance_type = fields.Integer(
        string='Insured Person Type',
        required=True,
        help='Code of the insured type according to the nomenclature'
    )
    insurance_start_day_1 = fields.Integer(string='Insurance Start/Resume Day 1', help='From 1 to 31')
    insurance_end_day_1 = fields.Integer(string='Last Day 1', help='From 1 to 31')
    insurance_start_day_2 = fields.Integer(string='Insurance Start/Resume Day 2', help='From 1 to 31')
    insurance_end_day_2 = fields.Integer(string='Last Day 2', help='From 1 to 31')
    insurance_start_day_3 = fields.Integer(string='Insurance Start/Resume Day 3', help='From 1 to 31')
    insurance_end_day_3 = fields.Integer(string='Last Day 3', help='From 1 to 31')
    insurance_start_day_4 = fields.Integer(string='Insurance Start/Resume Day 4', help='From 1 to 31')
    insurance_end_day_4 = fields.Integer(string='Last Day 4', help='From 1 to 31')
    insurance_start_day_5 = fields.Integer(string='Insurance Start/Resume Day 5', help='From 1 to 31')
    insurance_end_day_5 = fields.Integer(string='Last Day 5', help='From 1 to 31')

    # Worked days and hours
    insured_days_total = fields.Integer(string='Total Insured Days', required=True)
    worked_days_with_insurance = fields.Integer(string='Worked and Other Days with Insurance Contributions')
    sick_leave_days = fields.Integer(string='Days of Temporary Disability or with Compensation')
    child_care_days = fields.Integer(string='Child Care Days')
    days_without_insurance = fields.Integer(string='Days without Insurance Contributions, Counted for Insurance Length')
    unpaid_leave_days = fields.Integer(string='Unpaid Leave Days, Counted for Insurance Length')
    sick_leave_days_with_employer_salary = fields.Integer(string='Days of Temporary Disability with Employer Salary')

    # Hours
    worked_hours_total = fields.Integer(string='Total Worked Hours')
    overtime_hours = fields.Integer(string='Overtime Hours')

    # Qualification group and economic activity
    qualification_group = fields.Integer(string='Qualification Group Number', help='NKPD Nomenclature')
    economic_activity_code = fields.Char(string='Economic Activity Code of the Insured Person',
                                         help='KID 2008 Nomenclature', size=4)
    main_economic_activity = fields.Integer(string='Main Economic Activity Number', help='Nomenclature')
    working_time_code = fields.Char(string='Summarized Working Time Calculation Code', size=4, help='From 0 to 12')

    # Income and insurance
    health_insurance_income = fields.Float(string='Income for Health Insurance under Art. 40, Par. 1, Item 5 of HIA')
    health_insurance_rate_employer = fields.Float(string='% Health Insurance at Insurer Expense on Item 17',
                                                  digits=(5, 2))

    insurance_income = fields.Float(string='Insurable Income with Contributions', digits=(7, 2), required=True)
    doo_insurance_rate_employer = fields.Float(string='% State Social Insurance at Employer Expense', digits=(5, 2))
    doo_insurance_rate_employee = fields.Float(string='% State Social Insurance at Insured Person Expense',
                                               digits=(5, 2))
    health_insurance_rate_base_employer = fields.Float(string='% Health Insurance on Item 21 at Employer Expense',
                                                       digits=(5, 2))
    health_insurance_rate_base_employee = fields.Float(string='% Health Insurance on Item 21 at Insured Person Expense',
                                                       digits=(5, 2))
    tzpb_rate = fields.Float(string='% Work Accident and Occupational Disease Fund', digits=(5, 2))

    teacher_pension_fund_rate = fields.Float(string='% Teachers Pension Fund', digits=(5, 2))
    professional_pension_fund_rate = fields.Float(string='% Professional Pension Fund', digits=(5, 2))
    universal_pension_fund_rate_employer = fields.Float(string='% Universal Pension Fund at Employer Expense',
                                                        digits=(5, 2))
    universal_pension_fund_rate_employee = fields.Float(string='% Universal Pension Fund at Insured Person Expense',
                                                        digits=(5, 2))

    health_only_income = fields.Float(string='Income Subject to Health Insurance Only', digits=(7, 2))
    health_only_rate = fields.Float(string='% Health Insurance on Item 27', digits=(5, 2))

    # Salary and tax
    gross_salary = fields.Float(string='Gross Salary', digits=(9, 2), required=True)
    guaranteed_fund_rate = fields.Float(string='% Guaranteed Employee Claims Fund', digits=(5, 2))
    taxable_income = fields.Float(string='Monthly Taxable Income', digits=(9, 2))
    monthly_tax = fields.Float(string='Monthly Tax', digits=(8, 2))
    net_salary = fields.Float(string='Net Salary', digits=(9, 2))

    # Technical fields
    insurance_fund_code = fields.Integer(string='Insurance Fund Code', default=0)
    source_flag = fields.Char(string='Source Flag', help='BULSTAT UIC of the developer or insurance fund')

    @api.depends('employee_id.name')
    def _compute_family_name(self):
        for rec in self:
            if not rec.employee_id.name:
                rec.family_name = ''
                continue

            # Get the last part of the name as the family name
            name_parts = rec.employee_id.name.split()
            if name_parts:
                rec.family_name = name_parts[-1]
            else:
                rec.family_name = ''

    @api.depends('employee_id.name')
    def _compute_initials(self):
        for rec in self:
            if not rec.employee_id.name:
                rec.initials = ''
                continue

            # Get initials from name parts (excluding the last part which is family name)
            name_parts = rec.employee_id.name.split()
            initials = ''

            # Take first letter from each part except the last one (family name)
            for i in range(len(name_parts) - 1):
                if name_parts[i]:
                    initials += name_parts[i][0]

            # Limit to 2 characters as per requirements
            rec.initials = initials[:2]
