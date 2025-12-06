# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    """Extension of res.partner to add Bulgarian company registry integration"""
    _inherit = 'res.partner'

    # Note: name field is already multilingual (translate=True) via res.transliterate.mixin
    # We use it directly for Bulgarian and English company names
    # Note: company_registry field already exists in base Odoo for company registration numbers

    # Bulgarian company fields (all prefixed with l10n_bg for consistency)
    l10n_bg_legal_form = fields.Char(
        string='Legal Form (Bulgarian)',
        help='Bulgarian legal form (ООД, ЕООД, АД, etc.)'
    )
    l10n_bg_registration_date = fields.Date(
        string='Registration Date',
        help='Date of company registration in Bulgarian Trade Register'
    )
    l10n_bg_registration_court = fields.Char(
        string='Registration Court',
        help='Court where company is registered'
    )
    l10n_bg_activity_code = fields.Char(
        string='Activity Code (NACE)',
        help='Main economic activity code'
    )
    l10n_bg_activity_description = fields.Text(
        string='Activity Description'
    )

    # Link to registry data
    l10n_bg_registry_id = fields.Many2one(
        'bg.company.registry',
        string='Registry Data',
        ondelete='set null',
        help='Link to Bulgarian Company Registry data'
    )
    l10n_bg_registry_last_sync = fields.Datetime(
        string='Last Registry Sync',
        readonly=True,
        help='Last time data was synchronized with registry'
    )

    @api.onchange('l10n_bg_uic')
    def _onchange_l10n_bg_uic(self):
        """When UIC/EIK changes, offer to fetch company data"""
        if self.l10n_bg_uic and self.l10n_bg_uic_type in ('bg_uic',) and len(self.l10n_bg_uic) >= 9:
            # Check if we have registry data
            registry_model = self.env['bg.company.registry']
            registry_data = registry_model.search([('eik', '=', self.l10n_bg_uic)], limit=1)

            if registry_data:
                return {
                    'warning': {
                        'title': _('Company Data Found'),
                        'message': _('Company data found in registry for EIK: %s. '
                                   'You can use the "Fetch from Registry" button to populate fields.') % self.l10n_bg_uic
                    }
                }

    def action_fetch_from_registry(self):
        """
        Fetch and populate company data from Bulgarian Company Registry
        """
        self.ensure_one()

        if not self.l10n_bg_uic:
            raise UserError(_('Please enter EIK number first (in VAT field with BG prefix or UIC field)'))

        # Search in registry
        registry_model = self.env['bg.company.registry']
        company_data = registry_model.search_company_by_eik(self.l10n_bg_uic)

        if not company_data:
            raise UserError(_('No company data found for EIK: %s\n\n'
                            'Make sure you have imported the Trade Register data '
                            'or the company exists in the registry.') % self.l10n_bg_uic)

        # Populate partner fields
        vals = self._prepare_partner_vals_from_registry(company_data)
        self.write(vals)

        # If we have official English name from registry, override transliteration
        if company_data.get('company_name_en'):
            self.with_context(lang='en_US').write({
                'name': company_data['company_name_en']
            })

        # Link to registry record
        registry_record = registry_model.search([('eik', '=', self.l10n_bg_uic)], limit=1)
        if registry_record:
            self.l10n_bg_registry_id = registry_record.id

        self.l10n_bg_registry_last_sync = fields.Datetime.now()

        # Auto-populate representative if available in registry data
        self._populate_representative_from_registry(company_data)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Company data has been populated from registry'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_search_and_populate(self):
        """
        Open the wizard to search for company and populate data
        """
        self.ensure_one()

        return {
            'name': _('Search Bulgarian Company'),
            'type': 'ir.actions.act_window',
            'res_model': 'bg.company.search.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'default_search_eik': self.l10n_bg_uic or '',
            }
        }

    @api.model
    def _prepare_partner_vals_from_registry(self, company_data):
        """
        Prepare partner values from registry data

        Args:
            company_data (dict): Company data from registry

        Returns:
            dict: Partner values
        """
        vals = {}

        # Company name - use multilingual name field
        # The name field is translate=True, so we can set it in different languages
        if company_data.get('company_name_bg'):
            vals['name'] = company_data['company_name_bg']

        # Store English name in ref field for easy access
        if company_data.get('company_name_en'):
            vals['ref'] = company_data['company_name_en']

        # UIC/EIK (using existing l10n_bg_uic field)
        if company_data.get('eik'):
            vals['l10n_bg_uic'] = company_data['eik']
            vals['l10n_bg_uic_type'] = 'bg_uic'

        # VAT - set with BG prefix to trigger validation
        if company_data.get('vat_number'):
            vals['vat'] = company_data['vat_number']
        elif company_data.get('eik'):
            # Generate VAT from EIK if not present
            vals['vat'] = f"BG{company_data['eik']}"

        # Legal form
        if company_data.get('legal_form_bg'):
            vals['l10n_bg_legal_form'] = company_data['legal_form_bg']

        # Address
        if company_data.get('city_bg'):
            vals['city'] = company_data['city_bg']

        if company_data.get('postal_code'):
            vals['zip'] = company_data['postal_code']

        if company_data.get('street_bg'):
            vals['street'] = company_data['street_bg']
        elif company_data.get('address_full_bg'):
            # Use full address if street is not available
            vals['street'] = company_data['address_full_bg']

        # Country (Bulgaria)
        country_bg = self.env['res.country'].search([('code', '=', 'BG')], limit=1)
        if country_bg:
            vals['country_id'] = country_bg.id

        # Registration info
        if company_data.get('registration_date'):
            vals['l10n_bg_registration_date'] = company_data['registration_date']

        if company_data.get('registration_number'):
            vals['company_registry'] = company_data['registration_number']

        if company_data.get('court'):
            vals['l10n_bg_registration_court'] = company_data['court']

        # Activity
        if company_data.get('activity_code'):
            vals['l10n_bg_activity_code'] = company_data['activity_code']

        if company_data.get('activity_description_bg'):
            vals['l10n_bg_activity_description'] = company_data['activity_description_bg']

        # Set as company
        vals['is_company'] = True
        vals['company_type'] = 'company'

        return vals

    @api.model
    def create_partner_from_eik(self, eik):
        """
        Create a new partner from EIK number

        Args:
            eik (str): Company EIK

        Returns:
            res.partner: Created partner record
        """
        registry_model = self.env['bg.company.registry']
        company_data = registry_model.search_company_by_eik(eik)

        if not company_data:
            raise UserError(_('No company data found for EIK: %s') % eik)

        vals = self._prepare_partner_vals_from_registry(company_data)
        partner = self.create(vals)

        # If we have official English name from registry, override transliteration
        if company_data.get('company_name_en'):
            partner.with_context(lang='en_US').write({
                'name': company_data['company_name_en']
            })

        # Link to registry
        registry_record = registry_model.search([('eik', '=', eik)], limit=1)
        if registry_record:
            partner.l10n_bg_registry_id = registry_record.id

        partner.l10n_bg_registry_last_sync = fields.Datetime.now()

        # Auto-populate representative
        partner._populate_representative_from_registry(company_data)

        return partner

    def _populate_representative_from_registry(self, company_data):
        """
        Automatically populate the first representative / manager from registry data

        Args:
            company_data (dict): Company data from a registry
        """
        self.ensure_one()

        # Check if we have representative data in a registry
        # This assumes registry data has 'representative_name' and optionally 'representative_egn'
        rep_name = company_data.get('representative_name')
        rep_egn = company_data.get('representative_egn')

        if not rep_name:
            return

        # Check if a representative already exists
        if self.l10n_bg_represent_contact_id:
            _logger.info(f"Representative already exists for {self.name}")
            return

        # Search for existing contact with the same name or EGN
        existing_rep = False
        if rep_egn:
            # Try to find by EGN first (more precise)
            existing_rep = self.env['res.partner'].search([
                '|',
                ('l10n_bg_uic', '=', rep_egn),
                ('vat', '=', rep_egn),
                ('type', 'in', ['contact', 'represent'])
            ], limit=1)

        if not existing_rep:
            # Try to find by name in existing contacts of this company
            existing_rep = self.child_ids.filtered(
                lambda c: c.name and rep_name.lower() in c.name.lower()
            )
            if existing_rep:
                existing_rep = existing_rep[0]

        if existing_rep:
            # Use existing representative
            _logger.info(f"Using existing representative {existing_rep.name} for {self.name}")
            self.l10n_bg_represent_contact_id = existing_rep.id
        else:
            # Create new representative contact
            rep_vals = {
                'name': rep_name,
                'type': 'represent',
                'parent_id': self.id,
                'is_company': False,
            }

            # Add EGN if available
            if rep_egn:
                rep_vals['vat'] = rep_egn
                rep_vals['l10n_bg_uic'] = rep_egn
                rep_vals['l10n_bg_uic_type'] = 'bg_egn'

            _logger.info(f"Creating new representative {rep_name} for {self.name}")
            representative = self.env['res.partner'].create(rep_vals)
            self.l10n_bg_represent_contact_id = representative.id

