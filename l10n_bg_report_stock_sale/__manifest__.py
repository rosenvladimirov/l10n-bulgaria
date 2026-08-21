{
    "name": "Bulgarian Acceptance Protocol — Sale Order Bridge",
    "version": "19.0.1.0.0",
    "license": "AGPL-3",
    "category": "Sales/Sales",
    "author": "Rosen Vladimirov, Terraros Commerce Ltd.",
    "website": "https://github.com/OCA/l10n-bulgaria",
    "summary": "Edit the acceptance protocol date and the person who drew it "
               "up directly on the sale order.",
    "description": """
Bulgarian Acceptance Protocol — Sale Order Bridge
=================================================

The acceptance protocol is a document of the *transfer*, so its date and its
author belong on ``stock.picking`` — that is where ``l10n_bg_report_stock``
stores them. The people who fill them in, however, work from the sale order.

This bridge exposes both values on the order without storing them a second
time: reading walks to the order's non-cancelled transfers, writing pushes the
value down to all of them. When the transfers disagree, the order shows nothing
rather than picking one value and implying the others carry it too.

Kept as a separate module so ``l10n_bg_report_stock`` does not have to depend
on ``sale`` for a convenience field.
""",
    "depends": [
        "l10n_bg_report_stock",
        "sale_stock",
    ],
    "data": ["views/sale_order_views.xml"],
    "auto_install": True,
    "installable": True,
}
