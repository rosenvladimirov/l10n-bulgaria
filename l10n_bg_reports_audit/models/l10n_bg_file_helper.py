#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import tempfile
import zipfile

from odoo import _, fields, models
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


def l10n_bg_lang(env, lang_modules="partner", field_name=""):
    if lang_modules == "partner":
        return (
            f"""CASE
           WHEN {field_name} ? 'bg_BG' THEN {field_name}#>>'{'bg_BG'}'
           WHEN {field_name} ? 'en_US' THEN {field_name}#>>'{'en_US'}'
           ELSE {field_name}::text
           END"""
            if field_name and env.company.is_l10n_bg_multilanguage.get("partner_multilang", '') == 'installed'
            else f"""{field_name}"""
        )
    elif lang_modules == "narration":
        return (
            """CASE
           WHEN am.l10n_bg_narration ? 'bg_BG' THEN am.l10n_bg_narration#>>'{bg_BG}'
           WHEN am.l10n_bg_narration ? 'en_US' THEN am.l10n_bg_narration#>>'{en_US}'
           ELSE am.l10n_bg_narration::text
           END"""
        )
    else:
        return (
            f"""CASE
           WHEN {field_name} ? 'bg_BG' THEN {field_name}#>>'{'bg_BG'}'
           WHEN {field_name} ? 'en_US' THEN {field_name}#>>'{'en_US'}'
           ELSE {field_name}::text
           END"""
            if field_name and env.company.is_l10n_bg_multilanguage.get("l10n_bg_multilang", '') == 'installed'
            else f"""{field_name}"""
        )

def l10n_bg_odoo_compatible_line(env, mode):
    l10n_bg_compatible_odoo = env.user.company_id.l10n_bg_odoo_compatible
    if l10n_bg_compatible_odoo and mode == "tag_22":
        return """"""
    elif not l10n_bg_compatible_odoo and mode == "tag_22":
        return """*-1"""

def l10n_bg_odoo_compatible(env, mode):
    l10n_bg_compatible_odoo = env.user.company_id.l10n_bg_odoo_compatible
    if l10n_bg_compatible_odoo and mode == "tag_20":
        return """(
    CASE
        WHEN SUM(accs.account_tag_22) <= 0 THEN
            ABS(SUM(accs.account_tag_22)) + SUM(accs.account_tag_23 + accs.account_tag_24 + accs.account_tag_21)
        ELSE
            SUM(-accs.account_tag_22) + SUM(accs.account_tag_23 + accs.account_tag_24 + accs.account_tag_21)
    END
)"""
    elif not l10n_bg_compatible_odoo and mode == "tag_20":
        return """
        SUM(accs.account_tag_21 + accs.account_tag_22 + accs.account_tag_23 + accs.account_tag_24)
"""
    elif l10n_bg_compatible_odoo and mode == "tag_22":
        return """(
    CASE
        WHEN SUM(accs.account_tag_22) < 0 THEN
            ABS(SUM(accs.account_tag_22))
        ELSE
            SUM(-accs.account_tag_22)
    END
        )"""
    elif not l10n_bg_compatible_odoo and mode == "tag_22":
        return """SUM(accs.account_tag_22)"""
    elif l10n_bg_compatible_odoo and mode == "tag_50":
        return """(
CASE
    WHEN SUM(accs.account_tag_22) >= 0 THEN
        CASE
            WHEN SUM(accs.account_tag_21 + accs.account_tag_22 + accs.account_tag_23 + accs.account_tag_24) - SUM(accp.account_tag_41 + accp.account_tag_42 + accp.account_tag_43) >= 0 THEN
                ABS(SUM(accs.account_tag_21 + accs.account_tag_22 + accs.account_tag_23 + accs.account_tag_24) - SUM(accp.account_tag_41 + accp.account_tag_42 + accp.account_tag_43))
            ELSE 0.00
        END
    ELSE
        CASE
            WHEN SUM(accs.account_tag_22) < 0 THEN
                ABS(SUM(accs.account_tag_22)) + SUM(accs.account_tag_23 + accs.account_tag_24 + accs.account_tag_21) - SUM(accp.account_tag_41 + accp.account_tag_42 + accp.account_tag_43)
            ELSE 0.00
    END
END
        )"""
    elif not l10n_bg_compatible_odoo and mode == "tag_50":
        return """SUM(accr.account_tag_50)"""
    elif l10n_bg_compatible_odoo and mode == "tag_60":
        return """(
    CASE
        WHEN SUM(accs.account_tag_21 + accs.account_tag_22 + accs.account_tag_23 + accs.account_tag_24) - SUM(accp.account_tag_41 + accp.account_tag_42 + accp.account_tag_43) > 0 THEN
            0.00
        ELSE
            ABS(SUM(accs.account_tag_21 + accs.account_tag_22 + accs.account_tag_23 + accs.account_tag_24) - SUM(accp.account_tag_41 + accp.account_tag_42 + accp.account_tag_43))
    END
)"""
    elif not l10n_bg_compatible_odoo and mode == "tag_60":
        return """SUM(accr.account_tag_60)"""


def _set_options(options, report_date_from, report_date_to):
    if not options:
        date_now = fields.Date.today().strftime("%Y-%m-%d")
        options = {
            "date": {
                "date_from": report_date_from or date_now,
                "date_to": report_date_to or date_now,
            },
            "unposted_in_period": False,
            "all_entries": False,
        }
    else:
        options["date"]["date_from"] = report_date_from or options["date"]["date_from"]
        options["date"]["date_to"] = report_date_to or options["date"]["date_to"]
    return options


def l10n_bg_where(env, report_options):
    date_now = fields.Date.to_string(fields.Date.today())
    date_from = report_options["date"].get("date_from") or date_now
    date_to = report_options["date"].get("date_to") or date_now
    date_from_date = fields.Date.from_string(date_from)
    tax_period = date_from_date.strftime("%Y%m")
    company_id = env.company.id
    unposted_in_period = report_options.get("unposted_in_period", False)
    all_entries = report_options["all_entries"]
    state = ["posted", "cancel"]
    tax_periods = [tax_period] if tax_period else []

    if not tax_period and date_from and not date_to:
        date_from_date = fields.Date.from_string(date_from)
        tax_period = date_from_date.strftime("%Y%m")

    elif not tax_period and date_to and not date_from:
        date_to_date = fields.Date.from_string(date_to)
        tax_period = date_to_date.strftime("%Y%m")

    elif date_from and date_to:
        date_from_date = fields.Date.from_string(date_from)
        date_to_date = fields.Date.from_string(date_to)
        tax_periods = list_months_between_dates(date_from_date, date_to_date)

    if unposted_in_period or all_entries:
        state.append("draft")

    return date_from, date_to, tax_period, tax_periods, company_id, state


def list_months_between_dates(start_date, end_date):
    """
    Returns a list of months in the format YYYYMM between two dates.
    """
    months = []
    current_date = start_date
    while current_date <= end_date:
        formatted_month = current_date.strftime("%Y%m")
        months.append(formatted_month)
        current_date += relativedelta(months=1)
    return months


def parce_str_2(value):
    value = value or ""
    return f'{value.ljust(2, " ")}'[:2]


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
    if value is None or value == "":
        return "".ljust(6, " ")
    value = fields.Date.from_string(value)
    return f"{value.strftime('%Y%m')}"[:6]


def parce_date_10(value):
    if value is None or value == "":
        return "".ljust(10, " ")
    value = fields.Date.from_string(value)
    return f"{value.strftime('%d/%m/%Y')}"[:10]


def convert_date_vies(value):
    # Extract year and month
    year = value[:4]
    month = value[4:]
    return f"{month}/{year}"[:7]


def parce_fload_4(value, arrangement="R"):
    value = value or 0.00
    if arrangement == "L":
        return f"{value:.2f}".ljust(4)[:4]
    return f"{value:.2f}".rjust(4)[:4]


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
    "info_tag_5": lambda value: parce_integer_15(value),
    "info_tag_6": lambda value: parce_integer_15(value),
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
    "account_tag_33": lambda value: parce_fload_4(value),
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
    "account_tag_10": lambda value: parce_fload_15_2(value), # 02-10* Общ размер на данъчните основи за облагане с ДДС: цифров (15)
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
    "info_tag_vhr_1": lambda value: value if value is not None else "",
    "info_tag_vhr_2": lambda value: convert_date_vies(value)
    if value is not None
    else "",
    "info_tag_vhr_3": lambda value: f"{value:d}".rjust(5) + "\r\n"
    if value is not None
    else "" + "\r\n",
    "info_tag_vdr_1": lambda value: value if value is not None else "",
    "info_tag_vdr_2": lambda value: parce_str_15(value) if value is not None else "",
    "info_tag_vdr_3": lambda value: parce_str_150(value) if value is not None else "",
    "info_tag_vdr_4": lambda value: parce_str_50(value) if value is not None else "",
    "info_tag_vdr_5": lambda value: value if value is not None else "",
    "info_tag_vdr_6": lambda value: parce_str_150(value) if value is not None else "",
    "info_tag_vdr_7": lambda value: parce_str_5_vies(value) + "\r\n"
    if value is not None
    else "" + "\r\n",
    "info_tag_vtr_1": lambda value: value if value is not None else "",
    "info_tag_vtr_2": lambda value: parce_str_15(value) if value is not None else "",
    "info_tag_vtr_3": lambda value: parce_str_150(value) if value is not None else "",
    "info_tag_vtr_4": lambda value: parce_str_200(value) + "\r\n"
    if value is not None
    else "" + "\r\n",
    "info_tag_ttr_1": lambda value: value,
    "account_tag_ttr_2": lambda value: f"{value:.2f}".rjust(12),
    "account_tag_ttr_3": lambda value: f"{value:.2f}".rjust(12),
}

L10N_BG_VIES_LINES_FIELDS = {
    "info_tag_vir_1": lambda value: value,
    "info_tag_vir_2": lambda value: f"{value:d}".rjust(5),
    "info_tag_vir_3": lambda value: parce_str_15(value),
    "account_tag_vir_4": lambda value: f"{value:.2f}".rjust(12),
    "account_tag_vir_5": lambda value: f"{value:.2f}".rjust(12),
    "account_tag_vir_6": lambda value: f"{value:.2f}".rjust(12) + "       ",
}

L10N_BG_REPORTS = {
    "declaration": {
        "file_name": "Deklar.txt",
        "fields": L10N_BG_DECLARATION_FIELDS,
        "sql": "account.bg.vat.info.declar",
    },
    "purchase": {
        "file_name": "Pokupki.txt",
        "fields": L10N_BG_PURCHASES_FIELDS,
        "sql": "account.bg.info.purchases.line",
    },
    "sales": {
        "file_name": "Prodagbi.txt",
        "fields": L10N_BG_SALES_FIELDS,
        "sql": "account.bg.info.sale.line",
    },
    "vies": {
        "file_name": "Vies.txt",
        "fields": L10N_BG_VIES_FIELDS,
        "sql": "account.bg.vies.info.declar",
    },
    "vies_lines": {
        "file_name": "Vies.txt",
        "fields": L10N_BG_VIES_LINES_FIELDS,
        "sql": "account.bg.calc.vies.line",
    }
}


def get_l10n_bg_applicability():
    return [
        ("declaration", _("Declaration")),
        ("purchase", _("Purchase report")),
        ("sale", _("Sale report")),
        ("vies", _("VIES Report")),
    ]


def get_doc_type():
    return [
        ("01", _("Invoice")),
        ("02", _("Debit note")),
        ("03", _("Credit note")),
        ("04", _("Storeable goods sent to EU")),
        # Register of goods under the regime of storage of goods on demand,
        # sent or transported from the territory of the country to the territory of another member state
        ("05", _("Storeable goods receive from EU")),
        ("07", _("Customs declarations")),
        # Customs declaration/customs document certifying completion of customs formalities
        ("09", _("Protocols or other")),
        ("11", _("Invoice - cash reporting")),
        ("12", _("Debit notice - cash reporting")),
        ("13", _("Credit notice - cash statement")),
        ("50", _("Protocols fuel supplies")),
        ("81", _("Sales report - tickets")),
        (
            "82",
            _("Special tax order"),
        ),  # Report on the sales made under a special tax order
        ("83", _("sales of bread")),  # Report on the sales of bread
        ("84", _("Sales of flour")),  # Report on the sales of flour
        (
            "23",
            _("Credit note art. 126b"),
        ),  # Credit notification under Art. 126b, para. 1 of VAT
        (
            "29",
            _("Protocol under Art. 126b"),
        ),  # Protocol under Art. 126b, para. 2 and 7 of VAT
        (
            "91",
            _("Protocol under Art. 151c"),
        ),  # Protocol for the required tax under Art. 151c, para. 3 of the law
        ("92", _("Protocol under Art. 151g")),
        # Protocol on the tax credit under Art. 151g,
        # para. 8 of the law or a report under Art. 104g, para. 14
        ("93", _("Protocol under Art. 151c")),
        # Protocol for the required tax under Art. 151c,
        # para. 7 of the law with a delivery recipient who does not apply the special regime
        ("94", _("Protocol under Art. 151c, para. 7")),
        # Protocol for the required tax under Art. 151c,
        # para. 7 of the law with a delivery recipient, a person who applies the special regime
        ("95", _("Protocol for free provision of foodstuffs")),
        # Protocol for free provision of foodstuffs, to which Art. 6, para. 4, item 4 VAT
    ]


def get_type_vat():
    return [
        ("standard", _("Accounting document")),
        ("117_protocol", _("Art. 117 - Protocols")),
        ("119_report", _("Art. 119 - Report for sales")),
        # ('120_sales_report', _('Art. 119 - Report for sales-special rules')),
        # ('120_purchase_report', _('Art. 119 - Report for purchase-special rules')),
        ("in_customs", _("Import Customs declaration")),
        ("out_customs", _("Export Customs declaration")),
        ("dropship", _("Dropship/Try party deal")),
    ]


def get_delivery_type():
    return [
        ("01", _("Delivery under Part I of Annex 2 of VAT")),
        ("02", _("Delivery under Part II of Annex 2 of VAT")),
        ("03", _("Import under Annex 3 of VAT")),
        ("07", _("Supply, import or IC acquisition of bread")),
        ("08", _("Supply, import or IC acquisition of flour")),
        (
            "51",
            _(
                "Arrival of goods on the territory of the country under "
                "the regime of storage of goods until demand under Art. 15a of VAT"
            ),
        ),
        (
            "53",
            _(
                "Replacement of the person for whom the goods were intended without "
                "termination of the contract under Art. 15a, para. 4 of VAT"
            ),
        ),
        (
            "54",
            _("Marriage/absence/destruction of goods under Art. 15a, para. 10 of VAT"),
        ),
        (
            "58",
            _(
                "Termination of the contract under the mode of storage of goods until requested under Art. 15a of VAT"
            ),
        ),
    ]


class AuditExportFileHelper(models.AbstractModel):
    _name = "l10n.bg.export.file"
    _description = "Audit Reports File Helper"

    report_date_from = fields.Date(string="From")
    report_date_to = fields.Date(string="To")

    def _get_csvs(self, report_type, options=None):
        lines = []
        reports = L10N_BG_REPORTS.get(report_type, {})
        fields_to_export = reports.get("fields")
        file_name = reports.get("file_name")

        for line in self._get_l10n_bg_results(report_type, options=options):
            new_line = {}
            for field, helper in fields_to_export.items():
                val = line.get(field)
                if isinstance(val, dict):
                    val = list(val.values())[0]
                new_line[field] = helper(val)
            lines.append(new_line)

        line_csv = []
        for val in lines:
            content = ""
            for field in fields_to_export.keys():
                content += val[field]
            line_csv.append(content)
            # _logger.info(f"val: {val} content: {content}")
        return file_name, line_csv

    def get_csvs(self, report_type, options=None):
        file_name, line_csv = self._get_csvs(report_type, options=options)
        if line_csv:
            return file_name, ["\r\n".join(line_csv) + "\r\n"]
        else:
            return file_name, [""]

    def _get_l10n_bg_csv(self, l10n_bg_vat_report=False, options=None):
        files_report = {}
        l10n_bg_vat_report = l10n_bg_vat_report or []

        for report in l10n_bg_vat_report:
            fname, report_csv = self._get_csvs(report, options=options)
            if report == "vies":
                fname, report_csv_lines = self._get_csvs("vies_lines", options=options)
                report_csv = [
                    report_csv + report_csv_lines
                ]
            files_report[report] = {
                "file_name": fname,
                "file_content": [{'line': x} for x in report_csv],
            }
        return files_report

    def get_l10n_bg_csv(self, l10n_bg_vat_report=False, options=None):
        files_report = {}
        l10n_bg_vat_report = l10n_bg_vat_report or []

        for report in l10n_bg_vat_report:
            fname, report_csv = self.get_csvs(report, options=options)
            if report == "vies":
                fname, report_csv_lines = self.get_csvs("vies_lines", options=options)
                report_csv = [
                    report_csv[0] + report_csv_lines[0]
                ]
            files_report[report] = {
                "file_name": fname,
                "file_content": report_csv,
            }
        return files_report

    def _get_l10n_bg_results(self, tax_report, options=False):
        full_query = self._build_l10n_bg_query(tax_report, options=options)
        self._cr.execute(full_query, [])
        results = self._cr.dictfetchall()
        return results

    def _build_l10n_bg_query(self, tax_report, options=False):
        options = _set_options(options, self.report_date_from, self.report_date_to)

        sql_query = L10N_BG_REPORTS.get(tax_report, {}).get("sql", False)
        if not sql_query:
            return ""
        full_query = (
            self.env[sql_query]
            .with_context(**dict(self._context, report_options=options))
            ._table_query
        )
        _logger.warning(f"SQL QUERY {tax_report}: {full_query}")
        return full_query
