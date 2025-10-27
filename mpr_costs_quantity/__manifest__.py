{
    'name': 'MRP Labor Cost by Quantity',
    'version': '18.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Add quantity-based cost calculation method for work centers',
    'description': '''
   MRP Labor Cost by Quantity
   ==========================

   This module extends the manufacturing work center cost calculation with a new method
   based on produced quantity instead of time spent.

   Features:
   ---------
   * Add new cost method selection on work centers (hour-based or quantity-based)
   * Configure cost per single produced unit on work centers
   * Automatically calculate work order costs based on actual produced quantity
   * Preserve cost values at the time of work order completion for consistent accounting

   Use Cases:
   ----------
   * Suitable for operations where labor cost depends on output quantity rather than time
   * Useful for piece-rate or output-based costing scenarios
   * Provides more accurate costing for high-variability production processes
''',
    'author': 'Your Company',
    'depends': [
        'mrp',
        'mrp_account',
    ],
    'images': [
        'static/description/banner.png',
    ],
    'data': [
        'views/mrp_workcenter_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
