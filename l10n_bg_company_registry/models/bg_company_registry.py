# -*- coding: utf-8 -*-

import logging
import requests
import json
import csv
from io import StringIO
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BgCompanyRegistry(models.Model):
    """Model for Bulgarian Company Registry data from Open Data Portal"""
    _name = 'bg.company.registry'
    _description = 'Bulgarian Company Registry Data'
    _rec_name = 'company_name_bg'

    # Company identification
    eik = fields.Char(
        string='EIK',
        required=True,
        index=True,
        help='Bulgarian Company Identification Number'
    )
    bulstat = fields.Char(
        string='BULSTAT',
        index=True,
        help='Legacy Bulgarian company ID (pre-2007)'
    )

    # Company names
    company_name_bg = fields.Char(
        string='Company Name (BG)',
        index=True,
        required=True
    )
    company_name_en = fields.Char(
        string='Company Name (EN)',
        index=True
    )

    # Legal information
    legal_form_bg = fields.Char(string='Legal Form (BG)')
    legal_form_en = fields.Char(string='Legal Form (EN)')

    # VAT information
    vat_number = fields.Char(
        string='VAT Number',
        help='VAT registration number if company is VAT registered'
    )
    vat_registered = fields.Boolean(
        string='VAT Registered',
        default=False
    )

    # Address information
    address_full_bg = fields.Text(string='Full Address (BG)')
    address_full_en = fields.Text(string='Full Address (EN)')
    city_bg = fields.Char(string='City (BG)')
    city_en = fields.Char(string='City (EN)')
    postal_code = fields.Char(string='Postal Code')
    street_bg = fields.Char(string='Street (BG)')
    street_en = fields.Char(string='Street (EN)')
    country_code = fields.Char(string='Country Code', default='BG')

    # Registration information
    registration_date = fields.Date(string='Registration Date')
    registration_number = fields.Char(string='Registration Number')
    court = fields.Char(string='Registration Court')

    # Status
    status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('liquidation', 'In Liquidation'),
        ('deleted', 'Deleted')
    ], string='Status', default='active')

    # Additional information
    activity_code = fields.Char(string='Activity Code (NACE)')
    activity_description_bg = fields.Text(string='Activity Description (BG)')
    activity_description_en = fields.Text(string='Activity Description (EN)')

    # Data source tracking
    data_source = fields.Char(
        string='Data Source',
        default='data.egov.bg',
        readonly=True
    )
    data_last_updated = fields.Datetime(
        string='Data Last Updated',
        readonly=True
    )

    # Link to partner
    partner_id = fields.Many2one(
        'res.partner',
        string='Related Partner',
        ondelete='set null'
    )

    _sql_constraints = [
        ('eik_unique', 'unique(eik)', 'EIK must be unique!')
    ]

    @api.model
    def _get_ckan_api_base_url(self):
        """Get CKAN API base URL"""
        return "https://data.egov.bg/api/3/action"

    @api.model
    def _get_trade_register_dataset_id(self):
        """Get Trade Register dataset ID"""
        return "2df0c2af-e769-4397-be33-fcbe269806f3"

    @api.model
    def search_company_by_eik(self, eik):
        """
        Search for a company by EIK

        Args:
            eik (str): Company EIK number

        Returns:
            dict: Company data or False
        """
        if not eik:
            raise ValidationError(_('EIK is required for company search'))

        # Clean EIK (remove spaces, leading zeros for search)
        eik_clean = eik.strip().lstrip('0') if eik else ''

        # First check if we have cached data
        cached_company = self.search([('eik', '=', eik)], limit=1)
        if cached_company:
            _logger.info(f"Found cached company data for EIK: {eik}")
            return cached_company._prepare_company_data_dict()

        # If not cached, search in Open Data Portal
        _logger.info(f"Searching Open Data Portal for EIK: {eik}")
        try:
            # In a real implementation, you would query the CKAN API
            # or work with downloaded CSV files
            # For now, return False to indicate no data found
            return False
        except Exception as e:
            _logger.error(f"Error searching for company with EIK {eik}: {str(e)}")
            raise UserError(_('Error searching for company: %s') % str(e))

    @api.model
    def search_company_by_name(self, company_name, limit=10):
        """
        Search for companies by name

        Args:
            company_name (str): Company name to search (Bulgarian or English)
            limit (int): Maximum number of results

        Returns:
            list: List of company data dictionaries
        """
        if not company_name or len(company_name) < 3:
            raise ValidationError(_('Company name must be at least 3 characters'))

        # Search in cached data
        domain = [
            '|',
            ('company_name_bg', 'ilike', company_name),
            ('company_name_en', 'ilike', company_name)
        ]
        cached_companies = self.search(domain, limit=limit)

        if cached_companies:
            _logger.info(f"Found {len(cached_companies)} cached companies matching: {company_name}")
            return [company._prepare_company_data_dict() for company in cached_companies]

        return []

    def _prepare_company_data_dict(self):
        """
        Prepare company data dictionary for use in wizards and partner creation

        Returns:
            dict: Company data
        """
        self.ensure_one()
        return {
            'eik': self.eik,
            'bulstat': self.bulstat,
            'company_name_bg': self.company_name_bg,
            'company_name_en': self.company_name_en,
            'legal_form_bg': self.legal_form_bg,
            'legal_form_en': self.legal_form_en,
            'vat_number': self.vat_number,
            'vat_registered': self.vat_registered,
            'address_full_bg': self.address_full_bg,
            'address_full_en': self.address_full_en,
            'city_bg': self.city_bg,
            'city_en': self.city_en,
            'postal_code': self.postal_code,
            'street_bg': self.street_bg,
            'street_en': self.street_en,
            'registration_date': self.registration_date,
            'registration_number': self.registration_number,
            'activity_code': self.activity_code,
            'activity_description_bg': self.activity_description_bg,
            'status': self.status,
        }

    @api.model
    def import_csv_data(self, csv_file_path):
        """
        Import company data from CSV file
        This is useful for offline operation with downloaded data dumps

        Args:
            csv_file_path (str): Path to CSV file

        Returns:
            int: Number of companies imported
        """
        if not csv_file_path:
            raise ValidationError(_('CSV file path is required'))

        imported_count = 0

        try:
            with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
                # Try to detect the CSV format
                sample = csvfile.read(1024)
                csvfile.seek(0)

                # Detect delimiter
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter

                reader = csv.DictReader(csvfile, delimiter=delimiter)

                for row in reader:
                    try:
                        # Map CSV columns to model fields
                        # Note: Column names may vary depending on the actual data structure
                        vals = self._map_csv_row_to_vals(row)

                        if vals.get('eik'):
                            # Check if company already exists
                            existing = self.search([('eik', '=', vals['eik'])], limit=1)
                            if existing:
                                existing.write(vals)
                            else:
                                self.create(vals)
                            imported_count += 1

                    except Exception as e:
                        _logger.warning(f"Error importing row: {str(e)}")
                        continue

        except Exception as e:
            _logger.error(f"Error reading CSV file: {str(e)}")
            raise UserError(_('Error reading CSV file: %s') % str(e))

        return imported_count

    @api.model
    def _map_csv_row_to_vals(self, row):
        """
        Map CSV row to model values

        Args:
            row (dict): CSV row data

        Returns:
            dict: Model values
        """
        # This mapping depends on the actual CSV structure from data.egov.bg
        # You'll need to adjust these field names based on the real data
        vals = {
            'eik': row.get('EIK') or row.get('eik'),
            'company_name_bg': row.get('Firma') or row.get('company_name'),
            'legal_form_bg': row.get('PravnaForma') or row.get('legal_form'),
            'address_full_bg': row.get('Sedal_Adres') or row.get('address'),
            'registration_date': self._parse_date(row.get('DatRegistr') or row.get('reg_date')),
            'status': 'active',  # Default status
            'data_last_updated': fields.Datetime.now(),
        }

        # Add VAT number if exists (format: BG + EIK)
        if vals.get('eik'):
            vals['vat_number'] = f"BG{vals['eik']}"

        return vals

    @api.model
    def _parse_date(self, date_str):
        """
        Parse date string to date object

        Args:
            date_str (str): Date string

        Returns:
            date: Parsed date or False
        """
        if not date_str:
            return False

        # Try different date formats
        date_formats = [
            '%Y-%m-%d',
            '%d.%m.%Y',
            '%d/%m/%Y',
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(str(date_str), fmt).date()
            except (ValueError, TypeError):
                continue

        return False

    def action_create_partner(self):
        """Create a partner from registry data"""
        self.ensure_one()

        if self.partner_id:
            raise UserError(_('Partner already exists for this company'))

        # Prepare partner values
        company_data = self._prepare_company_data_dict()
        partner_model = self.env['res.partner']
        vals = partner_model._prepare_partner_vals_from_registry(company_data)

        # Create partner
        partner = partner_model.create(vals)

        # Link partner to registry
        self.partner_id = partner.id
        partner.l10n_bg_registry_id = self.id
        partner.l10n_bg_registry_last_sync = fields.Datetime.now()

        # Open created partner
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': partner.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_partner(self):
        """View linked partner"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError(_('No partner linked to this company'))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': self.partner_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
