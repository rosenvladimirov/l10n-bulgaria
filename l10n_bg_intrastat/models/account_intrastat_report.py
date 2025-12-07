# Part of Odoo. See LICENSE file for full copyright and licensing details.
from lxml import etree
from datetime import datetime as dt

from odoo import _, api, models, fields
from odoo.exceptions import UserError


class IntrastatReportCustomHandler(models.AbstractModel):
    _inherit = "account.intrastat.report.handler"

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)

        if self.env.company.partner_id.country_id.code != "BG":
            return

        xml_button = {
            "name": _("XML"),
            "sequence": 30,
            "action": "export_file",
            "action_param": "bg_intrastat_export_to_xml",
            "file_export_type": _("XML"),
        }
        options["buttons"].append(xml_button)
        options[
            "intrastat_grouped"
        ] = True  # We always activate the grouping for the belgian intrastat report

    def _show_region_code(self):
        if (
            self.env.company.account_fiscal_country_id.code == "BE"
            and not self.env.company.intrastat_region_id
        ):
            return False
        return super()._show_region_code()

    @api.model
    def bg_intrastat_export_to_xml(self, options):
        """Generate the INTRASTAT XML file export for Bulgaria."""
        report = self.env['account.report'].browse(options['report_id'])

        # Проверка за валиден период (месец или тримесечие)
        self._check_date_range(options, allow_quarterly=True)

        # Извличане на данни от отчета
        date_from = fields.Date.to_date(options['date']['date_from'])
        date_to = fields.Date.to_date(options['date']['date_to'])

        # Вземане на интрастат типа (пристигане или изпращане)
        include_arrivals, include_dispatches = self._determine_inclusion(options)

        if include_arrivals and include_dispatches:
            raise UserError(_('Please select only Arrival or Dispatch, not both.'))

        if not include_arrivals and not include_dispatches:
            raise UserError(_('Please select Arrival or Dispatch.'))

        flow_code = 'A' if include_arrivals else 'D'

        # Създаване на XML структура
        xml_string = self._bg_generate_xml_structure(options, report, date_from, flow_code)

        # Връщане на файл
        return {
            'file_name': f'intrastat_bg_{date_from.strftime("%Y%m")}.xml',
            'file_content': xml_string,
            'file_type': 'xml',
        }

    def _bg_generate_xml_structure(self, options, report, date_from, flow_code):
        """Създава XML структурата за български интрастат отчет."""
        company = self.env.company

        # Проверки за задължителни данни
        if company.country_id.code != 'BG':
            raise UserError(
                _("The Bulgaria Intrastat Declaration requires the Company's Country to be equal to 'Bulgaria'."))

        party_contact = company.l10n_bg_tax_contact_id and company.l10n_bg_tax_contact_id.parent_id
        if not party_contact:
            raise UserError(_("Tax contact person is not set for the company."))

        envelope_contact = company.l10n_bg_tax_contact_id
        if not envelope_contact:
            raise UserError(_("Tax contact person is not set for the company."))

        # Създаване на root елемент
        root = etree.Element('INSTAT')
        envelope = etree.SubElement(root, 'Envelope')

        # DateTime секция
        self._bg_add_datetime_section(envelope)

        # Party секция
        self._bg_add_party_section(envelope, party_contact, envelope_contact)

        # Declaration секция
        lines_data = self._bg_get_declaration_lines(options, report)
        self._bg_add_declaration_section(envelope, date_from, flow_code, lines_data, company)

        # Брой декларации
        number_of_declarations = etree.SubElement(envelope, 'numberOfDeclarations')
        number_of_declarations.text = '1'

        # Генериране на XML string
        xml_string = etree.tostring(
            root,
            pretty_print=True,
            encoding='UTF-8',
            xml_declaration=True
        )

        return xml_string

    def _bg_add_datetime_section(self, envelope):
        """Добавя DateTime секция към envelope."""
        create_date_time = etree.SubElement(envelope, 'DateTime')
        create_date = etree.SubElement(create_date_time, 'date')
        now_user_tz = fields.Datetime.context_timestamp(self, dt.now())
        create_date.text = now_user_tz.strftime('%Y-%m-%d')
        create_time = etree.SubElement(create_date_time, 'time')
        create_time.text = now_user_tz.strftime('%H:%M:%S')

    def _bg_add_party_section(self, envelope, party_contact, envelope_contact):
        """Добавя Party секция към envelope."""
        party = etree.SubElement(envelope, 'Party', partyType="PSI", partyRole="PSI")

        # Party ID
        party_id = etree.SubElement(party, 'partyId')
        party_id.text = party_contact.uid or ''
        party_id_type = etree.SubElement(party, 'partyIdType')
        party_id_type.text = party_contact.uid_type or ''

        # Address
        address = etree.SubElement(party, 'Address')
        address_street_number = etree.SubElement(address, 'streetNumber')
        address_street_number.text = party_contact.street_number or ''
        addres_city = etree.SubElement(address, 'city')
        addres_city.text = party_contact.city or ''
        addres_zip = etree.SubElement(address, 'postalCode')
        if not party_contact.zip:
            raise UserError(_("The zip is not set for the company '%s'.") % party_contact.name)
        addres_zip.text = party_contact.zip
        addres_phone_number = etree.SubElement(address, 'phoneNumber')
        addres_phone_number.text = party_contact.phone or ''
        addres_fax_number = etree.SubElement(address, 'faxNumber')
        addres_fax_number.text = party_contact.fax or ''

        # Contact Person
        envelope_id = etree.SubElement(party, 'ContactPerson')
        envelope_name = etree.SubElement(envelope_id, 'contactPersonName')
        envelope_name.text = envelope_contact.name

        envelope_address = etree.SubElement(envelope_id, 'ContactPersonAddress')
        envelope_address_street_number = etree.SubElement(envelope_address, 'streetNumber')
        envelope_address_street_number.text = envelope_contact.street_number or ''
        envelope_addres_city = etree.SubElement(envelope_address, 'city')
        envelope_addres_city.text = envelope_contact.city or ''
        envelope_addres_zip = etree.SubElement(envelope_address, 'postalCode')
        envelope_addres_zip.text = envelope_contact.zip or ''
        envelope_addres_phone_number = etree.SubElement(envelope_address, 'phoneNumber')
        envelope_addres_phone_number.text = envelope_contact.phone or ''
        envelope_addres_mobile = etree.SubElement(envelope_address, 'mobilePhoneNumber')
        envelope_addres_mobile.text = envelope_contact.mobile or ''
        envelope_addres_mail = etree.SubElement(envelope_address, 'e-mail')
        envelope_addres_mail.text = envelope_contact.email or ''

    def _bg_get_declaration_lines(self, options, report):
        """Извлича данните за декларационните редове."""
        # Използване на съществуващата логика за извличане на данни
        new_options = {**options, 'export_mode': 'file', 'unfold_all': True}
        lines = report._get_lines(new_options)

        declaration_lines = []
        for line in lines:
            if line.get('level') == 0:  # Само групирани редове
                continue

            # Извличане на колоните
            columns = line.get('columns', [])
            if not columns:
                continue

            line_data = {
                'commodity_code': self._bg_extract_column_value(line, 'commodity_code'),
                'vat_number': self._bg_extract_column_value(line, 'partner_vat'),
                'country_code': self._bg_extract_column_value(line, 'country_code'),
                'origin_country_code': self._bg_extract_column_value(line, 'intrastat_product_origin_country_code'),
                'origin_transport_code': self._bg_extract_column_value(line, 'transport_code'),
                'transaction_code': self._bg_extract_column_value(line, 'transaction_code'),
                'transport_code': self._bg_extract_column_value(line, 'transport_code'),
                'region_code': self._bg_extract_column_value(line, 'region_code'),
                'incoterm_code': self._bg_extract_column_value(line, 'incoterm_code'),
                'weight': self._bg_extract_column_value(line, 'weight'),
                'supplementary_units': self._bg_extract_column_value(line, 'supplementary_units'),
                'value': self._bg_extract_column_value(line, 'value'),
                'statistical_value': self._bg_extract_column_value(line, 'value'),  # Може да се модифицира при нужда
            }

            if line_data['commodity_code']:
                declaration_lines.append(line_data)

        return declaration_lines

    def _bg_extract_column_value(self, line, expression_label):
        """Извлича стойност от колона по expression_label."""
        for col in line.get('columns', []):
            if col.get('expression_label') == expression_label:
                value = col.get('no_format', col.get('name', ''))
                return value if value else ''
        return ''

    def _bg_add_declaration_section(self, envelope, date_from, flow_code, lines_data, company):
        """Добавя Declaration секция към envelope."""
        declaration = etree.SubElement(envelope, 'Declaration')

        # Declaration ID
        declaration_id = etree.SubElement(declaration, 'declarationId')
        declaration_id.text = date_from.strftime('%Y%m')

        # Reference Period
        reference_period = etree.SubElement(declaration, 'referencePeriod')
        reference_period.text = date_from.strftime('%Y-%m')

        # PSI ID
        psi_id = etree.SubElement(declaration, 'PSIId')
        psi_id.text = company.uid or ''
        psi_id_type = etree.SubElement(declaration, 'PSIIdType')
        psi_id_type.text = company.uid_type or ''

        # Function
        function = etree.SubElement(declaration, 'Function')
        function.text = 'REGULAR'

        # Flow Code
        flow_code_elem = etree.SubElement(declaration, 'flowCode')
        flow_code_elem.text = flow_code

        # Общи стойности
        total_net_mass = sum(float(line['weight'] or 0) for line in lines_data)
        total_invoiced_amount = sum(float(line['value'] or 0) for line in lines_data)
        total_statistical_value = sum(float(line['statistical_value'] or 0) for line in lines_data)

        total_net_mass_elem = etree.SubElement(declaration, 'totalNetMass')
        total_net_mass_elem.text = str(int(round(total_net_mass)))

        total_invoiced_amount_elem = etree.SubElement(declaration, 'totalInvoicedAmount')
        total_invoiced_amount_elem.text = str(int(round(total_invoiced_amount)))

        total_statistical_value_elem = etree.SubElement(declaration, 'totalStatisticalValue')
        total_statistical_value_elem.text = str(int(round(total_statistical_value)))

        total_number_detailed_lines_elem = etree.SubElement(declaration, 'totalNumberDetailedLines')
        total_number_detailed_lines_elem.text = str(len(lines_data))

        # Добавяне на Item елементи
        for line_number, line_data in enumerate(lines_data, start=1):
            self._bg_add_item_section(declaration, line_number, line_data, flow_code)

    def _bg_add_item_section(self, declaration, line_number, line_data, flow_code):
        """Добавя Item секция към declaration."""
        item = etree.SubElement(declaration, 'Item')

        # Item Number
        item_number = etree.SubElement(item, 'itemNumber')
        item_number.text = str(line_number)

        # CN8 Code
        cn8 = etree.SubElement(item, 'CN8')
        cn8_code = etree.SubElement(cn8, 'CN8Code')
        if not line_data['commodity_code']:
            raise UserError(_('Missing H.S. code on line %d.') % line_number)
        cn8_code.text = line_data['commodity_code']

        # VAT Number
        vin_number = etree.SubElement(item, 'vinNumber')
        if flow_code == 'D':  # Dispatch
            if not line_data['vat_number']:
                raise UserError(_('Missing partner VAT number on line %d.') % line_number)
            vin_number.text = line_data['vat_number']
        else:
            vin_number.text = ''

        # Country of Origin
        country_origin = etree.SubElement(item, 'countryOfOriginCode')
        if not line_data['origin_country_code']:
            raise UserError(_('Missing product country of origin on line %d.') % line_number)
        country_origin.text = line_data['origin_country_code']

        # Destination Country
        destination_country = etree.SubElement(item, 'MSConsDestCode')
        destination_country.text = line_data['country_code']

        # Nationality of Transport Vehicle
        nationality_of_transport_vehicle = etree.SubElement(item, 'nationalityOfTransportVehicle')
        nationality_of_transport_vehicle.text = line_data['origin_transport_code'] or ''

        # Net Mass
        weight = etree.SubElement(item, 'netMass')
        if not line_data['weight']:
            raise UserError(_('Missing weight on line %d.') % line_number)
        weight.text = str(int(round(float(line_data['weight']))))

        # Invoiced Amount
        invoiced_amount = etree.SubElement(item, 'invoicedAmount')
        if not line_data['value']:
            raise UserError(_('Missing fiscal value on line %d.') % line_number)
        invoiced_amount.text = str(int(round(float(line_data['value']))))

        # Statistical Value
        statistical_value = etree.SubElement(item, 'statisticalValue')
        statistical_value.text = str(int(round(float(line_data['statistical_value'] or line_data['value']))))

        # Supplementary Unit
        quantity_in_su = etree.SubElement(item, 'supplementaryUnit')
        suppl_units = line_data['supplementary_units']
        quantity_in_su.text = str(int(float(suppl_units))) if suppl_units else '0'

        # Nature of Transaction
        transaction_nature = etree.SubElement(item, 'NatureOfTransaction')
        transaction_code = line_data['transaction_code']
        if not transaction_code:
            raise UserError(_('Transaction code is missing on line %d.') % line_number)

        transaction_nature_a = etree.SubElement(transaction_nature, 'natureOfTransactionACode')
        transaction_nature_a.text = transaction_code[0] if transaction_code else ''

        if len(transaction_code) >= 2:
            transaction_nature_b = etree.SubElement(transaction_nature, 'natureOfTransactionBCode')
            transaction_nature_b.text = transaction_code[1]

        # Mode of Transport Code
        mode_of_transport_code = etree.SubElement(item, 'modeOfTransportCode')
        if not line_data['transport_code']:
            raise UserError(_('Mode of transport is not set on line %d.') % line_number)
        mode_of_transport_code.text = str(line_data['transport_code'])

        # Region Code
        region_code = etree.SubElement(item, 'regionCode')
        if not line_data['region_code']:
            raise UserError(_('Department is not set on line %d.') % line_number)
        region_code.text = line_data['region_code']

        # Delivery Terms
        delivery_terms = etree.SubElement(item, 'DeliveryTerms')
        delivery_terms_code = etree.SubElement(delivery_terms, 'TODCode')
        if not line_data['incoterm_code']:
            raise UserError(_('Incoterm is not set on line %d.') % line_number)
        delivery_terms_code.text = line_data['incoterm_code']
