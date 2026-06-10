# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class HRLeaveType(models.Model):
    _inherit = 'hr.work.entry.type'

    l10n_bg_code = fields.Char(
        string='Code',
        help='Internal code for the leave type (e.g., KT155, NSSI01)',
        copy=False,
        index=True,
    )
    l10n_bg_allow_paid_days = fields.Boolean(
        string='Allow Paid Days',
        compute='_compute_l10n_bg_allow_paid_days',
        store=True,
        help='Technical field to determine if paid days can be specified for this leave type'
    )
    l10n_bg_paid_days_unpaid_leave = fields.Float(
        string='Paid Days',
        default=0.0,
        help='Number of days to be paid when the leave type is unpaid. '
             'These days will be deducted from the total unpaid days.',
        digits=(16, 1)
    )
    l10n_bg_leave_reason_id = fields.Many2one(
        'nssi.leave.reason',
        string='Leave Reason'
    )
    l10n_bg_carryover_lapse_years = fields.Integer(
        string="Carry-over Lapse (years)",
        default=0,
        help="Number of years after which unused paid annual leave of this "
             "type lapses (BG Labor Code art. 176a §2 — 2 years from the end "
             "of the year it is due for). When > 0, allocations of this type "
             "get a date_to set automatically (end of grant year + N), so the "
             "oldest entitlement is consumed first (FIFO). 0 = no lapse / "
             "open-ended (default). Set to 2 only for basic/additional annual "
             "paid leave (KT155 / KT156*)."
    )
    # ---------------------------------------------------------------------
    # БГ-законови лимити (КТ / КСО) — конфигурируеми на ниво leave type.
    # Stand-by ValidationError в hr_leave._check_l10n_bg_max_days.
    # Seed defaults в data/hr_holidays_data.xml; може да се override-нат
    # per company чрез inheritance ако КТД дава по-добри условия.
    # ---------------------------------------------------------------------
    l10n_bg_max_days_per_year = fields.Integer(
        string="Max Days per Year",
        default=0,
        help="Annual cap in working days (per calendar year, per employee). "
             "0 = no annual cap. "
             "Examples per Bulgarian law: care for sick family member "
             "(NSSI 07, KT chap. 167) — 10 days/year (КСО чл. 45, ал. 1, "
             "т. 2); service-counting unpaid leave (KT 160 §1) — 30 days/year; "
             "marriage / bereavement / blood donation (KT 157) — 2 days/event."
    )
    l10n_bg_max_days_total = fields.Integer(
        string="Max Days Total (per event/lifetime)",
        default=0,
        help="Total cap in working days — applies to a single event or to "
             "the employee's lifetime per this type. 0 = no total cap. "
             "Examples: maternity pregnancy and birth (NSSI 04, KT 163) — "
             "410 days total per pregnancy (КСО чл. 50, ал. 1); paternity "
             "(KT 163-10) — 15 days per child; final state exam (KT 170) — "
             "30 days per event."
    )
    l10n_bg_legal_reference = fields.Char(
        string="Legal Reference",
        help="Citation of the law and article that establishes the cap, "
             "e.g. 'КСО чл. 45, ал. 1, т. 2' or 'КТ чл. 160, ал. 1'. "
             "Shown to the user when ValidationError is raised on overflow."
    )

    l10n_bg_doo_treatment = fields.Selection([
        ('normal', 'Normal — employer DOO/ZO/UPF on wage'),
        ('nssi_maternity', 'NSSI-funded maternity (BG Labor Code arts. 163, 164, 163-10, 166)'),
        ('nssi_sick', 'NSSI-funded sick leave (after 3 employer-paid days, BG Labor Code art. 162)'),
        ('nssi_work_accident', 'NSSI-funded work accident / occupational disease (90%, Social Security Code art. 41)'),
        ('unpaid_no_doo', 'Unpaid > 30 days/year — excluded from DOO base'),
    ],
        string='DOO Treatment',
        default='normal',
        help='How this leave type interacts with social-security contributions. '
             '`normal` — employer pays DOO/ZO/UPF based on wage as usual. '
             '`nssi_maternity` — NSSI pays the benefit AND funds the social-security '
             'contributions; employer DOO base excludes these days '
             '(BG Social Security Code art. 50). '
             '`nssi_sick` — first 3 days employer-paid (70%), remainder NSSI-funded. '
             '`nssi_work_accident` — work accident / occupational disease; benefit rate '
             'is 90% (BG Social Security Code art. 41) and no minimum insurance '
             'length is required (art. 40 par. 1). '
             '`unpaid_no_doo` — unpaid leave above 30 days/year per BG Labor Code '
             'art. 160 par. 1 — excluded from DOO base entirely.'
    )

    @api.depends('count_as')
    def _compute_l10n_bg_allow_paid_days(self):
        """Compute whether paid days are allowed for this leave type.

        19.4 (master): hr.leave.type merged into hr.work.entry.type; the old
        time_type=='leave' is now count_as=='absence' (vs 'working_time').
        """
        for leave_type in self:
            leave_type.l10n_bg_allow_paid_days = leave_type.count_as == 'absence'

    @api.depends('l10n_bg_code', 'name')
    def _compute_display_name(self):
        """Префиксира името с НОИ/КТ кода, ако такъв е зададен.

        Старата имплементация използваше `code and f'[{code}] '` което при
        празен code оценява в False (булева стойност) → f-string записва
        низа "False" в display_name. Резултат: „FalseДопълнителни часове".
        Новата прави явна проверка и пропуска префикса когато кода липсва.
        """
        for record in self:
            if record.l10n_bg_code:
                record.display_name = f"[{record.l10n_bg_code}] {record.name or ''}"
            else:
                record.display_name = record.name or ""
