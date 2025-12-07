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

    original_eik = fields.Char(
        string='Original EIK',
        help='Original EIK from partner (to detect changes)'
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

    eik_changed = fields.Boolean(
        string='EIK Changed',
        compute='_compute_eik_changed',
        help='Indicates if EIK was changed by user'
    )

    @api.depends('eik', 'original_eik')
    def _compute_eik_changed(self):
        """Check if EIK was changed from original"""
        for wizard in self:
            wizard.eik_changed = (
                wizard.original_eik and
                wizard.eik and
                wizard.eik != wizard.original_eik
            )

    @api.model
    def default_get(self, fields_list):
        """Auto-fetch data when wizard opens if EIK is provided"""
        res = super().default_get(fields_list)

        # If EIK is provided in context, auto-fetch immediately
        if res.get('eik'):
            # Store original EIK
            res['original_eik'] = res['eik']

            # Try to fetch data automatically
            try:
                eik = self._extract_eik_from_vat(res['eik'])
                if eik:
                    company_data = self._fetch_from_registry_api_eik_only(eik)
                    if company_data:
                        # Populate display fields
                        res.update(self._populate_display_fields(company_data))
                        res['data_fetched'] = True

                        # Store JSON data
                        import json
                        res['company_data_json'] = json.dumps(company_data, ensure_ascii=False)
            except Exception as e:
                _logger.warning(f"Could not auto-fetch data in wizard: {str(e)}")

        return res

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

    @classmethod
    def _fetch_from_registry_api_eik_only(cls, eik):
        """
        Static method to fetch from registry (without self)
        Used in default_get
        """
        if not eik:
            return False

        try:
            _logger.info(f"Fetching company data from portal.registryagency.bg API for EIK: {eik}")

            api_url = f"https://portal.registryagency.bg/CR/api/Deeds/{eik}"

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
                return cls._parse_registry_response_static(data)
            else:
                _logger.warning(f"Registry API returned status {response.status_code} for EIK: {eik}")
                return False

        except Exception as e:
            _logger.error(f"Error fetching from registry: {str(e)}")
            return False

    @staticmethod
    def _parse_bulgarian_address_static(address_text):
        """
        Parse Bulgarian address and map to city_id
        Static version for use in default_get

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
            'city_name': '',
            'zip': '',
            'street': '',
            'street_name': '',
            'street_number': '',
            'street_number2': '',
            'street_building_number': '',
            'street_floor_number': '',
            'phone': '',
            'email': '',
        }

        # Extract state/region (Област)
        state_match = re.search(r'Област:\s*([^,]+)', address_text)
        if state_match:
            result['state_name'] = state_match.group(1).strip()

        # Extract city and postal code
        city_match = re.search(r'Населено място:\s*(?:гр\.|с\.)\s*([^,]+)(?:,\s*п\.к\.\s*(\d+))?', address_text)
        if city_match:
            city_name = city_match.group(1).strip()
            postal_code = city_match.group(2).strip() if city_match.group(2) else ''
            result['city_name'] = city_name
            result['zip'] = postal_code

        # Extract phone and email from lines with "Телефон:" or "Факс:"
        phone_email_match = re.search(r'(?:Телефон|Факс):\s*(.+?)(?:\n|$)', address_text)
        if phone_email_match:
            contact_info = phone_email_match.group(1).strip()
            # Check if it's an email (contains @)
            if '@' in contact_info:
                result['email'] = contact_info
            else:
                # It's a phone number
                result['phone'] = contact_info

        # Extract street from last line - format: "бул./ул. ул. БЕЛИ ЛОМ № 53, бл. 3, вх. Б, ет. 5, ап. 36"
        # Split by lines and get the last line that contains бул./ул.
        lines = address_text.split('\n')
        street_line = ''
        for line in reversed(lines):
            if 'бул./ул.' in line or 'бул.' in line or 'ул.' in line:
                street_line = line.strip()
                break

        if street_line:
            # Remove "бул./ул." prefix and any additional "ул." or "бул."
            street_line = re.sub(r'^бул\./ул\.\s*', '', street_line)
            street_line = re.sub(r'^(?:бул\.|ул\.)\s*', '', street_line)

            # Pattern to extract all address components
            # Format: ул. БЕЛИ ЛОМ № 53, бл. 3, вх. Б, ет. 5, ап. 36
            street_pattern = r'^([^№]+?)(?:\s*№\s*(\d+[А-Яа-я]?))?(?:,\s*бл\.\s*(\d+[А-Яа-я]?))?(?:,\s*вх\.\s*([А-Яа-я\d]+))?(?:,\s*ет\.\s*(\d+))?(?:,\s*ап\.\s*(\d+))?'
            street_match = re.search(street_pattern, street_line)

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
    def _parse_registry_response_static(data):
        """Static parser for registry response"""
        try:
            legal_forms = {
                10: 'ЕООД', 1: 'ООД', 2: 'АД', 3: 'ЕАД',
                4: 'КД', 5: 'КДА', 6: 'СД', 7: 'ЕТ',
            }

            legal_form_bg = legal_forms.get(data.get('legalForm'), '')
            company_name_bg = data.get('companyName', '')

            # Добавяме правната форма към българското име
            if legal_form_bg:
                company_name_bg_full = f"{company_name_bg} {legal_form_bg}"
            else:
                company_name_bg_full = company_name_bg

            # Генериране на английско име от секция 4
            company_name_en_raw = ''
            sections = data.get('sections', [])
            for section in sections:
                for sub_deed in section.get('subDeeds', []):
                    for group in sub_deed.get('groups', []):
                        for field in group.get('fields', []):
                            if field.get('nameCode') == 'CR_F_4_L':
                                # Извличаме текста от HTML
                                html_data = field.get('htmlData', '')
                                text = re.sub(r'<[^>]+>', '', html_data)
                                company_name_en_raw = ' '.join(text.split()).strip()
                                break
                        if company_name_en_raw:
                            break
                    if company_name_en_raw:
                        break
                if company_name_en_raw:
                    break

            # Формиране на пълното английско име с правна форма
            legal_form_en_map = {
                'ЕООД': 'Ltd.', 'ООД': 'Ltd.', 'АД': 'JSC', 'ЕАД': 'JSC',
                'КД': 'LP', 'КДА': 'PLS', 'СД': 'GP', 'ЕТ': 'ET',
            }
            legal_form_en = legal_form_en_map.get(legal_form_bg, '')

            if company_name_en_raw and legal_form_en:
                company_name_en = f"{company_name_en_raw} {legal_form_en}"
            elif company_name_en_raw:
                company_name_en = company_name_en_raw
            elif company_name_bg and legal_form_en:
                company_name_en = f"{company_name_bg} {legal_form_en}"
            else:
                company_name_en = company_name_bg

            company_data = {
                'eik': data.get('uic', ''),
                'company_name_bg': company_name_bg_full,
                'company_name_en': company_name_en,
                'legal_form_bg': legal_form_bg,
                'vat_number': f"BG{data.get('uic', '')}" if data.get('uic') else '',
                'status': 'active',
                'managers': [],  # Списък с управители
            }

            # Parse sections for address, activity and managers
            sections = data.get('sections', [])
            for section in sections:
                for sub_deed in section.get('subDeeds', []):
                    for group in sub_deed.get('groups', []):
                        for field in group.get('fields', []):
                            field_code = field.get('nameCode', '')
                            html_data = field.get('htmlData', '')

                            if field_code == 'CR_F_5_L':
                                # Extract address
                                text = re.sub(r'<[^>]+>', '', html_data)
                                text = ' '.join(text.split())
                                company_data['address_full_bg'] = text

                                # Parse structured address
                                parsed_address = BgCompanySearchWizard._parse_bulgarian_address_static(text)
                                company_data.update(parsed_address)

                            elif field_code == 'CR_F_6_L':
                                text = re.sub(r'<[^>]+>', '', html_data)
                                company_data['activity_description_bg'] = ' '.join(text.split()).strip()

                            elif field_code == 'CR_F_6a_L':
                                text = re.sub(r'<[^>]+>', '', html_data)
                                match = re.search(r'Група по НКИД:\s*(\d+)', text)
                                if match:
                                    company_data['activity_code'] = match.group(1).strip()

                            elif field_code == 'CR_F_7_L':
                                # Extract managers
                                text = re.sub(r'<[^>]+>', '', html_data)
                                text = ' '.join(text.split()).strip()

                                # Разделяме по запетая, ако има повече от един управител
                                manager_entries = text.split(',')
                                for manager_entry in manager_entries:
                                    manager_entry = manager_entry.strip()
                                    if manager_entry:
                                        # Формат: "ИМЕ ПРЕЗИМЕ ФАМИЛИЯ, Държава: БЪЛГАРИЯ"
                                        manager_data = {}

                                        # Извличаме държавата
                                        country_match = re.search(r'Държава:\s*([^\n,]+)', manager_entry)
                                        if country_match:
                                            manager_data['country'] = country_match.group(1).strip()
                                            # Премахваме частта с държавата от името
                                            name_part = manager_entry.split('Държава:')[0].strip()
                                        else:
                                            name_part = manager_entry.strip()

                                        if name_part:
                                            manager_data['name'] = name_part
                                            company_data['managers'].append(manager_data)

                            elif field_code == 'CR_F_1_L':
                                action_date = field.get('fieldActionDate', '')
                                if action_date:
                                    company_data['registration_date'] = action_date.split('T')[0]

            return company_data

        except Exception as e:
            _logger.error(f"Error parsing registry response: {str(e)}")
            return False

    @staticmethod
    def _populate_display_fields(company_data):
        """Populate display fields from company data"""
        return {
            'display_eik': company_data.get('eik', ''),
            'display_name_bg': company_data.get('company_name_bg', ''),
            'display_name_en': company_data.get('company_name_en', ''),
            'display_legal_form_bg': company_data.get('legal_form_bg', ''),
            'display_vat': company_data.get('vat_number', ''),
            'display_address_bg': company_data.get('address_full_bg', ''),
            'display_city': company_data.get('city_name', ''),
            'display_postal_code': company_data.get('zip', ''),
            'display_street': company_data.get('street', ''),
            'display_activity_code': company_data.get('activity_code', ''),
            'display_activity_description': company_data.get('activity_description_bg', ''),
            'display_registration_date': company_data.get('registration_date', False),
        }

    def _fetch_from_registry_api(self, eik):
        """Instance method wrapper"""
        return self._fetch_from_registry_api_eik_only(eik)

    def _parse_registry_api_response(self, data):
        """Instance method wrapper"""
        return self._parse_registry_response_static(data)

    @staticmethod
    def _get_legal_form_name(company_name_bg, legal_form_code):
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
        Generate an English version by appending transliterated name and legal form

        Args:
            company_name_bg (str): Bulgarian company name
            legal_form_bg (str): Bulgarian legal form

        Returns:
            str: English name with transliterated legal form
        """
        if not company_name_bg:
            return ''

        legal_form_en_map = {
            'ЕООД': 'Ltd.',
            'ООД': 'Ltd.',
            'АД': 'JSC',
            'ЕАД': 'JSC',
            'КД': 'LP',
            'КДА': 'PLS',
            'СД': 'GP',
            'ЕТ': '—',
        }

        legal_form_en = legal_form_en_map.get(legal_form_bg, legal_form_bg)

        if legal_form_en:
            return f"{company_name_bg} {legal_form_en}"

        return company_name_bg

    @staticmethod
    def _extract_text_from_html(html_data):
        """Extract clean text from HTML"""
        text = re.sub(r'<[^>]+>', '', html_data)
        text = ' '.join(text.split())
        return text.strip()

    def _parse_bulgarian_address(self, address_text):
        """
        Instance method wrapper for address parsing
        Also resolves city_id and state_id from database
        """
        result = self._parse_bulgarian_address_static(address_text)

        # Resolve state_id
        if result.get('state_name'):
            state = self.env['res.country.state'].search([
                ('country_id.code', '=', 'BG'),
                ('name', 'ilike', result['state_name'])
            ], limit=1)
            if state:
                result['state_id'] = state.id

        # Resolve city_id
        if result.get('city_name'):
            city = False
            # Try by postal code first
            if result.get('zip'):
                city = self.env['res.city'].search([
                    ('country_id.code', '=', 'BG'),
                    ('zipcode', '=', result['zip'])
                ])
            if len(city.ids) > 1:
                city = city.filtered(lambda city: city.name.lower().\
                                     startswith(result['city_name'].lower()))
            # If not found, try by name
            if not city:
                city = self.env['res.city'].search([
                    ('country_id.code', '=', 'BG'),
                    ('name', 'ilike', result['city_name'])
                ], limit=1)

            if city:
                result['city_id'] = city.id

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
        """Fetch company data from registry (manual refresh)"""
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

        # Update original EIK
        self.original_eik = self.eik

        # Populate display fields
        self.write(self._populate_display_fields(company_data))

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

        # Re-parse address to get city_id and state_id
        if company_data.get('address_full_bg'):
            parsed_address = self._parse_bulgarian_address(company_data['address_full_bg'])
            company_data.update(parsed_address)

        # Prepare partner values
        vals = self._prepare_partner_vals_from_company_data(company_data)

        # Update partner
        self.partner_id.write(vals)

        # Create or update representative contact
        if company_data.get('managers') and len(company_data['managers']) > 0:
            # Вземаме първия управител
            manager = company_data['managers'][0]

            # Търсим съществуващ представител
            existing_represent = self.partner_id.child_ids.filtered(lambda r: r.type == 'represent')

            manager_vals = {
                'name': manager.get('name', ''),
                'type': 'represent',
                'parent_id': self.partner_id.id,
            }

            # Добавяме държава ако е налична
            if manager.get('country'):
                country = self.env['res.country'].search([
                    ('name', 'ilike', manager['country'])
                ], limit=1)
                if country:
                    manager_vals['country_id'] = country.id

            if existing_represent:
                # Актуализираме съществуващия
                existing_represent.write(manager_vals)
            else:
                # Създаваме нов
                self.env['res.partner'].create(manager_vals)

        return {'type': 'ir.actions.act_window_close'}

    @api.model
    def _prepare_partner_vals_from_company_data(self, company_data):
        """
        Prepare partner values from company data

        Args:
            company_data (dict): Company data from a registry

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

        # Phone and Email
        if company_data.get('phone'):
            vals['phone'] = company_data['phone']

        if company_data.get('email'):
            vals['email'] = company_data['email']

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
