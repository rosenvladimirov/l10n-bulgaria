#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to import Bulgarian Trade Register data from CSV files
downloaded from data.egov.bg into Odoo

Usage:
    python3 import_trade_register.py --database DATABASE --csv CSV_FILE [--url URL] [--user USER] [--password PASSWORD]

Example:
    python3 import_trade_register.py --database mydb --csv /path/to/trade_register_2024.csv

Requirements:
    - xmlrpc.client (standard library)
    - csv (standard library)
    - argparse (standard library)
"""

import xmlrpc.client
import csv
import argparse
import sys
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
_logger = logging.getLogger(__name__)


class OdooImporter:
    """Importer for Bulgarian Trade Register data into Odoo"""
    
    def __init__(self, url, database, username, password):
        """
        Initialize Odoo connection
        
        Args:
            url (str): Odoo server URL
            database (str): Database name
            username (str): Username
            password (str): Password
        """
        self.url = url
        self.database = database
        self.username = username
        self.password = password
        
        # Connect to Odoo
        try:
            common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
            self.uid = common.authenticate(database, username, password, {})
            
            if not self.uid:
                raise Exception("Authentication failed")
            
            self.models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
            _logger.info(f"Connected to Odoo as user ID: {self.uid}")
            
        except Exception as e:
            _logger.error(f"Failed to connect to Odoo: {e}")
            raise
    
    def import_csv_file(self, csv_file_path, batch_size=100, delimiter=','):
        """
        Import companies from CSV file
        
        Args:
            csv_file_path (str): Path to CSV file
            batch_size (int): Number of records to process in each batch
            delimiter (str): CSV delimiter
            
        Returns:
            tuple: (imported_count, updated_count, error_count)
        """
        imported_count = 0
        updated_count = 0
        error_count = 0
        
        _logger.info(f"Starting import from: {csv_file_path}")
        
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
                # Detect delimiter if not specified
                if delimiter == 'auto':
                    sample = csvfile.read(1024)
                    csvfile.seek(0)
                    sniffer = csv.Sniffer()
                    delimiter = sniffer.sniff(sample).delimiter
                    _logger.info(f"Detected delimiter: {delimiter}")
                
                reader = csv.DictReader(csvfile, delimiter=delimiter)
                
                batch = []
                row_num = 0
                
                for row in reader:
                    row_num += 1
                    
                    try:
                        vals = self._map_csv_row_to_vals(row)
                        
                        if not vals.get('eik'):
                            _logger.warning(f"Row {row_num}: Missing EIK, skipping")
                            error_count += 1
                            continue
                        
                        batch.append(vals)
                        
                        if len(batch) >= batch_size:
                            imported, updated, errors = self._process_batch(batch)
                            imported_count += imported
                            updated_count += updated
                            error_count += errors
                            batch = []
                            
                            if row_num % 1000 == 0:
                                _logger.info(f"Processed {row_num} rows...")
                    
                    except Exception as e:
                        _logger.error(f"Row {row_num}: Error processing - {str(e)}")
                        error_count += 1
                        continue
                
                # Process remaining batch
                if batch:
                    imported, updated, errors = self._process_batch(batch)
                    imported_count += imported
                    updated_count += updated
                    error_count += errors
        
        except Exception as e:
            _logger.error(f"Error reading CSV file: {e}")
            raise
        
        _logger.info(f"Import completed: {imported_count} imported, {updated_count} updated, {error_count} errors")
        return imported_count, updated_count, error_count
    
    def _process_batch(self, batch):
        """
        Process a batch of company records
        
        Args:
            batch (list): List of company value dictionaries
            
        Returns:
            tuple: (imported, updated, errors)
        """
        imported = 0
        updated = 0
        errors = 0
        
        for vals in batch:
            try:
                eik = vals['eik']
                
                # Check if company exists
                existing_ids = self.models.execute_kw(
                    self.database, self.uid, self.password,
                    'bg.company.registry', 'search',
                    [[('eik', '=', eik)]], {'limit': 1}
                )
                
                if existing_ids:
                    # Update existing
                    self.models.execute_kw(
                        self.database, self.uid, self.password,
                        'bg.company.registry', 'write',
                        [existing_ids, vals]
                    )
                    updated += 1
                else:
                    # Create new
                    self.models.execute_kw(
                        self.database, self.uid, self.password,
                        'bg.company.registry', 'create',
                        [vals]
                    )
                    imported += 1
            
            except Exception as e:
                _logger.error(f"Error processing EIK {vals.get('eik')}: {str(e)}")
                errors += 1
        
        return imported, updated, errors
    
    def _map_csv_row_to_vals(self, row):
        """
        Map CSV row to Odoo model values
        
        Args:
            row (dict): CSV row
            
        Returns:
            dict: Model values
        """
        # Common column name variations
        eik = (row.get('EIK') or row.get('eik') or 
               row.get('ЕИК') or row.get('Eik') or '').strip()
        
        company_name = (row.get('Firma') or row.get('firma') or
                       row.get('FIRMA') or row.get('Фирма') or
                       row.get('company_name') or row.get('name') or '').strip()
        
        legal_form = (row.get('PravnaForma') or row.get('pravnaforma') or
                     row.get('PRAVNAFORMA') or row.get('Правна форма') or
                     row.get('legal_form') or '').strip()
        
        address = (row.get('Sedal_Adres') or row.get('sedal_adres') or
                  row.get('SEDAL_ADRES') or row.get('Седалищен адрес') or
                  row.get('address') or '').strip()
        
        reg_date = (row.get('DatRegistr') or row.get('datregistr') or
                   row.get('DATREGISTR') or row.get('Дата на регистрация') or
                   row.get('reg_date') or '').strip()
        
        vals = {
            'eik': eik,
            'company_name_bg': company_name,
            'legal_form_bg': legal_form,
            'address_full_bg': address,
            'registration_date': self._parse_date(reg_date),
            'status': 'active',
            'data_last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data_source': 'data.egov.bg - CSV Import',
        }
        
        # Add VAT number (BG + EIK)
        if eik:
            vals['vat_number'] = f"BG{eik}"
            vals['vat_registered'] = True
        
        # Extract city from address if possible
        if address:
            vals['city_bg'] = self._extract_city(address)
        
        return vals
    
    @staticmethod
    def _extract_city(address):
        """
        Try to extract city from Bulgarian address
        
        Args:
            address (str): Full address
            
        Returns:
            str: City name or empty string
        """
        # Common patterns: "гр. София", "с. Драгоман", "София 1000"
        import re
        
        patterns = [
            r'гр\.\s*([А-Яа-я\s-]+?)(?:,|\d|$)',
            r'град\s+([А-Яа-я\s-]+?)(?:,|\d|$)',
            r'с\.\s*([А-Яа-я\s-]+?)(?:,|\d|$)',
            r'село\s+([А-Яа-я\s-]+?)(?:,|\d|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, address)
            if match:
                return match.group(1).strip()
        
        return ''
    
    @staticmethod
    def _parse_date(date_str):
        """
        Parse date string to YYYY-MM-DD format
        
        Args:
            date_str (str): Date string
            
        Returns:
            str: Date in YYYY-MM-DD format or False
        """
        if not date_str:
            return False
        
        date_formats = [
            '%Y-%m-%d',
            '%d.%m.%Y',
            '%d/%m/%Y',
            '%Y%m%d',
        ]
        
        for fmt in date_formats:
            try:
                dt = datetime.strptime(str(date_str), fmt)
                return dt.strftime('%Y-%m-%d')
            except (ValueError, TypeError):
                continue
        
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Import Bulgarian Trade Register data from CSV into Odoo'
    )
    
    parser.add_argument('--url', type=str, default='http://localhost:8069',
                       help='Odoo server URL (default: http://localhost:8069)')
    parser.add_argument('--database', '-d', type=str, required=True,
                       help='Odoo database name')
    parser.add_argument('--user', '-u', type=str, default='admin',
                       help='Odoo username (default: admin)')
    parser.add_argument('--password', '-p', type=str,
                       help='Odoo password (will prompt if not provided)')
    parser.add_argument('--csv', '-c', type=str, required=True,
                       help='Path to CSV file')
    parser.add_argument('--batch-size', type=int, default=100,
                       help='Batch size for processing (default: 100)')
    parser.add_argument('--delimiter', type=str, default='auto',
                       help='CSV delimiter (default: auto-detect)')
    
    args = parser.parse_args()
    
    # Prompt for password if not provided
    if not args.password:
        import getpass
        args.password = getpass.getpass('Password: ')
    
    try:
        # Initialize importer
        importer = OdooImporter(args.url, args.database, args.user, args.password)
        
        # Import data
        imported, updated, errors = importer.import_csv_file(
            args.csv,
            batch_size=args.batch_size,
            delimiter=args.delimiter
        )
        
        print("\n" + "="*60)
        print("IMPORT SUMMARY")
        print("="*60)
        print(f"Imported: {imported} new companies")
        print(f"Updated:  {updated} existing companies")
        print(f"Errors:   {errors}")
        print("="*60)
        
        return 0
    
    except Exception as e:
        _logger.error(f"Import failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
