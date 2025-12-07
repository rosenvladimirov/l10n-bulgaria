# -*- coding: utf-8 -*-

import logging
import requests
import re
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BgCompanySearchWizard(models.TransientModel):
    """Wizard for searching Bulgarian companies in the registry"""
    _name = 'bg.company.search.wizard'
    _description = 'Bulgarian Company Search Wizard'

    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        help='Partner to populate with company data'
    )

    search_type = fields.Selection([
        ('eik', 'Search by EIK'),
        ('name', 'Search by Company Name')
    ], string='Search Type', default='eik', required=True)

    search_eik = fields.Char(
        string='EIK',
        help='Enter company EIK number (9 or 13 digits)'
    )

    search_name = fields.Char(
        string='Company Name',
        help='Enter company name (at least 3 characters)'
    )

    search_language = fields.Selection([
        ('bg', 'Bulgarian'),
        ('en', 'English'),
        ('both', 'Both')
    ], string='Search Language', default='both')

    # Search results
    company_ids = fields.Many2many(
        'bg.company.registry',
        string='Search Results',
        help='Companies found in registry'
    )

    selected_company_id = fields.Many2one(
        'bg.company.registry',
        string='Selected Company',
        help='Select a company to populate partner data'
    )

    # Display fields for a selected company
    display_eik = fields.Char(
        related='selected_company_id.eik',
        string='EIK',
        readonly=True
    )
    display_name_bg = fields.Char(
        related='selected_company_id.company_name_bg',
        string='Company Name (BG)',
        readonly=True
    )
    display_name_en = fields.Char(
        related='selected_company_id.company_name_en',
        string='Company Name (EN)',
        readonly=True
    )
    display_address_bg = fields.Text(
        related='selected_company_id.address_full_bg',
        string='Address (BG)',
        readonly=True
    )
    display_vat = fields.Char(
        related='selected_company_id.vat_number',
        string='VAT Number',
        readonly=True
    )
    display_legal_form = fields.Char(
        related='selected_company_id.legal_form_bg',
        string='Legal Form',
        readonly=True
    )

    @staticmethod
    def _extract_eik_from_vat(vat_number):
        """
        Extract EIK from VAT number (removes BG prefix)

        Args:
            vat_number (str): VAT number (can be with or without a BG prefix)

        Returns:
            str: Clean EIK number or False
        """
        if not vat_number:
            return False

        # Remove spaces and convert to uppercase
        vat_clean = vat_number.strip().upper()

        # Remove BG prefix if present
        if vat_clean.startswith('BG'):
            vat_clean = vat_clean[2:]

        # Check if it's a valid EIK (9 or 13 digits)
        if re.match(r'^\d{9}$|^\d{13}$', vat_clean):
            return vat_clean

        return False

        def _fetch_from_registry_api(self, eik):
            """
            Fetch company data from portal.registryagency.bg API

            This is the actual Bulgarian Trade Registry API endpoint

            Args:
                eik (str): Company EIK number

            Returns:
                dict: Company data or False
            """
            if not eik:
                return False

            try:
                _logger.info(f"Fetching company data from portal.registryagency.bg API for EIK: {eik}")

                # Real API endpoint from portal.registryagency.bg
                api_url = f"https://portal.registryagency.bg/CR/api/Deeds/{eik}"

                # Current date for query parameter
                from datetime import datetime
                current_date = datetime.now().strftime('%Y-%m-%dT23:59:59.999Z')

                response = requests.get(
                    api_url,
                    params={
                        'entryDate': current_date,
                        'loadFieldsFromAllLegalForms': 'false'
                    },
                    headers={
                        'User-Agent': 'Mozilla/5.0 (compatible; Odoo/18.0)',
                        'Accept': '*/*',
                        'Content-Type': 'application/json; charset=utf-8'
                    },
                    timeout=30
                )

                if response.status_code == 200:
                    _logger.info(f"Successfully fetched company data for EIK: {eik}")
                    data = response.json()

                    # Parse the response
                    return self._parse_registry_api_response(data)
                elif response.status_code == 404:
                    _logger.warning(f"Company not found in registry for EIK: {eik}")
                    return False
                else:
                    _logger.error(f"Registry API returned status {response.status_code} for EIK: {eik}")
                    return False

            except requests.Timeout:
                _logger.error("Timeout while fetching data from registry API")
                return False
            except requests.RequestException as e:
                _logger.error(f"Error fetching data from registry API: {str(e)}")
                return False
            except Exception as e:
                _logger.error(f"Unexpected error in registry API fetch: {str(e)}")
                return False

        def _parse_registry_api_response(self, data):
            """
            Parse response from portal.registryagency.bg API

            Args:
                data (dict): JSON response from API

            Returns:
                dict: Standardized company data
            """
            try:
                company_data = {
                    'eik': data.get('uic', ''),
                    'company_name_bg': data.get('companyName', ''),
                    'legal_form_bg': self._get_legal_form_name(data.get('legalForm')),
                    'vat_number': f"BG{data.get('uic', '')}" if data.get('uic') else '',
                    'status': 'active',
                }

                # Parse sections to extract address and other data
                sections = data.get('sections', [])
                for section in sections:
                    sub_deeds = section.get('subDeeds', [])
                    for sub_deed in sub_deeds:
                        groups = sub_deed.get('groups', [])
                        for group in groups:
                            fields = group.get('fields', [])
                            for field in fields:
                                field_code = field.get('nameCode', '')

                                # Extract address (CR_F_5_L)
                                if field_code == 'CR_F_5_L':
                                    html_data = field.get('htmlData', '')
                                    company_data['address_full_bg'] = self._extract_text_from_html(html_data)
                                    company_data['city_bg'] = self._extract_city_from_address(html_data)
                                    company_data['postal_code'] = self._extract_postal_code(html_data)
                                    company_data['street_bg'] = self._extract_street(html_data)

                                # Extract activity (CR_F_6_L)
                                elif field_code == 'CR_F_6_L':
                                    html_data = field.get('htmlData', '')
                                    company_data['activity_description_bg'] = self._extract_text_from_html(html_data)

                                # Extract NKID code (CR_F_6a_L)
                                elif field_code == 'CR_F_6a_L':
                                    html_data = field.get('htmlData', '')
                                    company_data['activity_code'] = self._extract_nkid_code(html_data)

                                # Extract registration date from field action date
                                if field_code == 'CR_F_1_L':
                                    action_date = field.get('fieldActionDate', '')
                                    if action_date:
                                        company_data['registration_date'] = action_date.split('T')[0]

                _logger.info(f"Parsed company data: {company_data.get('company_name_bg')}")
                return company_data

            except Exception as e:
                _logger.error(f"Error parsing registry API response: {str(e)}")
                return False

        def _get_legal_form_name(self, legal_form_code):
            """Get legal form name from code"""
            legal_forms = {
                10: 'ЕООД',  # Еднолично дружество с ограничена отговорност
                1: 'ООД',  # Дружество с ограничена отговорност
                2: 'АД',  # Акционерно дружество
                3: 'ЕАД',  # Еднолично акционерно дружество
                4: 'КД',  # Командитно дружество
                5: 'КДА',  # Командитно дружество с акции
                6: 'СД',  # Събирателно дружество
                7: 'ЕТ',  # Едноличен търговец
            }
            return legal_forms.get(legal_form_code, '')

        def _extract_text_from_html(self, html_data):
            """Extract clean text from HTML"""
            import re
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', '', html_data)
            # Clean up whitespace
            text = ' '.join(text.split())
            return text.strip()

        def _extract_city_from_address(self, html_data):
            """Extract city from address HTML"""
            import re
            text = self._extract_text_from_html(html_data)
            # Look for city pattern: "Населено място: гр. XXXX"
            match = re.search(r'Населено място:\s*(?:гр\.|с\.)\s*([^,]+)', text)
            if match:
                return match.group(1).strip()
            return ''

        def _extract_postal_code(self, html_data):
            """Extract postal code from address HTML"""
            import re
            text = self._extract_text_from_html(html_data)
            # Look for postal code pattern: "п.к. XXXX"
            match = re.search(r'п\.к\.\s*(\d+)', text)
            if match:
                return match.group(1).strip()
            return ''

        def _extract_street(self, html_data):
            """Extract street from address HTML"""
            import re
            text = self._extract_text_from_html(html_data)
            # Look for street pattern: "бул./ул. XXXX"
            match = re.search(r'(?:бул\.|ул\.)\s*([^№]+)(?:№\s*(\d+))?', text)
            if match:
                street = match.group(1).strip()
                number = match.group(2)
                if number:
                    return f"{street} {number}"
                return street
            return ''

        def _extract_nkid_code(self, html_data):
            """Extract NKID code from HTML"""
            import re
            text = self._extract_text_from_html(html_data)
            # Look for NKID group code
            match = re.search(r'Група по НКИД:\s*(\d+)', text)
            if match:
                return match.group(1).strip()
            return ''

    def _search_in_resource(self, resource_url, resource_format, eik):
        """
        Search for company in a resource file

        Args:
            resource_url (str): URL to resource file
            resource_format (str): Format of the resource (CSV, XLSX, etc.)
            eik (str): Company EIK to search for

        Returns:
            dict: Company data or False
        """
        try:
            _logger.info(f"Searching in resource: {resource_url}")

            if resource_format in ['CSV', 'TXT']:
                return self._search_in_csv_resource(resource_url, eik)
            elif resource_format in ['XLSX', 'XLS']:
                # For Excel files, you might need openpyxl or xlrd
                _logger.warning(f"Excel format not yet supported: {resource_format}")
                return False
            else:
                _logger.warning(f"Unsupported resource format: {resource_format}")
                return False

        except Exception as e:
            _logger.error(f"Error searching resource: {str(e)}")
            return False

    def _search_in_csv_resource(self, csv_url, eik):
        """
        Search for company in CSV resource

        Args:
            csv_url (str): URL to CSV file
            eik (str): Company EIK to search for

        Returns:
            dict: Company data or False
        """
        try:
            _logger.info(f"Downloading CSV from: {csv_url}")

            # Download CSV content with streaming to handle large files
            response = requests.get(csv_url, timeout=60, stream=True)

            if response.status_code != 200:
                _logger.warning(f"Failed to download CSV: {response.status_code}")
                return False

            # Try different encodings
            encodings = ['utf-8', 'windows-1251', 'iso-8859-1']

            for encoding in encodings:
                try:
                    # Read content
                    content = response.content.decode(encoding, errors='ignore')

                    # Parse CSV
                    import csv
                    from io import StringIO

                    csv_reader = csv.DictReader(StringIO(content))

                    # Search for EIK in CSV
                    row_count = 0
                    for row in csv_reader:
                        row_count += 1

                        # Try different possible column names for EIK
                        row_eik = (
                            row.get('EIK', '').strip() or
                            row.get('eik', '').strip() or
                            row.get('ЕИК', '').strip() or
                            row.get('BULSTAT', '').strip() or
                            row.get('bulstat', '').strip()
                        )

                        if row_eik == eik:
                            _logger.info(f"Found company in CSV at row {row_count}!")
                            return self._parse_csv_row_to_company_data(row)

                    _logger.info(f"Searched {row_count} rows, EIK {eik} not found")
                    return False

                except UnicodeDecodeError:
                    _logger.debug(f"Failed to decode with {encoding}, trying next encoding")
                    continue
                except Exception as e:
                    _logger.error(f"Error parsing CSV with {encoding}: {str(e)}")
                    continue

            _logger.warning("Failed to decode CSV with any supported encoding")
            return False

        except Exception as e:
            _logger.error(f"Error searching CSV resource: {str(e)}")
            return False

    @staticmethod
    def _parse_csv_row_to_company_data(row):
        """
        Parse CSV row to company data dictionary

        Args:
            row (dict): CSV row data

        Returns:
            dict: Standardized company data
        """
        # Map common CSV column names to our data structure
        company_data = {
            'eik': row.get('EIK', '').strip() or row.get('eik', '').strip(),
            'company_name_bg': row.get('Firma', '').strip() or row.get('company_name', '').strip(),
            'legal_form_bg': row.get('PravnaForma', '').strip() or row.get('legal_form', '').strip(),
            'address_full_bg': row.get('Sedal_Adres', '').strip() or row.get('address', '').strip(),
            'city_bg': row.get('Grad', '').strip() or row.get('city', '').strip(),
            'registration_date': row.get('DatRegistr', '').strip() or row.get('reg_date', '').strip(),
            'status': 'active',
        }

        # Generate VAT number
        if company_data.get('eik'):
            company_data['vat_number'] = f"BG{company_data['eik']}"

        return company_data

    def action_search(self):
        """Execute company search"""
        self.ensure_one()

        registry_model = self.env['bg.company.registry']

        if self.search_type == 'eik':
            if not self.search_eik:
                raise ValidationError(_('Please enter EIK number'))

            # Extract EIK from VAT if needed
            eik = self._extract_eik_from_vat(self.search_eik)

            if not eik:
                raise ValidationError(_('Invalid EIK format. Please enter 9 or 13 digits.'))

            # Try to fetch from the official registry API
            _logger.info(f"Attempting to fetch company data from official registry API for EIK: {eik}")
            company_data = self._fetch_from_registry_api(eik)

            if company_data:
                _logger.info(f"Company data found in official registry API for EIK: {eik}")

                # Store in local registry
                existing_company = registry_model.search([('eik', '=', eik)], limit=1)

                if existing_company:
                    # Update existing record
                    existing_company.write({
                        'company_name_bg': company_data.get('company_name_bg'),
                        'legal_form_bg': company_data.get('legal_form_bg'),
                        'address_full_bg': company_data.get('address_full_bg'),
                        'city_bg': company_data.get('city_bg'),
                        'postal_code': company_data.get('postal_code'),
                        'street_bg': company_data.get('street_bg'),
                        'vat_number': company_data.get('vat_number'),
                        'activity_code': company_data.get('activity_code'),
                        'activity_description_bg': company_data.get('activity_description_bg'),
                        'registration_date': company_data.get('registration_date'),
                        'data_last_updated': fields.Datetime.now(),
                    })
                    company = existing_company
                else:
                    # Create new record
                    company = registry_model.create({
                        'eik': company_data.get('eik'),
                        'company_name_bg': company_data.get('company_name_bg'),
                        'legal_form_bg': company_data.get('legal_form_bg'),
                        'address_full_bg': company_data.get('address_full_bg'),
                        'city_bg': company_data.get('city_bg'),
                        'postal_code': company_data.get('postal_code'),
                        'street_bg': company_data.get('street_bg'),
                        'vat_number': company_data.get('vat_number'),
                        'activity_code': company_data.get('activity_code'),
                        'activity_description_bg': company_data.get('activity_description_bg'),
                        'registration_date': company_data.get('registration_date'),
                        'data_last_updated': fields.Datetime.now(),
                    })

                self.company_ids = [(6, 0, [company.id])]
                self.selected_company_id = company.id

            else:
                # Fall back to local search
                _logger.info(f"Searching locally for EIK: {eik}")
                company_data = registry_model.search_company_by_eik(eik)

                if not company_data:
                    raise UserError(_(
                        'No company found with EIK: %s\n\n'
                        'The company was not found in the official registry or local database.\n\n'
                        'Please verify the EIK number is correct.'
                    ) % eik)

                company = registry_model.search([('eik', '=', eik)], limit=1)
                if company:
                    self.company_ids = [(6, 0, [company.id])]
                    self.selected_company_id = company.id

        else:  # search by name
            if not self.search_name or len(self.search_name) < 3:
                raise ValidationError(_('Company name must be at least 3 characters'))

            # Search by name (local only for now)
            companies_data = registry_model.search_company_by_name(
                self.search_name,
                limit=20
            )

            if not companies_data:
                raise UserError(_('No companies found matching: %s\n\n'
                                  'Make sure you have imported the Trade Register data.') % self.search_name)

            # Get company records
            eiks = [c.get('eik') for c in companies_data if c.get('eik')]
            companies = registry_model.search([('eik', 'in', eiks)])

            if companies:
                self.company_ids = [(6, 0, companies.ids)]
                if len(companies) == 1:
                    self.selected_company_id = companies[0].id

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'bg.company.search.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    def action_select_company(self):
        """Select a company from the search results"""
        self.ensure_one()

        # Get the company ID from the context (set by the tree view button)
        company_id = self.env.context.get('active_id')

        if company_id:
            self.selected_company_id = company_id

        # Return action to refresh the view
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'bg.company.search.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_populate_partner(self):
        """Populate partner with selected company data"""
        self.ensure_one()

        if not self.selected_company_id:
            raise UserError(_('Моля изберете компания'))

        if not self.partner_id:
            raise UserError(_('Няма зададен партньор'))

        # Get company data
        company_data = self.selected_company_id._prepare_company_data_dict()

        # Prepare partner values
        vals = self.partner_id._prepare_partner_vals_from_registry(company_data)

        # Update partner
        self.partner_id.write(vals)
        self.partner_id.l10n_bg_registry_id = self.selected_company_id.id
        self.partner_id.l10n_bg_registry_last_sync = fields.Datetime.now()

        return {'type': 'ir.actions.act_window_close'}

    def action_create_partner(self):
        """Create new partner from selected company"""
        self.ensure_one()

        if not self.selected_company_id:
            raise UserError(_('Моля изберете компания'))

        # Get company data
        company_data = self.selected_company_id._prepare_company_data_dict()

        # Prepare partner values
        partner_model = self.env['res.partner']
        vals = partner_model._prepare_partner_vals_from_registry(company_data)

        # Create partner
        partner = partner_model.create(vals)
        partner.l10n_bg_registry_id = self.selected_company_id.id
        partner.l10n_bg_registry_last_sync = fields.Datetime.now()

        # Open the created partner
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': partner.id,
            'view_mode': 'form',
            'target': 'current',
        }
