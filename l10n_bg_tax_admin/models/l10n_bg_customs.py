
from odoo import models, fields, api


class CustomsNomenclature(models.Model):
    _name = 'l10n.bg.customs.nomenclature'
    _description = 'Митническа номенклатура'

    name = fields.Char('Наименование', required=True, translate=True)
    code = fields.Char('Код', required=True)
    type = fields.Selection([
        ('transport', 'Вид транспорт'),
        ('packaging', 'Вид опаковка'),
        ('document', 'Вид документ'),
        ('procedure', 'Митнически режим'),
    ], string='Тип номенклатура', required=True)
    description = fields.Text('Описание', translate=True)
    unece_code = fields.Char('UNECE Код', help='Код според номенклатурата на ИКЕ на ООН')
    active = fields.Boolean('Активен', default=True)
