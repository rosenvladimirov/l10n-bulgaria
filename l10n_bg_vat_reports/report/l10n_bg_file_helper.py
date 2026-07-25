from odoo import api, models, fields, _
from dateutil.relativedelta import relativedelta

L10N_BG_ADDRESS_EXTEND = ["l10n_bg_city"]


def _l10n_bg_extend_address(env):
    return env["ir.module.module"].search(
        [
            ("name", "in", L10N_BG_ADDRESS_EXTEND),
            ("state", "=", "installed"),
        ],
        limit=1,
    )


def l10n_bg_extend_address(env, model="company_partner"):
    if _l10n_bg_extend_address(env):
        return f"""
LEFT JOIN res_city AS {model}_city
    ON {model}.city_id = {model}_city.id
        """
    return ""


def l10n_bg_get_tag_negate_sql(table_alias="account_account_tag"):
    return f"COALESCE({table_alias}.tax_negate, false) AS negate"


def _normalize_lang_code(lang_code):
    if not lang_code:
        return None
    if "{" in lang_code and "}" in lang_code and "#>>" in lang_code:
        start = lang_code.find("{") + 1
        end = lang_code.find("}")
        return lang_code[start:end]
    return lang_code


def l10n_bg_lang(
    env,
    field=None,
    lang_modules="partner",
    lang_code=None,
    fallback_code="en_US",
    field_name=None,
    use_city_join=False,
):
    if field is None and field_name:
        field = field_name

    if use_city_join and l10n_bg_extend_address(env) and lang_modules == "partner":
        if field == "company_partner.city":
            return """(CASE
        WHEN company_partner_city.name ? 'bg_BG' THEN company_partner_city.name#>>'{bg_BG}'
        WHEN company_partner_city.name ? 'en_US' THEN company_partner_city.name#>>'{en_US}'
        ELSE company_partner_city.name::text
        END)"""
        if field == "represent_partner.city":
            return """(CASE
        WHEN represent_partner_city.name ? 'bg_BG' THEN represent_partner_city.name#>>'{bg_BG}'
        WHEN represent_partner_city.name ? 'en_US' THEN represent_partner_city.name#>>'{en_US}'
        ELSE represent_partner_city.name::text
        END)"""

    if lang_modules == 'partner':
        has_multilang = env['ir.module.module'].search([
            ('name', '=', 'partner_multilang'),
            ('state', '=', 'installed')
        ], limit=1)
    else:
        has_multilang = env['ir.module.module'].search([
            ('name', 'in', ('l10n_bg_multilang', 'partner_multilang')),
            ('state', '=', 'installed')
        ], limit=1)

    if not has_multilang:
        return field

    lang_code = _normalize_lang_code(lang_code) or 'bg_BG'
    fallback_code = _normalize_lang_code(fallback_code)
    if fallback_code and fallback_code != lang_code:
        return f"COALESCE({field}#>>'{{{lang_code}}}', {field}#>>'{{{fallback_code}}}')"
    return f"{field}#>>'{{{lang_code}}}'"


def l10n_bg_odoo_compatible(env, mode):
    l10n_bg_odoo_compatible = env.user.company_id.l10n_bg_odoo_compatible
    if l10n_bg_odoo_compatible and mode == 'tag_20':
        return """(
                CASE
                    WHEN (
                            COALESCE(SUM(accs.account_tag_22), 0.0)
                        ) <= 0 THEN
                            ABS(COALESCE(SUM(accs.account_tag_22), 0.0)) + COALESCE(SUM(accs.account_tag_23 + accs.account_tag_24 + accs.account_tag_21), 0.0)
                    ELSE
                        COALESCE(SUM(-accs.account_tag_22), 0.0) + COALESCE(SUM(accs.account_tag_23 + accs.account_tag_24 + accs.account_tag_21), 0.0)
                END
            ) AS account_tag_20"""
    elif not l10n_bg_odoo_compatible and mode == 'tag_20':
        return """COALESCE(SUM(accs.account_tag_21 + accs.account_tag_22 + accs.account_tag_23 + accs.account_tag_24), 0.0) AS account_tag_20"""
    elif l10n_bg_odoo_compatible and mode == 'tag_22':
        return """(
            CASE
                WHEN (
                        SUM(accs.account_tag_22)
                    ) < 0 THEN
                        ABS(SUM(accs.account_tag_22))
                ELSE
                    SUM(-accs.account_tag_22)
            END
        ) AS account_tag_22"""
    elif not l10n_bg_odoo_compatible and mode == 'tag_22':
        return """SUM(accs.account_tag_22) AS account_tag_22"""
    elif l10n_bg_odoo_compatible and mode == 'tag_50':
        return """(
            (CASE
                WHEN (
                    SUM(accs.account_tag_22)
                ) >= 0 THEN
                    CASE
                        WHEN (
                            SUM(accs.account_tag_21 + accs.account_tag_22 + accs.account_tag_23 + accs.account_tag_24)
                                - SUM(accp.account_tag_41 + accp.account_tag_42 + accp.account_tag_43)
                        ) >= 0 THEN
                            ABS(SUM(accs.account_tag_21 + accs.account_tag_22 + accs.account_tag_23 + accs.account_tag_24)
                                - SUM(accp.account_tag_41 + accp.account_tag_42 + accp.account_tag_43))
                        ELSE 0.00
                    END
                ELSE
                    CASE
                        WHEN (
                            SUM(accs.account_tag_22)
                        ) < 0 THEN
                            ABS(SUM(accs.account_tag_22)) + SUM(accs.account_tag_23 + accs.account_tag_24 + accs.account_tag_21)
                                - SUM(accp.account_tag_41 + accp.account_tag_42 + accp.account_tag_43)
                        ELSE 0.00
                END
            END)
        ) AS account_tag_50"""
    elif not l10n_bg_odoo_compatible and mode == 'tag_50':
        return """SUM(accr.account_tag_50) AS account_tag_50"""
    elif l10n_bg_odoo_compatible and mode == 'tag_60':
        return """(
            CASE
                WHEN (
                    SUM(accs.account_tag_21 + accs.account_tag_22 + accs.account_tag_23 + accs.account_tag_24) -
                        SUM(accp.account_tag_41 + accp.account_tag_42 + accp.account_tag_43)
                ) > 0 THEN
                    0.00
                ELSE
                    ABS(
                        SUM(accs.account_tag_21 + accs.account_tag_22 + accs.account_tag_23 + accs.account_tag_24) -
                            SUM(accp.account_tag_41 + accp.account_tag_42 + accp.account_tag_43)
                    )
            END
        ) AS account_tag_60"""
    elif not l10n_bg_odoo_compatible and mode == 'tag_60':
        return """SUM(accr.account_tag_60) AS account_tag_60"""


def l10n_bg_where(env, report_options, return_tax_periods=False):
    if not return_tax_periods:
        date_from = report_options['date'].get('date_from')
        date_to = report_options['date'].get('date_to')
        base_date = date_from or date_to
        date_from_date = fields.Date.from_string(base_date) if base_date else fields.Date.today()
        tax_period = date_from_date.strftime('%Y%m')
        company_id = env.company.id
        unposted_in_period = report_options.get('unposted_in_period', False)
        all_entries = report_options.get('all_entries', False)
        state = ['posted', 'cancel']

        if unposted_in_period or all_entries:
            state.append('draft')
        return date_from, date_to, tax_period, company_id, state

    date_now = fields.Date.to_string(fields.Date.today())
    date_from = report_options['date'].get('date_from') or date_now
    date_to = report_options['date'].get('date_to') or date_now
    date_from_date = fields.Date.from_string(date_from)
    tax_period = date_from_date.strftime('%Y%m')
    company_id = env.company.id
    unposted_in_period = report_options.get('unposted_in_period', False)
    all_entries = report_options.get('all_entries', False)
    state = ['posted', 'cancel']

    tax_periods = [tax_period] if tax_period else []

    if not tax_period and date_from and not date_to:
        date_from_date = fields.Date.from_string(date_from)
        tax_period = date_from_date.strftime('%Y%m')

    elif not tax_period and date_to and not date_from:
        date_to_date = fields.Date.from_string(date_to)
        tax_period = date_to_date.strftime('%Y%m')

    elif date_from and date_to:
        date_from_date = fields.Date.from_string(date_from)
        date_to_date = fields.Date.from_string(date_to)
        tax_periods = list_months_between_dates(date_from_date, date_to_date)

    if unposted_in_period or all_entries:
        state.append('draft')

    return date_from, date_to, tax_period, tax_periods, company_id, state


def list_months_between_dates(start_date, end_date):
    months = []
    current_date = start_date
    while current_date <= end_date:
        formatted_month = current_date.strftime('%Y%m')
        months.append(formatted_month)
        current_date += relativedelta(months=1)
    return months


def parce_str_2(value):
    value = value or ""
    return f'{value.ljust(2, " ")}'[:2]


def parce_fload_4_2(value, arrangement="R"):
    value = value or 0.00
    if arrangement == "L":
        return f"{value:.2f}".ljust(4, " ")[:4]
    return f"{value:.2f}".rjust(4, " ")[:4]


def parce_str_5(value):
    value = value or ""
    return f'{value.ljust(5, " ")}'[:5]


def parce_str_5_vies(value):
    value = value or ""
    return f'{value.rjust(5, " ").rjust(5)}'[:5]


def parce_str_6(value):
    value = value or ""
    return f'{value.ljust(6, " ")}'[:6]


def parce_str_15(value):
    value = value or ""
    return f'{value.ljust(15, " ")}'[:15]


def parce_str_20(value):
    value = value or ""
    return f'{value.ljust(20, " ")}'[:20]


def parce_str_30(value):
    value = value or ""
    return f'{value.ljust(30, " ")}'[:30]


def parce_str_50(value):
    value = value or ""
    return f'{value.ljust(50, " ")}'[:50]


def parce_str_150(value):
    value = value or ""
    return f'{value.ljust(150, " ")}'[:150]


def parce_str_200(value):
    value = value or ""
    return f'{value.ljust(200, " ")}'[:200]


def parce_date_6(value):
    if value is None or value == '':
        return "".ljust(6, " ")
    value = fields.Date.from_string(value)
    return f"{value.strftime('%Y%m')}"[:6]


def parce_date_10(value):
    if value is None or value == '':
        return "".ljust(10, " ")
    value = fields.Date.from_string(value)
    return f"{value.strftime('%d/%m/%Y')}"[:10]


def convert_date_vies(value):
    # Extract year and month
    year = value[:4]
    month = value[4:]
    return f"{month}/{year}"[:7]


def parce_fload_4(value):
    value = value or 0.00
    return "{:.2f}".format(value).rjust(4)[:4]


def parce_fload_15_2(value, arrangement="R"):
    value = value or 0.00
    if arrangement == "L":
        return f"{value:.2f}".ljust(15, " ")[:15]
    return f"{value:.2f}".rjust(15, " ")[:15]


def parce_integer_4(value, arrangement="L"):
    value = value or 0
    if arrangement == "L":
        return f"{int(float(value))}".ljust(4, " ")[:4]
    return f"{int(float(value))}".rjust(4, " ")[:4]


def parce_integer_15(value, arrangement="L"):
    value = value or 0
    if arrangement == "L":
        return f"{int(float(value))}".ljust(15, " ")[:15]
    return f"{int(float(value))}".rjust(15, " ")[:15]


L10N_BG_DECLARATION_FIELDS = {
    "info_tag_1": lambda value: parce_str_15(value),
    "info_tag_2": lambda value: parce_str_50(value),
    "info_tag_3": lambda value: parce_str_6(value),
    "info_tag_4": lambda value: parce_str_50(value),
    "info_tag_5": lambda value: parce_integer_15(value, arrangement='R'),
    "info_tag_6": lambda value: parce_integer_15(value, arrangement='R'),
    "account_tag_10": lambda value: parce_fload_15_2(value),
    "account_tag_20": lambda value: parce_fload_15_2(value),
    "account_tag_11": lambda value: parce_fload_15_2(value),
    "account_tag_21": lambda value: parce_fload_15_2(value),
    "account_tag_12": lambda value: parce_fload_15_2(value),
    "account_tag_22": lambda value: parce_fload_15_2(value),
    "account_tag_23": lambda value: parce_fload_15_2(value),
    "account_tag_13": lambda value: parce_fload_15_2(value),
    "account_tag_24": lambda value: parce_fload_15_2(value),
    "account_tag_14": lambda value: parce_fload_15_2(value),
    "account_tag_15": lambda value: parce_fload_15_2(value),
    "account_tag_16": lambda value: parce_fload_15_2(value),
    "account_tag_17": lambda value: parce_fload_15_2(value),
    "account_tag_18": lambda value: parce_fload_15_2(value),
    "account_tag_19": lambda value: parce_fload_15_2(value),
    "account_tag_30": lambda value: parce_fload_15_2(value),
    "account_tag_31": lambda value: parce_fload_15_2(value),
    "account_tag_41": lambda value: parce_fload_15_2(value),
    "account_tag_32": lambda value: parce_fload_15_2(value),
    "account_tag_42": lambda value: parce_fload_15_2(value),
    "account_tag_43": lambda value: parce_fload_15_2(value),
    "account_tag_33": lambda value: parce_fload_4_2(value),
    "account_tag_40": lambda value: parce_fload_15_2(value),
    "account_tag_50": lambda value: parce_fload_15_2(value),
    "account_tag_60": lambda value: parce_fload_15_2(value),
    "account_tag_70": lambda value: parce_fload_15_2(value),
    "account_tag_71": lambda value: parce_fload_15_2(value),
    "account_tag_80": lambda value: parce_fload_15_2(value),
    "account_tag_81": lambda value: parce_fload_15_2(value),
    "account_tag_82": lambda value: parce_fload_15_2(value),
}

L10N_BG_PURCHASES_FIELDS = {
    "info_tag_2": lambda value: parce_str_15(value),
    "info_tag_1": lambda value: parce_str_6(value),
    "info_tag_3": lambda value: parce_integer_4(value, arrangement="R"),
    "info_tag_4": lambda value: parce_integer_15(value,  arrangement="R"),
    "info_tag_5": lambda value: parce_str_2(value),
    "info_tag_6": lambda value: parce_str_20(value),
    "info_tag_7": lambda value: parce_date_10(value),
    "info_tag_8": lambda value: parce_str_15(value),
    "info_tag_9": lambda value: parce_str_50(value),
    "info_tag_10": lambda value: parce_str_30(value),
    "account_tag_30": lambda value: parce_fload_15_2(value),
    "account_tag_31": lambda value: parce_fload_15_2(value),
    "account_tag_41": lambda value: parce_fload_15_2(value),
    "account_tag_32": lambda value: parce_fload_15_2(value),
    "account_tag_42": lambda value: parce_fload_15_2(value),
    "account_tag_43": lambda value: parce_fload_15_2(value),
    "account_tag_44": lambda value: parce_fload_15_2(value),
    "info_tag_45": lambda value: parce_str_2(value),
}

L10N_BG_SALES_FIELDS = {
    "info_tag_0": lambda value: parce_str_15(value), # 02-00 Идентификационен номер по ДДС на лицето: символен (15)
    "info_tag_1": lambda value: parce_str_6(value), # 02-01 Данъчен период: символен (6) ггггмм
    "info_tag_2": lambda value: parce_integer_4(value, arrangement="R"), # 02-02 Клон/обособено звено: цифров (4)
    "info_tag_3": lambda value: parce_integer_15(value, arrangement="R"), #  02-03 Пореден номер на документа в дневника: цифров (15)
    "info_tag_4": lambda value: parce_str_2(value), # 02-04 Вид на документа: символен (2)
    "info_tag_5": lambda value: parce_str_20(value), # 02-05 Номер на документа символен (20)
    "info_tag_6": lambda value: parce_date_10(value), # 02-06 Дата на документа: Дата (dd/mm/yyyy)
    "info_tag_7": lambda value: parce_str_15(value), # 02-07 Идентификационен номер на контрагента (получател): символен (15)
    "info_tag_8": lambda value: parce_str_50(value), # 02-08 Име на контрагента (получател): символен (50)
    "info_tag_9": lambda value: parce_str_30(value), # 02-09 Вид на стоката или обхват и вид на услугата - точно описание съгласно документа: символен (30)
    "account_tag_9": lambda value: parce_fload_15_2(value), # 02-10* Общ размер на данъчните основи за облагане с ДДС: цифров (15)
    "account_tag_20": lambda value: parce_fload_15_2(value), # 02-20* Всичко начислен ДДС: цифров (15)
    "account_tag_11": lambda value: parce_fload_15_2(value), # 02-11 Данъчна основа на облагаемите доставки със ставка 20 %, вкл. доставките при условията на дистанционни продажби, с място на изпълнение на територията на страната: цифров (15)
    "account_tag_21": lambda value: parce_fload_15_2(value), # 02-21 Начислен ДДС 20 %: цифров (15)
    "account_tag_12": lambda value: parce_fload_15_2(value), # 02-12 ДО на ВОП: цифров (15)
    "account_tag_26": lambda value: parce_fload_15_2(value), # 02-26 ДО по получените доставки по чл. 82, ал. 2 - 5 ЗДДС: цифров (15)
    "account_tag_22": lambda value: parce_fload_15_2(value), # 02-22 Начислен ДДС за ВОП и за получени доставки по чл. 82, ал. 2 - 5 ЗДДС: цифров (15)
    "account_tag_23": lambda value: parce_fload_15_2(value), # 02-23 Начислен данък за доставки на стоки и услуги за лични нужди: цифров (15)
    "account_tag_13": lambda value: parce_fload_15_2(value), # 02-13 ДО на облагаемите доставки със ставка 9 %: цифров (15)
    "account_tag_24": lambda value: parce_fload_15_2(value), # 02-24 Начислен ДДС 9 %: цифров (15)
    "account_tag_14": lambda value: parce_fload_15_2(value), # 02-14 ДО на доставките със ставка 0 % по глава трета от ЗДДС: цифров (15)
    "account_tag_15": lambda value: parce_fload_15_2(value), # 02-15 ДО на доставките със ставка 0 % на ВОД на стоки: цифров (15)
    "account_tag_16": lambda value: parce_fload_15_2(value), # 02-16 ДО на доставките със ставка 0 % по чл. 140, чл. 146, ал. 1 и чл. 173 ЗДДС: цифров (15)
    "account_tag_17": lambda value: parce_fload_15_2(value), # 02-17 Данъчна основа на доставки на услуги по чл. 21, ал. 2 ЗДДС, с място на изпълнение на територията на друга държава членка: цифров (15)
    "account_tag_18": lambda value: parce_fload_15_2(value), # 02-18 Данъчна основа на доставки по чл. 69, ал. 2 ЗДДС, вкл. данъчна основа на доставките при условията на дистанционни продажби, с място на изпълнение на територията на друга държава членка: цифров (15)
    "account_tag_19": lambda value: parce_fload_15_2(value), # 02-19 ДО на освободени доставки и освободените ВОП: цифров (15)
    "account_tag_25": lambda value: parce_fload_15_2(value), # 02-25 ДО на доставки като посредник в тристранни операции: цифров (15)
    "info_tag_27": lambda value: parce_str_2(value), # 02-27 Доставка по чл. 163а или внос по чл. 167а от ЗДДС: символен (2)
}

L10N_BG_VIES_FIELDS = {
    "info_tag_vhr_1": lambda value: value if value is not None else '',
    "info_tag_vhr_2": lambda value: convert_date_vies(value) if value is not None else '',
    "info_tag_vhr_3": lambda value: "{:d}".format(value).rjust(5) + "\r\n" if value is not None else '' + "\r\n",
    "info_tag_vdr_1": lambda value: value if value is not None else '',
    "info_tag_vdr_2": lambda value: parce_str_15(value) if value is not None else '',
    "info_tag_vdr_3": lambda value: parce_str_150(value) if value is not None else '',
    "info_tag_vdr_4": lambda value: parce_str_50(value) if value is not None else '',
    "info_tag_vdr_5": lambda value: value if value is not None else '',
    "info_tag_vdr_6": lambda value: parce_str_150(value) if value is not None else '',
    "info_tag_vdr_7": lambda value: parce_str_5_vies(value) + "\r\n" if value is not None else '' + "\r\n",
    "info_tag_vtr_1": lambda value: value if value is not None else '',
    "info_tag_vtr_2": lambda value: parce_str_15(value) if value is not None else '',
    "info_tag_vtr_3": lambda value: parce_str_150(value) if value is not None else '',
    "info_tag_vtr_4": lambda value: parce_str_200(value) + "\r\n" if value is not None else '' + "\r\n",
    "info_tag_ttr_1": lambda value: value,
    "account_tag_ttr_2": lambda value: "{:.2f}".format(value).rjust(12),
    "account_tag_ttr_3": lambda value: "{:.2f}".format(value).rjust(12),
}

L10N_BG_VIES_LINES_FIELDS = {
    "info_tag_vir_1": lambda value: value,
    "info_tag_vir_2": lambda value: "{:d}".format(value).rjust(5),
    "info_tag_vir_3": lambda value: parce_str_15(value),
    "account_tag_vir_4": lambda value: "{:.2f}".format(value).rjust(12),
    "account_tag_vir_5": lambda value: "{:.2f}".format(value).rjust(12),
    "account_tag_vir_6": lambda value: "{:.2f}".format(value).rjust(12) + "       "
}
