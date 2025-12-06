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

    def _fetch_from_ckan_api(self, eik):
        """
        Fetch company data from data.egov.bg API

        Note: data.egov.bg may have changed their API structure.
        This method tries multiple approaches.

        Args:
            eik (str): Company EIK number

        Returns:
            dict: Company data or False
        """
        if not eik:
            return False

        try:
            _logger.info(f"Fetching company data from data.egov.bg for EIK: {eik}")

            # Approach 1: Try the custom data.egov.bg API
            # Based on: https://data.egov.bg/api/getDatasetDetails
            try:
                custom_api_url = "https://data.egov.bg/api/getDatasetDetails"
                response = requests.get(
                    custom_api_url,
                    params={'dataset_uri': '5b15917a'},  # Trade Register dataset
                    timeout=30
                )

                if response.status_code == 200:
                    _logger.info("Successfully connected to data.egov.bg custom API")
                    # Parse response and search for EIK
                    # Note: The actual structure depends on the API response
                    data = response.json()
                    # TODO: Parse the data structure once we know the format

            except Exception as e:
                _logger.debug(f"Custom API approach failed: {str(e)}")

            # Approach 2: Try CKAN API with correct base URL
            base_url = "https://data.egov.bg/api/3/action"

            # Try to search packages/datasets
            search_url = f"{base_url}/package_search"
            response = requests.get(
                search_url,
                params={
                    'q': f'name:trade-register OR title:търговски*',
                    'rows': 5
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    datasets = result.get('result', {}).get('results', [])
                    _logger.info(f"Found {len(datasets)} datasets related to trade register")

                    # Try to find the correct dataset
                    for dataset in datasets:
                        dataset_id = dataset.get('id') or dataset.get('name')
                        _logger.info(f"Checking dataset: {dataset.get('title')} (ID: {dataset_id})")

                        # Get package details
                        package_url = f"{base_url}/package_show"
                        pkg_response = requests.get(
                            package_url,
                            params={'id': dataset_id},
                            timeout=30
                        )

                        if pkg_response.status_code == 200:
                            pkg_data = pkg_response.json()
                            if pkg_data.get('success'):
                                resources = pkg_data.get('result', {}).get('resources', [])

                                # Search through resources
                                for resource in resources:
                                    resource_url = resource.get('url')
                                    resource_format = resource.get('format', '').upper()

                                    if resource_format in ['CSV', 'TXT', 'XLSX', 'XLS']:
                                        _logger.info(f"Found resource: {resource.get('name')} ({resource_format})")
                                        # Try to search in this resource
                                        company_data = self._search_in_resource(resource_url, resource_format, eik)
                                        if company_data:
                                            return company_data
            else:
                _logger.warning(f"CKAN API search returned status: {response.status_code}")

            _logger.info(f"Company with EIK {eik} not found in data.egov.bg")
            return False

        except requests.Timeout:
            _logger.error("Timeout while fetching data from data.egov.bg")
            return False
        except requests.RequestException as e:
            _logger.error(f"Error fetching data from data.egov.bg API: {str(e)}")
            return False
        except Exception as e:
            _logger.error(f"Unexpected error in data.egov.bg API fetch: {str(e)}")
            return False

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

            # First, try to fetch from CKAN API
            _logger.info(f"Attempting to fetch company data from CKAN API for EIK: {eik}")
            company_data = self._fetch_from_ckan_api(eik)

            if company_data:
                _logger.info(f"Company data found in CKAN API for EIK: {eik}")

                # Store in a local registry
                existing_company = registry_model.search([('eik', '=', eik)], limit=1)

                if existing_company:
                    # Update existing record
                    existing_company.write({
                        'company_name_bg': company_data.get('company_name_bg'),
                        'legal_form_bg': company_data.get('legal_form_bg'),
                        'address_full_bg': company_data.get('address_full_bg'),
                        'city_bg': company_data.get('city_bg'),
                        'vat_number': company_data.get('vat_number'),
                        'data_last_updated': fields.Datetime.now(),
                    })
                    company = existing_company
                else:
                    # Create a new record
                    company = registry_model.create({
                        'eik': company_data.get('eik'),
                        'company_name_bg': company_data.get('company_name_bg'),
                        'legal_form_bg': company_data.get('legal_form_bg'),
                        'address_full_bg': company_data.get('address_full_bg'),
                        'city_bg': company_data.get('city_bg'),
                        'vat_number': company_data.get('vat_number'),
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
                    raise UserError(_('No company found with EIK: %s\n\n'
                                      'The company was not found in data.egov.bg or local registry.\n'
                                      'Make sure you have imported the Trade Register data.') % eik)

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
