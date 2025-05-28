# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from collections import defaultdict
from contextlib import contextmanager
from multiprocessing.connection import default_family

from odoo import Command, _, api, fields, models
from odoo.addons.l10n_bg_tax_admin.models.partner import BG_MOVE_TYPES

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
    # ---------------
    # PROTOCOL FIELDS
    # ---------------
    l10n_bg_protocol_number = fields.Char(
        "Technical Protocol number",
        copy=False,
    )
    l10n_bg_protocol_move_id = fields.Many2one(
        "account.move.bg.protocol",
        "Protocol",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    # --------------------------
    # Private credit reverse VAT
    # --------------------------
    l10n_bg_private_number = fields.Char(
        "Technical Protocol number",
        copy=False,
    )
    l10n_bg_private_move_id = fields.Many2one(
        "account.move.bg.private",
        "Self signed Private VAT",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    # --------------------------
    # Customs moves VAT
    # --------------------------
    l10n_bg_customs_number = fields.Char(
        "Technical Protocol number",
        store=True,
    )
    l10n_bg_customs_move_id = fields.Many2one(
        "account.move.bg.customs",
        "Self signed Private VAT",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    l10n_bg_currency_rate = fields.Float(
        "Statistic Currency rate",
        # compute="_compute_l10n_bg_currency_rate",
        # inverse="_inverse_l10n_bg_currency_rate",
        # store=True,
        copy=False,
        default=1.0,
    )

    # --------------------------
    # COMPUTE METHODS
    # --------------------------
    @api.depends('fiscal_position_id')
    def _compute_l10n_bg_move_type(self):
        for move in self:
            if not move.fiscal_position_id:
                move.l10n_bg_move_type = 'standard'
            else:
                self._inverse_l10n_bg_move_type()

    def _inverse_l10n_bg_move_type(self):
        for move in self:
            if not move.l10n_bg_move_type or not move.fiscal_position_id:
                l10n_bg_move_type = 'standard'
            else:
                l10n_bg_move_type = move.l10n_bg_move_type

            new_fiscal_position = self.env['account.fiscal.position'].tax_action_map or defaultdict(dict)
            key_value = f"{move.move_type}-{move.fiscal_position_id.id}"

            if move.fiscal_position_id and move.l10n_bg_move_type != new_fiscal_position[key_value]['l10n_bg_type_vat']:
                l10n_bg_move_type = new_fiscal_position[key_value]['l10n_bg_type_vat']

            move.l10n_bg_move_type = l10n_bg_move_type

    @contextmanager
    def _sync_invoice(self, container):
        def get_defaults(mv):
            new_fiscal_position = self.env['account.fiscal.position'].tax_action_map or defaultdict(dict)
            key_value = f"{mv.move_type}-{mv.fiscal_position_id.id}"
            defaults = {}

            if new_fiscal_position.get(key_value):
                defaults = {
                    'l10n_bg_move_type': new_fiscal_position[key_value]['l10n_bg_type_vat'],
                    'l10n_bg_doc_type': new_fiscal_position[key_value]['l10n_bg_doc_type'],
                    'l10n_bg_narration': new_fiscal_position[key_value]['l10n_bg_narration'],
                }
                if mv.position_dest_id:
                    defaults.update({
                        'move_type': new_fiscal_position[key_value]['dest_move_type'],
                        'position_dest_id': new_fiscal_position[key_value]['position_dest_id'].id,
                        "line_ids": [Command.clear()],
                        'invoice_line_ids': [Command.clear()],
                    })
            return defaults, new_fiscal_position, key_value

        def reset_external(old, field_name=False):
            if not field_name:
                return {}
            delete_name = f"l10n_bg_{field_name}_move_id"
            if old[delete_name]:
                old[delete_name].unlink()
            return {
                f'l10n_bg_{field_name}_number': False,
                f'l10n_bg_{field_name}_date': False,
                f'l10n_bg_{field_name}_move_id': False,
            }

        def reset_external_all(old):
            values = {}
            for field_nm in ('customs', 'private', 'protocol'):
                values.update(reset_external(old, field_nm))
            return values

        def get_move_data(move):
            return {
                'fiscal_position_id': move.fiscal_position_id,
                'l10n_bg_move_type': move.l10n_bg_move_type,
                'l10n_bg_customs_number': move.l10n_bg_customs_number,
                'l10n_bg_customs_move_id': move.l10n_bg_customs_move_id,
                'l10n_bg_private_number': move.l10n_bg_private_number,
                'l10n_bg_private_move_id': move.l10n_bg_private_move_id,
                'l10n_bg_protocol_number': move.l10n_bg_protocol_number,
                'l10n_bg_protocol_move_id': move.l10n_bg_protocol_move_id,
            }

        def calculate_amount_currency(base_lines, factor_percent):
            amount_total = sum(line.amount_currency for line in base_lines)
            return amount_total * (factor_percent / 100)

        def prepare_move_line_values(invoice_id, account_id, amount_currency_total, currency_rate, tax_ids, nra_id):
            return Command.create({
                "display_type": "product",
                "account_id": account_id.id,
                "partner_id": nra_id.id,
                "currency_id": invoice_id.currency_id.id,
                "amount_currency": amount_currency_total,
                "balance": amount_currency_total * currency_rate,
                "tax_ids": [Command.set(tax_ids.ids)],
            })

        def get_tax_ids(account_id, invoice_id, position_dest_id, env):
            tax_ids = account_id.tax_ids.filtered(lambda tax: tax.type_tax_use == "purchase")
            if not tax_ids:
                tax_ids = invoice_id.company_id.account_purchase_tax_id
            if tax_ids and position_dest_id:
                map_id = env['account.fiscal.position'].browse(position_dest_id)
                tax_ids = map_id.map_tax(tax_ids)
            return tax_ids

        def process_destination_move(source_move, default_values, fiscal_position, doc_type, nra_id):
            if not default_values.get('position_dest_id'):
                return

            dest_key = f"{default_values['move_type']}-{default_values['position_dest_id'].id}"
            currency_rate = source_move.l10n_bg_currency_rate if doc_type == 'customs' else source_move.currency_rate
            partner_id = nra_id.id if doc_type == 'customs' else source_move.partner_id.id

            base_values = {
                "partner_id": partner_id,
                "partner_shipping_id": source_move.partner_shipping_id.id,
                f'l10n_bg_{doc_type}_move_id': source_move.id,
                f'l10n_bg_{doc_type}_number': getattr(source_move, f'l10n_bg_{doc_type}_number'),
                f'l10n_bg_{doc_type}_vat_date': getattr(source_move, f'l10n_bg_{doc_type}_vat_date'),
                'l10n_bg_type_vat': fiscal_position[dest_key]['l10n_bg_type_vat'],
                'l10n_bg_doc_type': fiscal_position[dest_key]['l10n_bg_doc_type'],
                'l10n_bg_narration': fiscal_position[dest_key]['l10n_bg_narration'],
                'invoice_line_ids': dest_aml(source_move, fiscal_position, currency_rate),
            }
            default_values.update(base_values)
            setattr(source_move, f'l10n_bg_{doc_type}_move_id', source_move.copy(default=default_values))

        def dest_aml(invoice_id, map_action, currency_rate):
            base_lines = invoice_id.invoice_line_ids.filtered(lambda r: r.display_type == "product")
            factor_percent = map_action.get('factor_percent', 100.0)
            currency_rate = currency_rate or 1.0

            amount_currency_total = calculate_amount_currency(base_lines, factor_percent)
            account_id = map_action.get('account_id') or invoice_id.company_id.account_journal_suspense_account_id
            tax_ids = get_tax_ids(account_id, invoice_id, map_action.get('position_dest_id'), self.env)

            return [
                prepare_move_line_values(invoice_id, account_id, amount_currency_total, currency_rate, tax_ids, nra_id)]

        before = {
            rec_move: get_move_data(rec_move)
            for rec_move in container['records'].filtered(lambda m: m.is_invoice(True))
        }

        with super()._sync_invoice(container):
            yield

        nra_id = self.env.ref("l10n_bg_tax_offices.nra", raise_if_not_found=False)

        for move in container['records'].filtered(lambda m: m.is_invoice(True)):
            if before[move]['l10n_bg_move_type'] == move.l10n_bg_move_type:
                continue

            default_values, fiscal_position, _ = get_defaults(move)
            vals = {
                field: default_values[field]
                for field in ('l10n_bg_type_vat', 'l10n_bg_doc_type', 'l10n_bg_narration')
                if field in default_values
            }

            if move.l10n_bg_move_type == 'standard':
                vals.update(reset_external_all(before[move]))
            elif move.l10n_bg_move_type == 'protocol':
                vals.update(reset_external(before[move], 'protocol'))
                vals.update({
                    'l10n_bg_protocol_move_id': self.env['account.move.bg.protocol'].create({
                        'l10n_bg_protocol_move_id': move.id,
                    })
                })
            elif move.l10n_bg_move_type == 'invoice_customs':
                process_destination_move(move, default_values, fiscal_position, 'customs', nra_id)
            elif move.l10n_bg_move_type == 'invoice_private':
                process_destination_move(move, default_values, fiscal_position, 'private', nra_id)

            if vals:
                move.write(vals)
