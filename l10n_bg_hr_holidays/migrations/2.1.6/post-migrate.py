# Part of Odoo. See LICENSE file for full copyright and licensing details.
# DEF-40 (master/20.0): „Игнориране на официални празници" = Да за болничните
# work entry типове, така че официалните празници остават в периода на болничния
# (поемат се от НОИ като календарни дни).
#
# На master типът отсъствие Е work entry типът → флагът е на hr.work.entry.type.
# Директен SQL — заобикаля core constraint-а _check_overlapping_public_holidays
# (@api.constrains), който при ORM write би хвърлил ValidationError, ако има
# валидни отпуски върху празник в текущата година.
#
# N стойностите и l10n_bg_doo_treatment се прилагат от hr_holidays_doo_treatment.xml
# (noupdate=0) автоматично на -u — тук е само празничният флаг.


def migrate(cr, version):
    cr.execute(
        "UPDATE hr_work_entry_type "
        "SET include_public_holidays_in_duration = TRUE "
        "WHERE l10n_bg_doo_treatment IN "
        "('nssi_sick', 'nssi_work_accident', 'nssi_maternity')"
    )
