# Copyright 2021 Rosen Vladimirov
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Bulgaria - Vehicle Waybill',
    'summary': """
        Waybill for Bulgaria with stock move""",
    'version': '11.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'Rosen Vladimirov, '
              'BioPrint Ltd., '
              'Odoo Community Association (OCA)',
    'website': 'https://github.com/rosenvladimirov/l10n_bg-locales',
    'depends': [
        'l10n_bg',
        'fleet',
        'stock',
        'fleet_vehicle_stock',
        'stock_warehouse_consumption',
    ],
    'data': [
        'views/fleet_waybill.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'report/report_fleet_waybill.xml',
        'views/res_config_settings.xml',
        'views/fleet_waybill.xml',
        'views/fleet_vehicle.xml',
        'views/waybill_report_views.xml',
    ],
    'demo': [
    ],
}
