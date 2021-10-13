# Copyright 2009-2019 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError, RedirectWarning
from odoo.addons.report_xlsx_helper.report.report_xlsx_abstract \
    import ReportXlsxAbstract
import odoo.addons.decimal_precision as dp

from lxml import etree
import logging
_logger = logging.getLogger(__name__)
_render = ReportXlsxAbstract._render

class L10nBgIntrastatProductDeclaration(models.Model):
    _name = 'l10n.bg.intrastat.product.declaration'
    _description = "Intrastat Product Declaration for Bulgaria"
    _inherit = ['intrastat.product.declaration', 'mail.thread']

    computation_line_ids = fields.One2many(
        'l10n.bg.intrastat.product.computation.line',
        'parent_id', string='Intrastat Product Computation Lines',
        states={'done': [('readonly', True)]})
    declaration_line_ids = fields.One2many(
        'l10n.bg.intrastat.product.declaration.line',
        'parent_id', string='Intrastat Product Declaration Lines',
        states={'done': [('readonly', True)]})
    reporting_level_bg = fields.Selection(
        selection='_get_reporting_level_bg',
        string='BG Reporting Level',
        states={'done': [('readonly', True)]})

    @api.model
    def _get_reporting_level_bg(self):
        return [
            ('standard', _('Standard')),
            ('extended', _('Extended'))]

    def _get_statistical_amount(self, inv_line, amount_company_currency):
        # За статистически цели, при изпращания, в стойността на съответната стока се отчита по цени FOB, а при пристигания – по цени CIF.
        # Условията на доставка от типа EXW, FOB, FAS, FCA са условия без включени разходи за транспорт и застраховка. Ако при изпращания сте посочили във вашата декларация този # тип условия, то в тези случаи стойността по фактурата е равна на статистическата стойност.
        # Условията на доставка от типа CFR, CIF, CIP, DAP, DAT и CPT означават, че във фактурата са включени разходите за доставката на стоката и при пристигания фактурната
        # стойност ще е равна на статистическата.
        # При  изпращания при условия на доставка от тип СIF, означава, че когато декларирате статистическа стойност по Интрастат, трябва да намалите фактурната стойност с
        # разходите за транспорт и застраховка.
        # При пристигания с условия на доставка от тип FOB, означава, че за да декларирате статистическата стойност към фактурната стойност, трябва да добавите разходите за
        # транспорт и застраховка.
        inv = inv_line.invoice_id
        avg_sum_landed_cost = 0.0
        landed_cost = inv.invoice_line_ids.filtered(lambda r: r.product_id.intrastat_landed_cost)
        if landed_cost and amount_company_currency > 0:
            sum_landed_cost = sum([x.price_subtotal for x in landed_cost])
            coef = inv_line.price_subtotal / (inv.amount_untaxed - sum_landed_cost)
            avg_sum_landed_cost = sum_landed_cost * coef
            avg_sum_landed_cost = inv.currency_id.with_context(date=inv.date_invoice).compute(avg_sum_landed_cost,
                                                                                              self.company_id.currency_id)
        return avg_sum_landed_cost

    def _get_intrastat_transaction(self, inv_line):
        transaction = super()._get_intrastat_transaction(inv_line)
        if not transaction:
            transaction = self.env.ref('intrastat_product.intrastat_transaction_11')
        return transaction

    def _get_transport(self, inv_line):
        transport = inv_line.invoice_id.intrastat_transport_id \
            or self.company_id.intrastat_transport_id
        if not transport:
            msg = _(
                "The default Intrastat Transport Mode "
                "of the Company is not set, "
                "please configure it first.")
            self._account_config_warning(msg)
        return transport

    def _get_orgin_transport(self, inv_line):
        origin_transport = inv_line.invoice_id.origin_transport_id \
            or self.company_id.intrastat_origin_transport_id
        if not origin_transport:
            msg = _(
                "The default Intrastat Transport Origin "
                "of the Company is not set, "
                "please configure it first.")
            self._account_config_warning(msg)
        return origin_transport

    def _get_region(self, inv_line):
        module = __name__.split('addons.')[1].split('.')[0]
        region = super()._get_region(inv_line)
        if not region:
            delivery_partner_id = inv_line.invoice_id.get_delivery_partner_id()
            # self.ref('')
            delivery_address = self.env['res.partner'].browse([delivery_partner_id]).city_id
            if delivery_address:
                region = delivery_address.region_id
            if not region and delivery_address.municipality_id:
                region = delivery_address.municipality_id.region_id
            if not region:
                region = self.env.ref('%s.intrastat_region_bg_XXX' % module)
        if not region:
            msg = _("The Intrastat Region of the Company is not set, "
                "please configure it first.")
            # self._company_warning(msg)
        return region

    def _handle_refund(self, inv_line, line_vals):
        invoice = inv_line.invoice_id
        return_picking = invoice.picking_ids
        if return_picking:

            if invoice.type == 'in_refund':
                if self.type == 'arrivals':
                    if self.company_id.intrastat_dispatches == 'exempt':
                        line_vals.update({
                            'hs_code_id': self._credit_note_code.id,
                            'region_id': invoice.src_dest_region_id.id,
                            'transaction_id': False,
                            })
                    else:
                        line_vals.clear()
                else:
                    line_vals.update({
                        'region_id': invoice.src_dest_region_id.id,
                        'transaction_id': self._transaction_2.id,
                        })

            else:  # 'out_refund':
                if self.type == 'dispatches':
                    if self.company_id.intrastat_arrivals == 'exempt':
                        line_vals.update({
                            'hs_code_id': self._credit_note_code.id,
                            'region_id': invoice.src_dest_region_id.id,
                            'transaction_id': False,
                            })
                    else:
                        line_vals.clear()
                else:
                    line_vals.update({
                        'region_id': invoice.src_dest_region_id.id,
                        'transaction_id': self._transaction_2.id,
                        })
        else:
            # Manual correction of the declaration lines can be required
            # when the sum of the computation lines results in
            # negative values
            line_vals.update({
                'weight': -line_vals['weight'],
                'suppl_unit_qty': -line_vals['suppl_unit_qty'],
                'amount_company_currency':
                    -line_vals['amount_company_currency'],
                })

    def _update_computation_line_vals(self, inv_line, line_vals):
        super()._update_computation_line_vals(inv_line, line_vals)
        # handling of refunds
        # cf. NBB/BNB Intrastat guide 2016, Part,  I - Basis, par 9.6
        inv = inv_line.invoice_id
        if inv.type in ['in_refund', 'out_refund']:
            self._handle_refund(inv_line, line_vals)

        if line_vals:
            if self.type == 'dispatches':
                vat_number = self._sanitize_vat(inv.partner_id.vat)
                if not vat_number:
                    note = "\n" + _(
                        "Missing VAT Number on partner '%s'"
                        % inv.partner_id.name_get()[0][1])
                    self._note += note
                else:
                    line_vals['vat_number'] = vat_number
            origin_transport = self._get_orgin_transport(inv_line)
            incoterm = self._get_incoterm(inv_line)
            line_vals.update({
                'incoterm_id': incoterm.id,
                'origin_transport_id': origin_transport.id,
            })
            if self.type == 'arrivals':
                    avg_sum_landed_cost = self._get_statistical_amount(inv_line, line_vals.get('amount_company_currency', 0))
                    line_vals.update({
                        'amount_company_currency': self._get_amount(inv_line) + avg_sum_landed_cost,
                        'avg_sum_landed_cost': avg_sum_landed_cost,
                    })
            if self.reporting_level == 'extended':
                line_vals.update({
                    'amount_statistical_company_currency': self._get_amount(inv_line) +
                                                           self._get_statistical_amount(inv_line, line_vals.get('amount_company_currency', 0)),
                    # for future develope to add transport cost linked with incoterm
                })

    def _handle_invoice_accessory_cost(
            self, invoice, lines_current_invoice,
            total_inv_accessory_costs_cc, total_inv_product_cc,
            total_inv_weight):
        """
        In Belgue accessory cost should not be added.
        If transport costs and insurance costs are included in the price
        of the goods, you do not have to make any additional calculation
        or estimate in order to deduct them. If they are separately known
        (e.g. stated on a separate line on the invoice),
        transport and insurance costs may not be included in the value of
        the goods
        """
        pass

    def _gather_invoices_init(self):
        if self.company_id.country_id.code not in ('bg', 'BG'):
            raise UserError(
                _("The Bulgaria Intrastat Declaration requires "
                  "the Company's Country to be equal to 'Bulgaria'."))

        # module = __name__.split('addons.')[1].split('.')[0]

        # Special commodity codes
        # Current version implements only regular credit notes
        # special_code = '99600000' todo to check in NRA
        # hs_code = self.env['hs.code'].search(
        #    [('local_code', '=', special_code)])
        # if not hs_code:
        #    action = self.env.ref(
        #        '%s.intrastat_installer_action' % module)
        #    msg = _(
        #        "Intrastat Code '%s' not found. "
        #        "\nYou can update your codes "
        #        "via the Intrastat Configuration Wizard."
        #        ) % special_code
        #    raise RedirectWarning(
        #        msg, action.id,
        #        _("Go to the Intrastat Configuration Wizard."))
        # self._credit_note_code = hs_code[0]

        self._transaction_2 = self.env.ref(
            '%s.intrastat_transaction_2' % 'intrastat_product')

    def _prepare_invoice_domain(self):
        """
        Both in_ and out_refund must be included in order to cover
        - credit notes with and without return
        - companies subject to arrivals or dispatches only
        """
        domain = super()._prepare_invoice_domain()
        if self.type == 'arrivals':
            domain.append(
                ('type', 'in', ('in_invoice', 'in_refund')))
        elif self.type == 'dispatches':
            domain.append(
                ('type', 'in', ('out_invoice', 'out_refund')))
        return domain

    def _sanitize_vat(self, vat):
        return vat and vat.replace(' ', '').replace('.', '').upper()

    @api.model
    def _group_line_hashcode_fields(self, computation_line):
        res = super()._group_line_hashcode_fields(computation_line)
        # if self.type == 'arrivals':
            # del res['product_origin_country']
        if self.type == 'dispatches':
            res['vat_number'] = computation_line.vat_number
        res['incoterm'] = computation_line.incoterm_id.id or False
        res['origin_transport'] = computation_line.origin_transport_id.id or False
        return res

    @api.model
    def _prepare_grouped_fields(self, computation_line, fields_to_sum):
        vals = super()._prepare_grouped_fields(
            computation_line, fields_to_sum)
        if self.type == 'dispatches':
            vals['vat_number'] = computation_line.vat_number
        vals['incoterm_id'] = computation_line.incoterm_id.id
        vals['origin_transport_id'] = computation_line.origin_transport_id.id

        for field in fields_to_sum:
            if field == 'vat_number' or \
                    field == 'incoterm_id' or \
                    field == 'origin_transport_id':
                vals[field] = 0.0
        return vals

    def _fields_to_sum(self):
        fields_to_sum = super(L10nBgIntrastatProductDeclaration, self)._fields_to_sum()
        fields_to_sum += ['avg_sum_landed_cost']
        fields_to_sum += ['amount_statistical_company_currency']
        return fields_to_sum

    def _xls_computation_line_fields(self):
        res = super()._xls_computation_line_fields()
        i = res.index('product_origin_country')
        if self.type == 'dispatches':
            res.insert(i + 1, 'vat_number')
        # else:
        #     res.pop(i)
        res.append('incoterm_id')
        res.append('origin_transport_id')
        return res

    def _xls_declaration_line_fields(self):
        res = super()._xls_declaration_line_fields()
        if self.type == 'dispatches':
            i = res.index('hs_code')
            res.insert(i + 1, 'vat_number')
            res.insert(i + 1, 'product_origin_country')
        res.append('incoterm_id')
        res.append('origin_transport_id')
        if self.reporting_level == 'extended':
            i = res.index('amount_company_currency')
            res.insert(i + 1, 'amount_statistical_company_currency')
        return res

    def _xls_template(self):
        res = super()._xls_template()
        res['vat_number'] = {
            'header': {
                'type': 'string',
                'value': _('VAT Number'),
            },
            'line': {
                'value': _render(
                    "line.vat_number or ''"),
            },
            'width': 18,
        }
        return res

    @api.multi
    def _generate_xml(self):
        '''Generate the INSTAT XML file export.'''
        self = self.with_context(dict(self._context, lang=self.company_id.lang))

        self._check_generate_xml()
        # my_company_vat = self.company_id.partner_id.vat.replace(' ', '')

        my_company_currency = self.company_id.currency_id.name

        root = etree.Element('INSTAT')
        envelope = etree.SubElement(root, 'Envelope')

        create_date_time = etree.SubElement(envelope, 'DateTime')
        create_date = etree.SubElement(create_date_time, 'date')
        now_user_tz = fields.Datetime.context_timestamp(self, datetime.now())
        create_date.text = datetime.strftime(now_user_tz, '%Y-%m-%d')
        create_time = etree.SubElement(create_date_time, 'time')
        create_time.text = datetime.strftime(now_user_tz, '%H:%M:%S')

        party_contact = self.company_id.tax_contact_id.parent_id
        envelope_contact = self.company_id.tax_contact_id

        party = etree.SubElement(envelope, 'Party', partyType="PSI", partyRole="PSI")
        party_id = etree.SubElement(party, 'partyId')
        party_id.text = party_contact.uid
        party_name = etree.SubElement(party, 'partyIdType')
        party_name.text = party_contact.uid_type

        address = etree.SubElement(party, 'Address')
        address_street_number = etree.SubElement(address, 'streetNumber')
        address_street_number.text = party_contact.street_number
        addres_city = etree.SubElement(address, 'city')
        addres_city.text = party_contact.city
        addres_zip = etree.SubElement(address, 'postalCode')
        if not party_contact.zip:
            raise UserError(_(
                "The zip is not set "
                "for the company '%s'.") % party_contact.name)
        addres_zip.text = party_contact.zip

        addres_phone_number = etree.SubElement(address, 'phoneNumber')
        addres_phone_number.text = party_contact.phone and party_contact.phone or ''

        addres_fax_number = etree.SubElement(address, 'faxNumber')
        addres_fax_number.text = party_contact.fax and party_contact.fax or ''

        envelope_id = etree.SubElement(party, 'ContactPerson')
        if not envelope_contact:
            raise UserError(_(
                "The tax contact person is not set "
                "for the company '%s'.") % envelope_contact.name)
        envelope_name = etree.SubElement(envelope_id, 'contactPersonName')
        envelope_name.text = envelope_contact.name
        envelope_address = etree.SubElement(envelope_id, 'ContactPersonAddress')
        envelope_address_street_number = etree.SubElement(envelope_address, 'streetNumber')
        envelope_address_street_number.text = envelope_contact.street_number
        envelope_addres_city = etree.SubElement(envelope_address, 'city')
        envelope_addres_city.text = envelope_contact.city
        envelope_addres_zip = etree.SubElement(envelope_address, 'postalCode')
        envelope_addres_zip.text = envelope_contact.zip

        envelope_addres_phone_number = etree.SubElement(envelope_address, 'phoneNumber')
        envelope_addres_phone_number.text = envelope_contact.phone and envelope_contact.phone or ''

        envelope_addres_mobile = etree.SubElement(envelope_address, 'mobilePhoneNumber')
        envelope_addres_mobile.text = envelope_contact.mobile and envelope_contact.mobile or ''
        envelope_addres_mail = etree.SubElement(envelope_address, 'e-mail')
        envelope_addres_mail.text = envelope_contact.email and envelope_contact.email or ''

        declaration = etree.SubElement(envelope, 'Declaration')
        declaration_id = etree.SubElement(declaration, 'declarationId')
        declaration_id.text = self.year_month.replace('-', '')
        reference_period = etree.SubElement(declaration, 'referencePeriod')
        reference_period.text = self.year_month
        psi_id = etree.SubElement(declaration, 'PSIId')
        psi_id.text = self.company_id.uid
        psi_id = etree.SubElement(declaration, 'PSIIdType')
        psi_id.text = self.company_id.uid_type

        function = etree.SubElement(declaration, 'Function')
        function.text = 'REGULAR'  # Check it (REGULAR, CORRECTIVE, LEDGER)

        flow_code = etree.SubElement(declaration, 'flowCode')
        assert self.type in ('arrivals', 'dispatches'), \
            "The DEB must be of type 'Arrivals' or 'Dispatches'"
        if self.type == 'dispatches':
            flow_code.text = 'D'
        elif self.type == 'arrivals':
            flow_code.text = 'A'

        total_net_mass = etree.SubElement(declaration, 'totalNetMass')
        total_net_mass.text = str(sum([x.weight for x in self.declaration_line_ids]))
        total_invoiced_amount = etree.SubElement(declaration, 'totalInvoicedAmount')
        total_invoiced_amount.text = str(sum([x.amount_company_currency for x in self.declaration_line_ids]))
        total_statistical_value = etree.SubElement(declaration, 'totalStatisticalValue')
        total_statistical_value.text = str(int(sum([round(x.amount_statistical_company_currency, 0) for x in
                                                self.declaration_line_ids])))
        total_number_detailed_lines = etree.SubElement(declaration, 'totalNumberDetailedLines')
        total_number_detailed_lines.text = str(len(self.declaration_line_ids.ids))

        # THEN, the fields which vary from a line to the next
        if not self.declaration_line_ids:
            raise UserError(_(
                'No declaration lines. You probably forgot to generate '
                'them !'))
        line = 0
        for pline in self.declaration_line_ids:
            line += 1  # increment line number
            # print "line =", line
            assert pline.transaction_id, "Missing Intrastat Type"
            transaction = pline.transaction_id
            item = etree.SubElement(declaration, 'Item')
            item_number = etree.SubElement(item, 'itemNumber')
            item_number.text = str(line)
            # START of elements which are only required in "detailed" level

            cn8 = etree.SubElement(item, 'CN8')
            cn8_code = etree.SubElement(cn8, 'CN8Code')
            if not pline.hs_code_id:
                raise UserError(
                    _('Missing H.S. code on line %d.') % line)
            # local_code is required=True, so no need to check it
            cn8_code.text = pline.hs_code_id.local_code

            if self.type == 'arrivals':
                country_origin = etree.SubElement(item, 'countryOfOriginCode')
                if not pline.product_origin_country_id:
                    raise UserError(_(
                        'Missing product country of origin on line %d.')
                        % line)
                country_origin.text = pline.product_origin_country_id.code

            destination_country = etree.SubElement(item, 'MSConsDestCode')
            destination_country.text = pline.src_dest_country_id.code

            nationality_of_transport_vehicle = etree.SubElement(item, 'nationalityOfTransportVehicle')
            nationality_of_transport_vehicle.text = pline.origin_transport_id.code

            weight = etree.SubElement(item, 'netMass')
            if not pline.weight:
                raise UserError(
                    _('Missing weight on line %d.') % line)
            weight.text = str(pline.weight)

            invoiced_amount = etree.SubElement(item, 'invoicedAmount')
            if not pline.amount_company_currency:
                raise UserError(
                    _('Missing fiscal value on line %d.') % line)
            invoiced_amount.text = str(pline.amount_company_currency)

            statistical_value = etree.SubElement(item, 'statisticalValue')
            if not pline.amount_statistical_company_currency and self.reporting_level_bg == 'extended':
                raise UserError(
                    _('Missing statistical value on line %d.') % line)
            statistical_value.text = str(int(pline.amount_statistical_company_currency))

            quantity_in_SU = etree.SubElement(item, 'supplementaryUnit')
            if not pline.suppl_unit_qty:
                quantity_in_SU.text = str(0)
            else:
                quantity_in_SU.text = str(pline.suppl_unit_qty)

            transaction_nature = etree.SubElement(item, 'NatureOfTransaction')
            transaction_nature_a = etree.SubElement(transaction_nature, 'natureOfTransactionACode')
            transaction_nature_a.text = transaction.code[0]
            if len(transaction.code) >= 2:
                transaction_nature_b = etree.SubElement(transaction_nature, 'natureOfTransactionBCode')
                transaction_nature_b.text = transaction.code[1]

            mode_of_transport_code = etree.SubElement(item, 'modeOfTransportCode')
            if not pline.transport_id:
                raise UserError(_(
                    'Mode of transport is not set on line %d.') % line)
            mode_of_transport_code.text = str(pline.transport_id.code)
            region_code = etree.SubElement(item, 'regionCode')
            if not pline.region_id:
                raise UserError(
                    _('Department is not set on line %d.') % line)
            region_code.text = pline.region_id.code

            delivery_terms = etree.SubElement(item, 'DeliveryTerms')
            delivery_terms_code = etree.SubElement(delivery_terms, 'TODCode')
            if not pline.incoterm_id:
                raise UserError(
                    _('Incoterm is not set on line %d.') % line)
            delivery_terms_code.text = pline.incoterm_id.code
            # action = etree.SubElement(item, 'action') for develop

        number_of_declarations = etree.SubElement(envelope, 'numberOfDeclarations')
        number_of_declarations.text = str(1)  # for develop

        xml_string = etree.tostring(
            root, pretty_print=True, encoding='UTF-8', xml_declaration=True)
        # We validate the XML file against the official XML Schema Definition
        # Because we may catch some problems with the content
        # of the XML file this way

        # self._check_xml_schema(
        #     xml_string, 'l10n_bg_intrastat_product/data/deb.xsd')

        # Attach the XML file to the current object
        return xml_string


class L10nBgIntrastatProductComputationLine(models.Model):
    _name = 'l10n.bg.intrastat.product.computation.line'
    _inherit = 'intrastat.product.computation.line'

    parent_id = fields.Many2one(
        comodel_name='l10n.bg.intrastat.product.declaration',
        string='Intrastat Product Declaration',
        ondelete='cascade', readonly=True)
    declaration_line_id = fields.Many2one(
        comodel_name='l10n.bg.intrastat.product.declaration.line',
        string='Declaration Line', readonly=True)
    vat_number = fields.Char(
        string='VAT Number',
        help="VAT number of the trading partner")
    origin_transport_id = fields.Many2one(
        comodel_name='res.country',
        string='Country of transport',
        help='In which country the transport unit is registered')
    amount_statistical_company_currency = fields.Float(
        string='Additional for Statistical Value',
        digits=dp.get_precision('Account'),
        help="Addition amount for transport cost in company currency to write in the declaration. "
        "Amount in company currency = amount in invoice currency "
        "converted to company currency with the rate of the invoice date."
        "Statistical amount = amount in invoice currency + Additional for Statistical Value")
    avg_sum_landed_cost  = fields.Float(
        string='Additional landed cost',
        digits=dp.get_precision('Account'),
        help="Additional delivery costs mentioned in the invoice to the ICI")


class L10nBgIntrastatProductDeclarationLine(models.Model):
    _name = 'l10n.bg.intrastat.product.declaration.line'
    _inherit = 'intrastat.product.declaration.line'

    parent_id = fields.Many2one(
        comodel_name='l10n.bg.intrastat.product.declaration',
        string='Intrastat Product Declaration',
        ondelete='cascade', readonly=True)
    computation_line_ids = fields.One2many(
        comodel_name='l10n.bg.intrastat.product.computation.line',
        inverse_name='declaration_line_id',
        string='Computation Lines', readonly=True)
    vat_number = fields.Char(
        string='VAT Number',
        help="VAT number of the trading partner")
    origin_transport_id = fields.Many2one(
        comodel_name='res.country',
        string='Country of transport',
        help='In which country the transport unit is registered')
    amount_statistical_company_currency = fields.Float(
        string='Additional for Statistical Value',
        digits=dp.get_precision('Account'),
        help="Addition amount for transport cost in company currency to write in the declaration. "
        "Amount in company currency = amount in invoice currency "
        "converted to company currency with the rate of the invoice date."
        "Statistical amount = amount in invoice currency + Additional for Statistical Value")
    avg_sum_landed_cost  = fields.Float(
        string='Additional for landed cost',
        digits=dp.get_precision('Account'),
        help="Additional delivery costs mentioned in the invoice to the ICI")
