# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from collections import defaultdict
from contextlib import contextmanager

from odoo import Command, _, api, fields, models
from odoo.addons.l10n_bg_tax_admin.models.partner import BG_MOVE_TYPES
from odoo.addons.l10n_bg_reports_audit.models.l10n_bg_file_helper import (
    get_doc_type,
    get_type_vat,
)

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_bg_move_type = fields.Selection(
        BG_MOVE_TYPES,
        compute="_compute_l10n_bg_move_type",
        inverse="_inverse_l10n_bg_move_type",
        store=True,
        copy=False,
        index=True
    )

    # Add missing fields that are referenced in the code
    l10n_bg_type_vat = fields.Selection(
        selection=get_type_vat(),
        string="Type of VAT",
        default="standard",
        copy=False,
    )
    l10n_bg_doc_type = fields.Selection(
        selection=get_doc_type(),
        string="VAT type document",
        default="01",
        copy=False,
    )
    l10n_bg_name = fields.Char("Document Name", copy=False)
    l10n_bg_date = fields.Date("Document Date", copy=False)
    l10n_bg_narration = fields.Char("Narration", copy=False)

    # ---------------
    # PROTOCOL FIELDS
    # ---------------
    l10n_bg_protocol_move_id = fields.Many2one(
        "account.move.bg.protocol",
        "Protocol",
        readonly=True,
    )

    # --------------------------
    # Private credit reverse VAT
    # --------------------------
    l10n_bg_private_move_id = fields.Many2one(
        "account.move.bg.private",
        "Self signed Private VAT",
        readonly=True,
    )
    l10n_bg_private_percentage = fields.Float(
        "Percent for partly VAT credit",
        default=100.00
    )

    # --------------------------
    # Customs moves VAT
    # --------------------------
    l10n_bg_customs_number = fields.Char(
        "Technical Protocol number",
        store=True,
    )
    l10n_bg_customs_date = fields.Date(
        "Customs date", copy=False, default=fields.Date.today()
    )
    # Commented out until the model is created
    # l10n_bg_customs_move_id = fields.Many2one(
    #     "account.move.bg.customs",
    #     "Self signed Private VAT",
    #     readonly=True,
    # )
    l10n_bg_currency_rate = fields.Float(
        "Statistic Currency rate",
        copy=False,
        default=1.0,
    )

    # --------------------------
    # COMPUTE METHODS
    # --------------------------
    @api.depends('fiscal_position_id', 'state')
    def _compute_l10n_bg_move_type(self):
        for move in self:
            if not move.fiscal_position_id:
                move.l10n_bg_move_type = 'standard'
            else:
                move._inverse_l10n_bg_move_type()

    def _inverse_l10n_bg_move_type(self):
        for move in self.filtered(lambda r: r.state == 'draft'):
            if not move.l10n_bg_move_type or not move.fiscal_position_id:
                l10n_bg_move_type = 'standard'
            else:
                l10n_bg_move_type = move.l10n_bg_move_type

            fiscal_position_id = move.fiscal_position_id
            if fiscal_position_id:
                new_fiscal_position = move.fiscal_position_id.tax_action_map or defaultdict(dict)
                key_value = f"{move.move_type}-{fiscal_position_id.id}"

                if (new_fiscal_position.get(key_value) and
                    move.l10n_bg_move_type != new_fiscal_position[key_value]['l10n_bg_move_type']):
                    l10n_bg_move_type = new_fiscal_position[key_value]['l10n_bg_move_type']

            move.l10n_bg_move_type = l10n_bg_move_type

    @contextmanager
    def _sync_invoice(self, container):
        def get_defaults(mv, new_fiscal_position):
            key_value = f"{mv.move_type}-{mv.fiscal_position_id.id}"
            defaults = {}

            if new_fiscal_position.get(key_value):
                defaults = {
                    'l10n_bg_move_type': new_fiscal_position[key_value]['l10n_bg_move_type'],
                    'l10n_bg_doc_type': new_fiscal_position[key_value]['l10n_bg_doc_type'],
                    'l10n_bg_type_vat': new_fiscal_position[key_value]['l10n_bg_type_vat'],
                    'l10n_bg_narration': new_fiscal_position[key_value]['l10n_bg_narration'],
                    'dest_move_type': new_fiscal_position[key_value]['dest_move_type'],
                    'position_dest_id': new_fiscal_position[key_value]['position_dest_id'],
                    'account_id': new_fiscal_position[key_value]['account_id'],
                    'factor_percent': new_fiscal_position[key_value]['factor_percent'],
                }
            return defaults, new_fiscal_position, key_value

        def reset_external(old, field_name=False):
            if not field_name:
                return {}
            delete_name = f"l10n_bg_{field_name}_move_id"
            if old.get(delete_name) and old[delete_name]:
                old[delete_name].unlink()
            return {
                'l10n_bg_name': False,
                'l10n_bg_date': False,
                f'l10n_bg_{field_name}_move_id': False,
            }

        def reset_external_all(old):
            values = {}
            # Only reset existing fields - removed 'customs' since the model doesn't exist
            for field_nm in ('private', 'protocol'):
                values.update(reset_external(old, field_nm))
            return values

        def get_move_data(move):
            return {
                'fiscal_position_id': move.fiscal_position_id,
                'l10n_bg_move_type': move.l10n_bg_move_type,
                'l10n_bg_type_vat': move.l10n_bg_type_vat,
                # 'l10n_bg_customs_move_id': move.l10n_bg_customs_move_id,  # Commented out
                'l10n_bg_private_move_id': move.l10n_bg_private_move_id,
                'l10n_bg_protocol_move_id': move.l10n_bg_protocol_move_id,
                'l10n_bg_name': move.l10n_bg_name,
                'l10n_bg_date': move.l10n_bg_date,
            }

        def calculate_amount_currency(base_lines, factor_percent):
            amount_total = sum(line.get('amount_currency', 0) for line in base_lines)
            return amount_total * (factor_percent / 100)

        def prepare_move_line_values(invoice_id, account_id, amount_currency_total, currency_rate, tax_ids, res_nra_id):
            return Command.create({
                "display_type": "product",
                "account_id": account_id.id if hasattr(account_id, 'id') else account_id,
                "partner_id": res_nra_id.id if res_nra_id else False,
                "currency_id": invoice_id.currency_id.id,
                "amount_currency": amount_currency_total,
                "balance": amount_currency_total * currency_rate,
                "tax_ids": [Command.set(tax_ids.ids if tax_ids else [])],
            })

        def get_tax_ids(account_id, invoice_id, position_dest_id, env):
            if hasattr(account_id, 'tax_ids'):
                tax_ids = account_id.tax_ids.filtered(lambda tax: tax.type_tax_use == "purchase")
            else:
                tax_ids = env['account.tax']

            if not tax_ids:
                tax_ids = invoice_id.company_id.account_purchase_tax_id
            if tax_ids and position_dest_id:
                map_id = env['account.fiscal.position'].browse(position_dest_id)
                tax_ids = map_id.map_tax(tax_ids)
            return tax_ids

        before = {
            rec_move: get_move_data(rec_move)
            for rec_move in container['records'].filtered(lambda m: m.is_invoice(True))
        }

        with super()._sync_invoice(container):
            yield

        nra_id = self.env.ref("l10n_bg_tax_offices.nra", raise_if_not_found=False)

        for move in container['records'].filtered(lambda m: m.is_invoice(True)):
            new_move = self.env['account.move']
            l10n_bg_type_vat = move.l10n_bg_type_vat
            l10n_bg_move_type = move.l10n_bg_move_type
            if move.state != 'posted':
                continue

            l10n_bg_mapping = move.fiscal_position_id.tax_action_map or defaultdict(dict)

            default_values, fiscal_position, base_key_id = get_defaults(move, l10n_bg_mapping)
            vals = {
                field: default_values[field]
                for field in ('l10n_bg_doc_type', 'l10n_bg_narration', 'l10n_bg_type_vat')
                if field in default_values
            }

            if l10n_bg_move_type == 'standard':
                vals.update(reset_external_all(before[move]))
            elif l10n_bg_move_type == 'protocol':
                vals.update(reset_external(before[move], 'protocol'))
                try:
                    new_move = self.env['account.move.bg.protocol'].create({
                        'l10n_bg_protocol_move_id': move.id,
                    })
                    vals.update({
                        'l10n_bg_protocol_move_id': new_move.id,
                        'l10n_bg_name': getattr(new_move, 'l10n_bg_protocol_name', ''),
                        'l10n_bg_date': getattr(new_move, 'l10n_bg_protocol_date_creation', False),
                    })
                except Exception as e:
                    _logger.warning("Could not create protocol move: %s", e)

            elif l10n_bg_move_type == 'private':
                vals.update(reset_external(before[move], 'private'))
                try:
                    new_move = self.env['account.move.bg.private'].create({
                        'l10n_bg_private_move_id': move.id,
                    })
                    vals.update({
                        'l10n_bg_private_move_id': new_move.id,
                        'l10n_bg_name': getattr(new_move, 'l10n_bg_private_name', ''),
                        'l10n_bg_date': getattr(new_move, 'l10n_bg_private_date_creation', False),
                    })
                except Exception as e:
                    _logger.warning("Could not create private move: %s", e)

            if vals:
                move.write(vals)

    def action_open_protocol(self):
        self.ensure_one()
        if not self.l10n_bg_protocol_move_id:
            return {'type': 'ir.actions.act_window_close'}
        return {
            'name': _("Protocol Entry"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'res_model': 'account.move.bg.protocol',
            'res_id': self.l10n_bg_protocol_move_id.id,
            'target': 'current',
        }

    def action_open_private(self):
        self.ensure_one()
        if not self.l10n_bg_private_move_id:
            return {'type': 'ir.actions.act_window_close'}
        return {
            'name': _("Self Signed VAT - Entry"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'res_model': 'account.move.bg.private',
            'res_id': self.l10n_bg_private_move_id.id,
            'target': 'current',
        }
