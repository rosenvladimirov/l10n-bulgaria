# Part of Odoo. See LICENSE file for full copyright and licensing details.
from itertools import groupby

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class FleetWayBill(models.Model):
    _name = 'fleet.vehicle.waybill'
    _description = 'Waybill for cal/truck'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.depends('waybill_lines')
    def _compute_totals(self):
        for record in self:
            record.total_quantity = 0.0
            record.total_fuel_quantity = 0.0
            for line in record.waybill_lines:
                record.total_quantity += line.quantity
                record.total_fuel_quantity += line.fuel_quantity
            # _logger.info("ROWS %s" % self.waybill_lines)
            if record.waybill_lines:
                # _logger.info("ODOMETER %s:%s" % (self.waybill_lines[-1].odometer_stop, self.odometer))
                if record.waybill_lines[0].odometer_start != 0:
                    record.odometer_start = record.waybill_lines[0].odometer_start
                if record.waybill_lines[-1].odometer_stop != 0 and record.waybill_lines[-1].odometer_stop > record.odometer:
                    record.odometer = record.waybill_lines[-1].odometer_stop

    name = fields.Char('Waybill reference', required=True, copy=False, readonly=True,
                       states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))
    date_waybill = fields.Date('Date', readonly=True, required=True, default=lambda self: fields.Date.today(),
                               states={'draft': [('readonly', False)], 'confirmed': [('readonly', False)]})
    vehicle_id = fields.Many2one('fleet.vehicle', 'Fleet', readonly=True,
                                 states={'draft': [('readonly', False)], 'confirmed': [('readonly', False)]})
    company_id = fields.Many2one('res.company', 'Company', readonly=True,
                                 states={'draft': [('readonly', False)], 'confirmed': [('readonly', False)]},
                                 default=lambda self: self.env['res.company']._company_default_get(
                                     'fleet.vehicle.waybill'))
    waybill_lines = fields.One2many('fleet.vehicle.waybill.line', 'waybill_id', 'Lines', readonly=True,
                                    states={'draft': [('readonly', False)], 'confirmed': [('readonly', False)]})
    driver_id = fields.Many2one('res.partner', 'Driver', copy=False, readonly=True,
                                states={'draft': [('readonly', False)], 'confirmed': [('readonly', False)]})
    fuel_type_id = fields.Many2one('product.product', related='vehicle_id.fuel_type_id', string='Fuel type')
    location_id = fields.Many2one('stock.location', 'Fuel tank location', related='vehicle_id.location_id')
    odometer_start = fields.Integer('Start odometer', compute="_compute_totals", store=True)
    odometer = fields.Integer('Last odometer', compute="_compute_totals", store=True)
    total_fuel_quantity = fields.Float('Total fuel quantity', compute="_compute_totals", store=True)
    total_quantity = fields.Float('Total quantity', compute="_compute_totals", store=True)
    stock_move_ids = fields.One2many('stock.move', 'waybill_id', 'Stock move', readonly=True,
                                     states={'draft': [('readonly', False)], 'confirmed': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft',
        copy=False, index=True, readonly=True, track_visibility='onchange',
        help=" * Draft: not confirmed yet and will not be scheduled until confirmed.\n"
             " * Confirmed: Checked by a manager or adviser.\n"
             " * Done: has been processed, can't be modified or cancelled anymore.\n"
             " * Cancelled: has been cancelled, can't be confirmed anymore.")
    count_stock_move = fields.Integer('Count moves', compute="_compute_count_stock_move")
    no_fuel_consumption = fields.Boolean('Without consumption')

    @api.multi
    def _compute_count_stock_move(self):
        for record in self:
            record.count_stock_move = len(record.stock_move_ids.ids)

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        for record in self:
            if record.vehicle_id and record.odometer == 0:
                record.odometer = record.vehicle_id.odometer

    @api.onchange('waybill_lines')
    def _onchange_waybill_lines(self):
        self._compute_totals()

    @api.multi
    def action_cancel(self):
        self.mapped('stock_move_ids').filtered(lambda r: r.state != 'cancel')._action_cancel()
        self.write({'state': 'cancel'})
        self.message_post(body=_('For %s has been canceled the waybill %s!') % (self.vehicle_id.name, self.name))
        return True

    @api.multi
    def action_assign(self):
        self.mapped('stock_move_ids').filtered(lambda r: r.state != 'cancel')._action_assign()
        self.write({'state': 'confirmed'})
        self.message_post(body=_('For %s has been confirmed the waybill %s!') % (self.vehicle_id.name, self.name))
        return True

    @api.multi
    def button_validate(self):
        self.ensure_one()
        if not self.waybill_lines:
            raise UserError(_('Please add some lines for roadmap'))
        self.write({'state': 'done'})
        self.with_context(dict(self._context, force_period_date=self.date_waybill)).mapped('stock_move_ids').filtered(
            lambda r: r.state != 'cancel')._action_done()
        self.message_post(body=_('For %s has been validated the pickings %s!') % (
        self.vehicle_id.name, '-'.join([x.name for x in self.stock_move_ids])))

    def prepare_stock_move_line_waybill_data(self, waybill, location_id=False, location_dest_id=False, owner_id=False):
        if not waybill.company_id.cons_location_id:
            raise UserError('Please set up a virtual fuel consumption location!')
        if not location_id:
            location_id = waybill.location_id
        if not location_dest_id:
            location_dest_id = waybill.company_id.cons_location_id
        res = []
        res_stock_move_line = {}
        stock_move = self.env['stock.move']
        lot_obj = self.env['stock.production.lot']
        curr_quant_ids = waybill.waybill_lines.filtered(lambda r: r.lot_id)
        if curr_quant_ids:
            for quant in curr_quant_ids:
                qty = quant.fuel_quantity
                lot_id = False
                if quant.lot_id:
                    lot_id = lot_obj.search(
                        [('product_id', '=', waybill.fuel_type_id.id), ('name', '=', quant.lot_id.name)])
                    if not lot_id:
                        lot_id = lot_obj.create({'name': quant.lot_id.name, 'product_id': waybill.fuel_type_id.id,
                                                 'use_date': quant.lot_id.use_date})

                stock_move_line = self.env['stock.move.line'].new({
                    # 'picking_id': curr_picking.id,
                    'product_id': waybill.fuel_type_id.id,
                    'product_uom_id': waybill.vehicle_id.fuel_type_uom_id.id,
                    'lot_id': lot_id and lot_id.id or False,
                    'location_id': location_id.id,
                    'location_dest_id': location_dest_id.id,
                    'qty_done': qty,
                    'owner_id': owner_id,
                    'ordered_qty': qty,
                    'date': fields.datetime.now(),
                })
                if not res_stock_move_line.get(waybill.fuel_type_id):
                    res_stock_move_line[waybill.fuel_type_id] = []
                res_stock_move_line[waybill.fuel_type_id].append(
                    (0, 0, stock_move_line._convert_to_write(stock_move_line._cache)))
        else:
            qty = sum([x.fuel_quantity for x in waybill.waybill_lines])
            stock_move_line = self.env['stock.move.line'].new({
                # 'picking_id': curr_picking.id,
                'product_id': waybill.fuel_type_id.id,
                'product_uom_id': waybill.vehicle_id.fuel_type_uom_id.id,
                'location_id': location_id.id,
                'location_dest_id': location_dest_id.id,
                'qty_done': qty,
                'owner_id': owner_id,
                'ordered_qty': qty,
                # 'date': fields.datetime.now(),
                'date': waybill.date_waybill,
            })
            if not res_stock_move_line.get(waybill.fuel_type_id):
                res_stock_move_line[waybill.fuel_type_id] = []
            res_stock_move_line[waybill.fuel_type_id].append(
                (0, 0, stock_move_line._convert_to_write(stock_move_line._cache)))

        if waybill.stock_move_ids:
            for product, lines in groupby(waybill.stock_move_ids.filtered(lambda r: r.state != 'cancel'),
                                          lambda l: l.product_id):
                qty = sum([x[2]['qty_done'] for x in res_stock_move_line[product]])
                for move in lines:
                    move_line = move._convert_to_write(move._cache)
                    if res_stock_move_line.get(product):
                        del move_line['product_qty']
                        move_line['ordered_qty'] = qty
                        move_line['product_uom_qty'] = qty
                        move_line['move_line_ids'] = [(5, 0, 0)] + res_stock_move_line[product]
                        res.append((1, move.id, move_line))
        else:
            qty = sum([x.fuel_quantity for x in waybill.waybill_lines])
            move = self.prepare_stock_move_waybill_data(waybill.fuel_type_id, qty, waybill, location_id=location_id,
                                                        location_dest_id=location_dest_id)
            if res_stock_move_line.get(waybill.fuel_type_id, False):
                move['move_line_ids'] = res_stock_move_line[waybill.fuel_type_id]
            res.append((0, 0, move._convert_to_write(move._cache)))
        return res

    def prepare_stock_move_waybill_data(self, product, qty, waybill, old_qty=0, location_id=False,
                                        location_dest_id=False):
        origin = ''
        if waybill:
            origin = _('%s' % waybill.name)
        name = '%s%s/%s>%s' % (
            origin,
            product.code and '/%s: ' % product.code or '/',
            location_id and location_id.name or '', location_dest_id and location_dest_id.name or '')
        stock_move = self.env['stock.move'].new({
            'name': name,
            'date': waybill.date_waybill,
            'accounting_date': waybill.date_waybill,
            'origin': origin,
            'waybill_id': waybill.id,
            'location_id': location_id and location_id.id or False,
            'location_dest_id': location_dest_id and location_dest_id.id or False,
            'product_id': product.id,
            'ordered_qty': qty + old_qty,
            'product_uom_qty': qty + old_qty,
            'product_uom': product.product_tmpl_id.uom_id.id,
        })
        return stock_move

    @api.multi
    def _get_fuel_amount_by_group(self):
        self.ensure_one()
        res = {}
        labels = dict(self.waybill_lines._fields['roadmap_type'].selection)
        for type, lines in groupby(self.waybill_lines, lambda r: r.roadmap_type):
            res.setdefault(type, {'name': labels.get(type), 'quantity': 0.0, 'fuel_quantity': 0.0})
            for line in lines:
                res[type]['quantity'] += line.quantity
                res[type]['fuel_quantity'] += line.fuel_quantity
        res = [(k, l['quantity'], l['fuel_quantity'], l['name']) for k, l in res.items()]
        return res

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'fleet.vehicle.waybill') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('fleet.vehicle.waybill') or _('New')
        res = super(FleetWayBill, self).create(vals)
        if 'no_fuel_consumption' in vals and vals['no_fuel_consumption']:
            values = self.prepare_stock_move_line_waybill_data(res, location_id=res.location_id,
                                                               location_dest_id=res.company_id.cons_location_id)
            res.write({
                'stock_move_ids': values,
            })
        # res._compute_totals()
        data = {'value': res.odometer, 'date': res.date_waybill, 'vehicle_id': res.vehicle_id.id}
        odometer = self.env['fleet.vehicle.odometer'].search([('vehicle_id', '=', res.vehicle_id.id),
                                                              ('date', '=', res.date_waybill)])
        if odometer:
            odometer.write(data)
        else:
            self.env['fleet.vehicle.odometer'].create(data)
        # perform_tracking = not self.env.context.get('mail_notrack') and vals.get('waybill_lines')
        # if perform_tracking:
        #     res.message_track(res.fields_get(['state']), {res.id: res.state})
        res.message_post(body=_('For %s has been added to the waybill %s!') % (res.vehicle_id.name, res.name))
        return res

    @api.multi
    def write(self, values):
        res = super(FleetWayBill, self).write(values)
        if values.get('waybill_lines') and not values.get('stock_move_ids'):
            for record in self:
                if 'no_fuel_consumption' in values and values['no_fuel_consumption'] or record.no_fuel_consumption:
                    vals = self.prepare_stock_move_line_waybill_data(record, location_id=record.location_id,
                                                                     location_dest_id=record.company_id.cons_location_id)
                    # _logger.info("VALS %s" % vals)
                    record.write({
                        'stock_move_ids': vals,
                    })
                # record._compute_totals()
                data = {'value': record.odometer, 'date': record.date_waybill, 'vehicle_id': record.vehicle_id.id}
                odometer = self.env['fleet.vehicle.odometer'].search([('vehicle_id', '=', record.vehicle_id.id),
                                                                      ('date', '=', record.date_waybill)])
                if odometer:
                    odometer.write(data)
                else:
                    self.env['fleet.vehicle.odometer'].create(data)
        return res

    @api.multi
    def unlink(self):
        for record in self:
            if record.state == 'done':
                raise UserError(_('First cancel up and then remove'))
            if record.stock_move_ids:
                record.stock_move_ids.filtered(lambda r: r.state == 'done')._action_cancel()
                record.stock_move_ids.filtered(lambda r: r.state in ('partially_available', 'assigned'))._do_unreserve()
                record.stock_move_ids.filtered(lambda r: r.state in ('draft', 'waiting', 'confirmed')).unlink()
        return super(FleetWayBill, self).unlink()


class FleetWayBillLine(models.Model):
    _name = 'fleet.vehicle.waybill.line'
    _description = 'Waybill lenes for car/truck'
    _order = 'odometer_start'

    waybill_id = fields.Many2one('fleet.vehicle.waybill', 'Waybill')
    description = fields.Char('Description')
    lot_id = fields.Many2one('stock.production.lot', 'Lot/SN')
    roadmap_ids = fields.Many2many('res.partner', string='Roadmap')
    odometer_start = fields.Integer('Odometer start')
    odometer_stop = fields.Integer('Odometer stop')
    quantity = fields.Integer('Distance')
    fuel_quantity = fields.Float('Fuel quantity')
    roadmap_type = fields.Selection([
        ('city', _('City fuel consumption')),
        ('suburban', _('Suburban fuel consumption'))
    ], 'Roadmap type', default='city')

    @api.onchange('odometer_start', 'odometer_stop')
    def _onchange_odometer(self):
        if self.odometer_start != 0 and self.odometer_stop != 0:
            self.quantity = self.odometer_stop - self.odometer_start
            self._onchange_quantity()
            self.waybill_id._compute_totals()
        # if self.odometer_stop != 0:
        #     self.waybill_id.odometer = self.odometer_stop

    @api.onchange('quantity', 'roadmap_type')
    def _onchange_quantity(self):
        if self.roadmap_type == 'city':
            self.fuel_quantity = self.quantity / 100 * self.waybill_id.vehicle_id.fuel_city_quantity
        elif self.roadmap_type == 'suburban':
            self.fuel_quantity = self.quantity / 100 * self.waybill_id.vehicle_id.fuel_suburban_quantity
        else:
            self.fuel_quantity = self.quantity / 100 * self.waybill_id.vehicle_id.fuel_city_quantity
