# Copyright 2026 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""cfx.endpoint.template — каталог на known CFX машинни типове."""

from odoo import fields, models

from .cfx_endpoint import MACHINE_KINDS, TRANSPORTS


class CfxEndpointTemplate(models.Model):
    _name = 'cfx.endpoint.template'
    _description = 'CFX Endpoint Template (machine-type catalog)'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    description = fields.Text()

    machine_kind = fields.Selection(
        MACHINE_KINDS, required=True, default='generic')
    default_transport = fields.Selection(
        TRANSPORTS, default='broker')
    default_topics = fields.Char(
        help='Default CFX topics for this machine type, '
             'space- or comma-separated.')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Template code must be unique.'),
    ]
