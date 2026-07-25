# Copyright 2009-2019 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from datetime import datetime

# from odoo.addons.report_xlsx_helper.report.report_xlsx_abstract \
#     import ReportXlsxAbstract
from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


# _render = ReportXlsxAbstract._render


class IntrastatProductDeclaration(models.Model):
    _name = "intrastat.product.declaration"
    _description = "Intrastat Product Declaration for Bulgaria"
    _inherit = [
        "intrastat.product.declaration",
        "report.intrastat_product.product_declaration_xls",
        "mail.thread",
    ]

    def _get_origin_transport(self, inv_line, notedict):
        invoice = inv_line.move_id
        origin_transport = (
            invoice.origin_transport_id or self.company_id.intrastat_origin_transport_id
        )
        if not origin_transport:
            msg = _(
                "The default Intrastat Transport Origin "
                "of the Company is not set, "
                "please configure it first."
            )
            self._account_config_warning(msg)
        return origin_transport

    def _get_region_code(self, inv_line, notedict):
        region = False
        invoice = inv_line.move_id
        delivery_partner_id = invoice.partner_shipping_id
        delivery_address_city = delivery_partner_id.city_id
        if delivery_address_city:
            region = delivery_address_city.region_id
        if not region and delivery_address_city.l10n_bg_municipality_id:
            region = delivery_address_city.l10n_bg_municipality_id.region_id
        if region:
            return region.code
        return super()._get_region_code(inv_line, notedict)

    def _update_computation_line_vals(self, inv_line, line_vals, notedict):
        invoice = inv_line.move_id
        line_vals.update(
            {
                "origin_transport_id": self._get_origin_transport(
                    inv_line, notedict
                ).id,
                "incoterm_id": self._get_incoterm(inv_line, notedict).id,
            }
        )

    def _handle_invoice_accessory_cost(
        self,
        invoice,
        lines_current_invoice,
        total_inv_accessory_costs_cc,
        total_inv_product_cc,
        total_inv_weight,
    ):
        """
        In Bulgaria accessory cost should not be added.
        If transport costs and insurance costs are included in the price
        of the goods, you do not have to make any additional calculation
        or estimate in order to deduct them. If they are separately known
        (e.g. stated on a separate line on the invoice),
        transport and insurance costs may not be included in the value of
        the goods
        """
        pass

    def _gather_invoices_init(self, notedict):
        if self.company_id.country_id.code not in ("bg", "BG"):
            raise UserError(
                _(
                    "The Bulgaria Intrastat Declaration requires "
                    "the Company's Country to be equal to 'Bulgaria'."
                )
            )
        # self.reporting_level = self.company_id.l10n_bg_intrastat_reporting_level

    # def _xls_computation_line_fields(self):
    #     res = super()._xls_computation_line_fields()
    #     i = res.index('product_origin_country')
    #     if self.type == 'dispatches':
    #         res.insert(i + 1, 'vat_number')
    #     # else:
    #     #     res.pop(i)
    #     res.append('incoterm_id')
    #     res.append('origin_transport_id')
    #     return res
    #
    # def _xls_declaration_line_fields(self):
    #     res = super()._xls_declaration_line_fields()
    #     if self.type == 'dispatches':
    #         i = res.index('hs_code')
    #         res.insert(i + 1, 'vat_number')
    #         res.insert(i + 1, 'product_origin_country')
    #     res.append('incoterm_id')
    #     res.append('origin_transport_id')
    #     if self.reporting_level == 'extended':
    #         i = res.index('amount_company_currency')
    #         res.insert(i + 1, 'amount_statistical_company_currency')
    #     return res

    # def _xls_template(self):
    #     res = super()._xls_template()
    #     res['vat_number'] = {
    #         'header': {
    #             'type': 'string',
    #             'value': _('VAT Number'),
    #         },
    #         'line': {
    #             'value': _render(
    #                 "line.vat_number or ''"),
    #         },
    #         'width': 18,
    #     }
    #     return res

    def _generate_xml(self):
        """Generate the INSTAT XML file export."""
        if self.company_id.country_id.code != "BG":
            return super()._generate_xml()

        """Generate the INSTAT XML file export."""
        self = self.with_context(dict(self._context, lang=self.env.user.lang))

        self._check_generate_xml()
        # my_company_vat = self.company_id.partner_id.vat.replace(' ', '')

        my_company_currency = self.company_id.currency_id.name

        root = etree.Element("INSTAT")
        envelope = etree.SubElement(root, "Envelope")

        create_date_time = etree.SubElement(envelope, "DateTime")
        create_date = etree.SubElement(create_date_time, "date")
        now_user_tz = fields.Datetime.context_timestamp(self, datetime.now())
        create_date.text = datetime.strftime(now_user_tz, "%Y-%m-%d")
        create_time = etree.SubElement(create_date_time, "time")
        create_time.text = datetime.strftime(now_user_tz, "%H:%M:%S")

        party_contact = self.company_id.l10n_bg_tax_contact_id.parent_id
        envelope_contact = self.company_id.l10n_bg_tax_contact_id

        party = etree.SubElement(envelope, "Party", partyType="PSI", partyRole="PSI")
        party_id = etree.SubElement(party, "partyId")
        party_id.text = party_contact.l10n_bg_uic or ""
        party_name = etree.SubElement(party, "partyIdType")
        party_name.text = party_contact.l10n_bg_uic_type or ""

        address = etree.SubElement(party, "Address")
        address_street_number = etree.SubElement(address, "streetNumber")
        address_street_number.text = party_contact.street_number or ""
        address_city = etree.SubElement(address, "city")
        address_city.text = party_contact.city or ""
        addres_zip = etree.SubElement(address, "postalCode")
        if not party_contact.zip:
            raise UserError(
                _("The zip is not set " "for the company '%s'.") % party_contact.name
            )
        addres_zip.text = party_contact.zip

        address_phone_number = etree.SubElement(address, "phoneNumber")
        address_phone_number.text = party_contact.phone and party_contact.phone or ""

        address_fax_number = etree.SubElement(address, "faxNumber")
        address_fax_number.text = party_contact.fax and party_contact.fax or ""

        envelope_id = etree.SubElement(party, "ContactPerson")
        if not envelope_contact:
            raise UserError(
                _("The tax contact person is not set " "for the company '%s'.")
                % self.company_id.name
            )
        envelope_name = etree.SubElement(envelope_id, "contactPersonName")
        envelope_name.text = envelope_contact.name
        envelope_address = etree.SubElement(envelope_id, "ContactPersonAddress")
        envelope_address_street_number = etree.SubElement(
            envelope_address, "streetNumber"
        )
        envelope_address_street_number.text = envelope_contact.street_number or ""
        envelope_address_city = etree.SubElement(envelope_address, "city")
        envelope_address_city.text = envelope_contact.city or ""
        envelope_address_zip = etree.SubElement(envelope_address, "postalCode")
        envelope_address_zip.text = envelope_contact.zip

        envelope_address_phone_number = etree.SubElement(
            envelope_address, "phoneNumber"
        )
        envelope_address_phone_number.text = (
            envelope_contact.phone and envelope_contact.phone or ""
        )

        envelope_address_mobile = etree.SubElement(
            envelope_address, "mobilePhoneNumber"
        )
        envelope_address_mobile.text = (
            envelope_contact.mobile and envelope_contact.mobile or ""
        )
        envelope_address_mail = etree.SubElement(envelope_address, "e-mail")
        envelope_address_mail.text = (
            envelope_contact.email and envelope_contact.email or ""
        )

        declaration = etree.SubElement(envelope, "Declaration")
        declaration_id = etree.SubElement(declaration, "declarationId")
        declaration_id.text = self.year_month.replace("-", "")
        reference_period = etree.SubElement(declaration, "referencePeriod")
        reference_period.text = self.year_month
        psi_id = etree.SubElement(declaration, "PSIId")
        psi_id.text = self.company_id.l10n_bg_uic or ""
        psi_id = etree.SubElement(declaration, "PSIIdType")
        psi_id.text = self.company_id.l10n_bg_uic_type or ""

        function = etree.SubElement(declaration, "Function")
        function.text = "REGULAR"  # Check it (REGULAR, CORRECTIVE, LEDGER)

        flow_code = etree.SubElement(declaration, "flowCode")
        assert self.declaration_type in (
            "arrivals",
            "dispatches",
        ), "The DEB must be of type 'Arrivals' or 'Dispatches'"
        if self.declaration_type == "dispatches":
            flow_code.text = "D"
        elif self.declaration_type == "arrivals":
            flow_code.text = "A"

        total_net_mass = etree.SubElement(declaration, "totalNetMass")
        total_net_mass.text = str(sum([x.weight for x in self.declaration_line_ids]))
        total_invoiced_amount = etree.SubElement(declaration, "totalInvoicedAmount")
        total_invoiced_amount.text = str(
            sum([x.amount_company_currency for x in self.declaration_line_ids])
        )
        total_statistical_value = etree.SubElement(declaration, "totalStatisticalValue")
        total_statistical_value.text = str(
            int(
                sum(
                    [
                        round(x.amount_company_currency, 0)
                        for x in self.declaration_line_ids
                    ]
                )
            )
        )
        total_number_detailed_lines = etree.SubElement(
            declaration, "totalNumberDetailedLines"
        )
        total_number_detailed_lines.text = str(len(self.declaration_line_ids.ids))

        # THEN, the fields which vary from a line to the next
        if not self.declaration_line_ids:
            raise UserError(
                _("No declaration lines. You probably forgot to generate " "them !")
            )
        line = 0
        for pline in self.declaration_line_ids:
            line += 1  # increment line number
            # print "line =", line
            assert pline.transaction_id, "Missing Intrastat Type"
            transaction = pline.transaction_id
            item = etree.SubElement(declaration, "Item")
            item_number = etree.SubElement(item, "itemNumber")
            item_number.text = str(line)
            # START of elements which are only required in "detailed" level

            cn8 = etree.SubElement(item, "CN8")
            cn8_code = etree.SubElement(cn8, "CN8Code")
            if not pline.hs_code_id:
                raise UserError(_("Missing H.S. code on line %d.") % line)
            # local_code is required=True, so no need to check it
            cn8_code.text = pline.hs_code_id.local_code
            vinNumber = etree.SubElement(item, "vinNumber")
            if self.declaration_type == "dispatches":
                if not pline.vat:
                    raise UserError(
                        _("Missing partner VAT number on line #: %d.") % line
                    )
                vinNumber.text = pline.vat
            else:
                vinNumber.text = ""
            # if self.type == 'arrivals':
            country_origin = etree.SubElement(item, "countryOfOriginCode")
            if not pline.product_origin_country_code:
                raise UserError(
                    _("Missing product country of origin on line #: %d.") % line
                )
            country_origin.text = pline.product_origin_country_code

            destination_country = etree.SubElement(item, "MSConsDestCode")
            destination_country.text = pline.src_dest_country_code

            nationality_of_transport_vehicle = etree.SubElement(
                item, "nationalityOfTransportVehicle"
            )
            nationality_of_transport_vehicle.text = pline.origin_transport_id.code
            nationality_of_transport_vehicle.text = ""

            weight = etree.SubElement(item, "netMass")
            if not pline.weight:
                raise UserError(_("Missing weight on line #: %d.") % line)
            weight.text = f"{pline.weight:.3f}"

            invoiced_amount = etree.SubElement(item, "invoicedAmount")
            if not pline.amount_company_currency:
                raise UserError(_("Missing fiscal value on line %d.") % line)
            invoiced_amount.text = str(pline.amount_company_currency)

            statistical_value = etree.SubElement(item, "statisticalValue")
            if not pline.amount_company_currency and self.reporting_level == "extended":
                raise UserError(_("Missing statistical value on line %d.") % line)
            statistical_value.text = str(int(pline.amount_company_currency))

            quantity_in_SU = etree.SubElement(item, "supplementaryUnit")
            if not pline.suppl_unit_qty:
                quantity_in_SU.text = f"{0.0:.3f}"
            else:
                quantity_in_SU.text = f"{pline.suppl_unit_qty:.3f}"

            transaction_nature = etree.SubElement(item, "NatureOfTransaction")
            transaction_nature_a = etree.SubElement(
                transaction_nature, "natureOfTransactionACode"
            )
            transaction_nature_a.text = transaction.code[0]
            if len(transaction.code) >= 2:
                transaction_nature_b = etree.SubElement(
                    transaction_nature, "natureOfTransactionBCode"
                )
                transaction_nature_b.text = transaction.code[1]

            mode_of_transport_code = etree.SubElement(item, "modeOfTransportCode")
            if not pline.transport_id:
                raise UserError(_("Mode of transport is not set on line %d.") % line)
            mode_of_transport_code.text = str(pline.transport_id.code)
            region_code = etree.SubElement(item, "regionCode")
            if not pline.region_code:
                raise UserError(_("Department is not set on line %d.") % line)
            region_code.text = pline.region_code

            delivery_terms = etree.SubElement(item, "DeliveryTerms")
            delivery_terms_code = etree.SubElement(delivery_terms, "TODCode")
            if not pline.incoterm_id:
                raise UserError(_("Incoterm is not set on line %d.") % line)
            delivery_terms_code.text = pline.incoterm_id.code
            # action = etree.SubElement(item, 'action') for develop

        number_of_declarations = etree.SubElement(envelope, "numberOfDeclarations")
        number_of_declarations.text = str(1)  # for develop

        xml_string = etree.tostring(
            root, pretty_print=True, encoding="UTF-8", xml_declaration=True
        )
        # We validate the XML file against the official XML Schema Definition
        # Because we may catch some problems with the content
        # of the XML file this way

        # self._check_xml_schema(
        #     xml_string, 'l10n_bg_intrastat_product/data/deb.xsd')

        # Attach the XML file to the current object
        return xml_string


class IntrastatProductComputationLine(models.Model):
    _inherit = "intrastat.product.computation.line"

    origin_transport_id = fields.Many2one(
        "res.country",
        string="Transport Country of origin",
        help="Transport Country of Origin",
    )
    origin_transport_code = fields.Char(
        compute="_compute_origin_transport_code",
        string="Transport Country Code",
        required=True,
        readonly=False,
        help="2 letters code of the country of origin transport.\n"
        "Specify 'XI' for Northern Ireland.",
    )
    incoterm_code = fields.Char(
        compute="_compute_incoterm_code",
        string="Incoterm Code",
        required=True,
        readonly=False,
        help="2 letters code of the country of origin transport.\n"
        "Specify 'XI' for Northern Ireland.",
    )

    @api.depends("origin_transport_id")
    def _compute_origin_transport_code(self):
        for this in self:
            code = this.origin_transport_id and this.origin_transport_id.code or False
            this.origin_transport_code = code

    @api.depends("incoterm_id")
    def _compute_incoterm_code(self):
        for this in self:
            code = this.incoterm_id and this.incoterm_id.code or False
            this.incoterm_code = code

    def _group_line_hashcode_fields(self):
        self.ensure_one()
        res = super()._group_line_hashcode_fields()
        res.update(
            {
                "incoterm": self.incoterm_id.id or False,
                "origin_transport": self.origin_transport_code or False,
            }
        )
        return res

    def _prepare_grouped_fields(self, fields_to_sum):
        self.ensure_one()
        vals = super()._prepare_grouped_fields(fields_to_sum)
        vals.update(
            {
                "incoterm_id": self.incoterm_id.id,
                "origin_transport_id": self.origin_transport_id.id,
            }
        )
        return vals


class IntrastatProductDeclarationLine(models.Model):
    _inherit = "intrastat.product.declaration.line"

    origin_transport_id = fields.Many2one(
        "res.country",
        string="Transport Country of origin",
        help="Transport Country of Origin",
    )
