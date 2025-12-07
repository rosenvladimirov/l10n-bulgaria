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

    eik = fields.Char(
        string='EIK',
        help='Company EIK number (9 or 13 digits)',
        required=True
    )

    # Display fields for company data from registry
    display_eik = fields.Char(
        string='EIK',
        readonly=True
    )
    display_name_bg = fields.Char(
        string='Company Name (BG)',
        readonly=True
    )
    display_name_en = fields.Char(
        string='Company Name (EN)',
        readonly=True
    )
    display_legal_form_bg = fields.Char(
        string='Legal Form (BG)',
        readonly=True
    )
    display_vat = fields.Char(
        string='VAT Number',
        readonly=True
    )
    display_address_bg = fields.Text(
        string='Address (BG)',
        readonly=True
    )
    display_city = fields.Char(
        string='City',
        readonly=True
    )
    display_postal_code = fields.Char(
        string='Postal Code',
        readonly=True
    )
    display_street = fields.Char(
        string='Street',
        readonly=True
    )
    display_activity_code = fields.Char(
        string='Activity Code',
        readonly=True
    )
    display_activity_description = fields.Text(
        string='Activity Description',
        readonly=True
    )
    display_registration_date = fields.Date(
        string='Registration Date',
        readonly=True
    )

    # Store fetched company data as JSON
    company_data_json = fields.Text(
        string='Company Data',
        readonly=True,
        help='Raw company data from registry'
    )

    data_fetched = fields.Boolean(
        string='Data Fetched',
        default=False,
        help='Indicates if data was successfully fetched'
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
            legal_form_bg = self._get_legal_form_name(data.get('legalForm'))
            company_name_bg = data.get('companyName', '')

            company_data = {
                'eik': data.get('uic', ''),
                'company_name_bg': company_name_bg,
                'company_name_en': self._generate_english_name(company_name_bg, legal_form_bg),
                'legal_form_bg': legal_form_bg,
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
                        fields_list = group.get('fields', [])
                        for field in fields_list:
                            field_code = field.get('nameCode', '')

                            # Extract address (CR_F_5_L)
                            if field_code == 'CR_F_5_L':
                                html_data = field.get('htmlData', '')
                                address_text = self._extract_text_from_html(html_data)
                                company_data['address_full_bg'] = address_text

                                # Parse structured address
                                parsed_address = self._parse_bulgarian_address(address_text)
                                company_data.update(parsed_address)

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

    @staticmethod
    def _get_legal_form_name(legal_form_code):
        """Get legal form name from code"""
        legal_forms = {
            10: 'ЕООД',
            1: 'ООД',
            2: 'АД',
            3: 'ЕАД',
            4: 'КД',
            5: 'КДА',
            6: 'СД',
            7: 'ЕТ',
        }
        return legal_forms.get(legal_form_code, '')

    @staticmethod
    def _generate_english_name(company_name_bg, legal_form_bg):
        """
        Generate English version by appending transliterated name and legal form

        Args:
            company_name_bg (str): Bulgarian company name
            legal_form_bg (str): Bulgarian legal form

        Returns:
            str: English name with transliterated legal form
        """
        if not company_name_bg:
            return ''

        # Transliteration map for legal form
        legal_form_en_map = {
            'ЕООД': {
                'short': 'Ltd.',
                'long': 'Single-Member Limited Liability Company'
            },
            'ООД': {
                'short': 'Ltd.',
                'long': 'Limited Liability Company'
            },
            'АД': {
                'short': 'JSC',
                'long': 'Joint-Stock Company'
            },
            'ЕАД': {
                'short': 'JSC',
                'long': 'Single-Member Joint-Stock Company'
            },
            'КД': {
                'short': 'LP',
                'long': 'Limited Partnership'
            },
            'КДА': {
                'short': 'PLS',
                'long': 'Partnership Limited by Shares'
            },
            'СД': {
                'short': 'GP',
                'long': 'General Partnership'
            },
            'ЕТ': {
                'short': '—',
                'long': 'Sole Proprietor'
            },
        }

        # Get English legal form
        legal_form_en = legal_form_en_map.get(legal_form_bg, {'short': legal_form_bg})

        # Append to company name
        if legal_form_en:
            return f"{company_name_bg} {legal_form_en.get('short', legal_form_en)}"

        return company_name_bg

    @staticmethod
    def _extract_text_from_html(html_data):
        """Extract clean text from HTML"""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html_data)
        # Clean up whitespace
        text = ' '.join(text.split())
        return text.strip()

    def _parse_bulgarian_address(self, address_text):
        """
        Parse Bulgarian address and map to city_id

        Args:
            address_text (str): Full address text from registry

        Returns:
            dict: Parsed address components with city_id
        """
        if not address_text:
            return {}

        result = {
            'country_code': 'BG',
            'state_id': False,
            'city_id': False,
            'zip': '',
            'street': '',
            'street_name': '',
            'street_number': '',
            'street_number2': '',
            'street_building_number': '',
            'street_floor_number': '',
        }

        # Extract country
        country_match = re.search(r'Държава:\s*([А-Я]+)', address_text)
        if country_match and country_match.group(1) != 'БЪЛГАРИЯ':
            result['country_code'] = country_match.group(1)

        # Extract state/region (Област)
        state_match = re.search(r'Област:\s*([^,]+)', address_text)
        if state_match:
            state_name = state_match.group(1).strip()
            state = self.env['res.country.state'].search([
                ('country_id.code', '=', 'BG'),
                ('name', 'ilike', state_name)
            ], limit=1)
            if state:
                result['state_id'] = state.id

        # Extract city and postal code
        city_match = re.search(r'Населено място:\s*(?:гр\.|с\.)\s*([^,]+)(?:,\s*п\.к\.\s*(\d+))?', address_text)
        if city_match:
            city_name = city_match.group(1).strip()
            postal_code = city_match.group(2).strip() if city_match.group(2) else ''
            result['zip'] = postal_code

            # Find city by postal code first, then by name
            city = False
            if postal_code:
                city = self.env['res.city'].search([
                    ('country_id.code', '=', 'BG'),
                    ('zipcode', '=', postal_code)
                ], limit=1)

            # If not found by postal code, search by name
            if not city and city_name:
                city = self.env['res.city'].search([
                    ('country_id.code', '=', 'BG'),
                    ('name', 'ilike', city_name)
                ], limit=1)

            if city:
                result['city_id'] = city.id

        # Extract street
        street_pattern = r'(?:бул\.|ул\.)\s*(?:ул\.\s*)?([^№]+)(?:№\s*(\d+[А-Яа-я]?))?(?:,\s*бл\.\s*(\d+[А-Яа-я]?))?(?:,\s*вх\.\s*([А-Яа-я\d]+))?(?:,\s*ет\.\s*(\d+))?(?:,\s*ап\.\s*(\d+))?'
        street_match = re.search(street_pattern, address_text)

        if street_match:
            street_name = street_match.group(1).strip()
            street_number = street_match.group(2) or ''
            building_number = street_match.group(3) or ''
            entrance = street_match.group(4) or ''
            floor_number = street_match.group(5) or ''
            apartment = street_match.group(6) or ''

            result['street_name'] = street_name
            result['street_number'] = street_number

            if apartment:
                result['street_number2'] = apartment

            if building_number:
                if entrance:
                    result['street_building_number'] = f"{building_number}, вх. {entrance}"
                else:
                    result['street_building_number'] = building_number

            if floor_number:
                result['street_floor_number'] = floor_number

            # Build full street
            street_parts = [street_name]
            if street_number:
                street_parts.append(f"№ {street_number}")
            if building_number:
                street_parts.append(f"бл. {building_number}")
            if entrance:
                street_parts.append(f"вх. {entrance}")
            if floor_number:
                street_parts.append(f"ет. {floor_number}")
            if apartment:
                street_parts.append(f"ап. {apartment}")

            result['street'] = ', '.join(street_parts)

        return result

    @staticmethod
    def _extract_nkid_code(html_data):
        """Extract NKID code from HTML"""
        text = re.sub(r'<[^>]+>', '', html_data)
        text = ' '.join(text.split()).strip()
        match = re.search(r'Група по НКИД:\s*(\d+)', text)
        if match:
            return match.group(1).strip()
        return ''

    def action_fetch_data(self):
        """Fetch company data from registry"""
        self.ensure_one()

        if not self.eik:
            raise ValidationError(_('Моля въведете ЕИК номер'))

        # Extract EIK from VAT if needed
        eik = self._extract_eik_from_vat(self.eik)

        if not eik:
            raise ValidationError(_('Невалиден ЕИК формат. Моля въведете 9 или 13 цифри.'))

        # Fetch from registry API
        company_data = self._fetch_from_registry_api(eik)

        if not company_data:
            raise UserError(_(
                'Не е намерена компания с ЕИК: %s\n\n'
                'Компанията не е намерена в официалния търговски регистър.\n\n'
                'Моля проверете дали ЕИК номерът е правилен.'
            ) % eik)

        # Store data in JSON format
        import json
        self.company_data_json = json.dumps(company_data, ensure_ascii=False)
        self.data_fetched = True

        # Populate display fields
        self.display_eik = company_data.get('eik', '')
        self.display_name_bg = company_data.get('company_name_bg', '')
        self.display_name_en = company_data.get('company_name_en', '')
        self.display_legal_form_bg = company_data.get('legal_form_bg', '')
        self.display_vat = company_data.get('vat_number', '')
        self.display_address_bg = company_data.get('address_full_bg', '')
        self.display_city = company_data.get('city_id', False) and self.env['res.city'].browse(company_data['city_id']).name or ''
        self.display_postal_code = company_data.get('zip', '')
        self.display_street = company_data.get('street', '')
        self.display_activity_code = company_data.get('activity_code', '')
        self.display_activity_description = company_data.get('activity_description_bg', '')
        self.display_registration_date = company_data.get('registration_date', False)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'bg.company.search.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    def action_populate_partner(self):
        """Populate partner with fetched company data"""
        self.ensure_one()

        if not self.data_fetched:
            raise UserError(_('Моля първо изтеглете данните от регистъра'))

        if not self.partner_id:
            raise UserError(_('Няма зададен партньор'))

        # Get company data from JSON
        import json
        company_data = json.loads(self.company_data_json)

        # Prepare partner values
        vals = self._prepare_partner_vals_from_company_data(company_data)

        # Update partner
        self.partner_id.write(vals)

        return {'type': 'ir.actions.act_window_close'}

    @api.model
    def _prepare_partner_vals_from_company_data(self, company_data):
        """
        Prepare partner values from company data

        Args:
            company_data (dict): Company data from registry

        Returns:
            dict: Partner values
        """
        vals = {}

        # Company name
        if company_data.get('company_name_bg'):
            vals['name'] = company_data['company_name_bg']

        # UIC/EIK
        if company_data.get('eik'):
            vals['l10n_bg_uic'] = company_data['eik']
            vals['l10n_bg_uic_type'] = 'bg_uic'

        # VAT
        if company_data.get('vat_number'):
            vals['vat'] = company_data['vat_number']

        # Legal form
        if company_data.get('legal_form_bg'):
            vals['l10n_bg_legal_form'] = company_data['legal_form_bg']

        # Address fields
        if company_data.get('city_id'):
            vals['city_id'] = company_data['city_id']

        if company_data.get('state_id'):
            vals['state_id'] = company_data['state_id']

        if company_data.get('zip'):
            vals['zip'] = company_data['zip']

        if company_data.get('street_name'):
            vals['street_name'] = company_data['street_name']

        if company_data.get('street_number'):
            vals['street_number'] = company_data['street_number']

        if company_data.get('street_number2'):
            vals['street_number2'] = company_data['street_number2']

        if company_data.get('street_building_number'):
            vals['street_building_number'] = company_data['street_building_number']

        if company_data.get('street_floor_number'):
            vals['street_floor_number'] = company_data['street_floor_number']

        if company_data.get('street'):
            vals['street'] = company_data['street']

        # Country (Bulgaria)
        country_bg = self.env['res.country'].search([('code', '=', 'BG')], limit=1)
        if country_bg:
            vals['country_id'] = country_bg.id

        # Registration date
        if company_data.get('registration_date'):
            vals['l10n_bg_registration_date'] = company_data['registration_date']

        # Activity
        if company_data.get('activity_code'):
            vals['l10n_bg_activity_code'] = company_data['activity_code']

        if company_data.get('activity_description_bg'):
            vals['l10n_bg_activity_description'] = company_data['activity_description_bg']

        # Set as company
        vals['is_company'] = True
        vals['company_type'] = 'company'

        return vals
