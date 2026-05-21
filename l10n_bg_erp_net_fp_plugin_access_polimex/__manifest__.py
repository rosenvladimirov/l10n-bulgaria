# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    'name': 'ErpNet.FP Fleet — Polimex Access Plugin',
    'summary': """
        Structured UI for Polimex iCON access controllers (split into reader/
        magnet/motor/sensor/button parts) — generates the access fragment
        YAML pushed to the hardware proxy.""",
    'description': """
Структуриран UI за Polimex iCON контролери за достъп. За оператора на
Odoo контролерът се вижда абстрактно — само номер + типове части
(reader, магнит, motor, sensor, бутон). За проксито YAML-ът съдържа
конкретните detail-и (host, bus_id, output channel, mode).

Логиката е на flat plug-in над erpnet.fp.proxy.config.template
(kind=access). При save се регенерира yaml_text в свързания template
запис; оператор натиска "Push" на template-а — проксито hot-reload-ва
config.d/access.yaml.

Структура:
  * polimex.controller  — bridge (web module) + bus controller. Един
    Polimex Web Device може да хоства до 31 контролера на RS-485.
  * polimex.part        — една 'функция' окачена на bridge-а: магнит,
    reader, motor, sensor, бутон. Свързана с output/input channel.

Plugin pattern — модулът е optional. Без него Polimex YAML се
поддържа ръчно в template form-а.
""",
    'version': '19.0.1.2.0',
    'license': 'LGPL-3',
    'author': 'Rosen Vladimirov,Odoo Community Association (OCA)',
    'website': 'https://github.com/rosenvladimirov/l10n-bulgaria',
    'category': 'Hardware/Fleet/Plugins',
    "development_status": "Alpha",
    'maintainers': ['rosenvladimirov'],
    'depends': [
        'l10n_bg_erp_net_fp_fleet',
    ],
    'external_dependencies': {
        'python': ['yaml'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/polimex_controller_views.xml',
        'views/polimex_part_views.xml',
        'views/menu_items.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
