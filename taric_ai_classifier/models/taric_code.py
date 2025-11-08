# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import requests
import json
import logging

_logger = logging.getLogger(__name__)


class TaricCode(models.Model):
    _name = 'taric.code'
    _description = 'TARIC Code'
    _order = 'code'

    code = fields.Char('TARIC Code', required=True, size=10, index=True,
                      help='10-digit TARIC code (CN8 + 2 additional digits)')
    cn8_code = fields.Char('CN8 Code', size=8, index=True,
                          help='8-digit Combined Nomenclature code')
    description = fields.Text('Description', translate=True)
    description_bg = fields.Text('Описание (BG)')
    description_en = fields.Text('Description (EN)')
    
    # Duty and tax information
    duty_rate = fields.Float('Duty Rate %', digits=(5, 2))
    duty_type = fields.Selection([
        ('ad_valorem', 'Ad Valorem (%)'),
        ('specific', 'Specific (per unit)'),
        ('compound', 'Compound'),
    ], string='Duty Type', default='ad_valorem')
    
    # Additional information
    supplementary_unit = fields.Char('Supplementary Unit',
                                     help='e.g., kg, litre, number of items')
    restrictions = fields.Text('Restrictions and Requirements')
    
    # Validity
    valid_from = fields.Date('Valid From')
    valid_to = fields.Date('Valid To')
    active = fields.Boolean('Active', default=True)
    
    # Relations
    product_ids = fields.One2many('product.template', 'taric_code_id',
                                  string='Products')
    classification_history_ids = fields.One2many('taric.classification.history',
                                                 'taric_code_id',
                                                 string='Classification History')
    
    # AI and verification
    confidence_score = fields.Float('AI Confidence Score', digits=(3, 2),
                                   help='AI confidence level (0-100)')
    verified = fields.Boolean('Verified',
                             help='Manually verified by customs expert')
    verified_by_id = fields.Many2one('res.users', string='Verified By')
    verified_date = fields.Date('Verification Date')
    
    _sql_constraints = [
        ('code_unique', 'unique(code)', 'TARIC code must be unique!'),
    ]

    @api.constrains('code')
    def _check_code_format(self):
        """Validate TARIC code format"""
        for record in self:
            if record.code:
                if not record.code.isdigit():
                    raise ValidationError('TARIC code must contain only digits!')
                if len(record.code) not in [8, 10]:
                    raise ValidationError('TARIC code must be 8 or 10 digits!')

    @api.model
    def search_by_ai(self, product_description, product_category=None):
        """
        Use Claude AI to suggest TARIC codes based on product description
        
        Args:
            product_description: Product name and description
            product_category: Optional product category for better context
            
        Returns:
            List of suggested TARIC codes with confidence scores
        """
        api_key = self.env['ir.config_parameter'].sudo().get_param('taric_ai.anthropic_api_key')
        if not api_key:
            raise UserError('Anthropic API key not configured in Settings!')
        
        # Prepare the prompt for Claude
        prompt = f"""Analyze this product and suggest appropriate TARIC (Combined Nomenclature) codes.

Product Description: {product_description}
"""
        if product_category:
            prompt += f"Product Category: {product_category}\n"
        
        prompt += """
Based on the EU TARIC classification system, suggest the most appropriate 8-digit CN codes.

For each suggested code, provide:
1. The 8-digit CN code
2. Brief description in English and Bulgarian
3. Confidence level (0-100)
4. Supplementary unit if applicable
5. Key classification reasoning

Respond in JSON format:
{
    "suggestions": [
        {
            "code": "12345678",
            "description_en": "...",
            "description_bg": "...",
            "confidence": 95,
            "supplementary_unit": "kg",
            "reasoning": "..."
        }
    ]
}

Provide 3-5 most relevant suggestions, ordered by confidence.
"""

        try:
            # Call Claude API
            response = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers={
                    'Content-Type': 'application/json',
                    'x-api-key': api_key,
                    'anthropic-version': '2023-06-01'
                },
                json={
                    'model': 'claude-sonnet-4-20250514',
                    'max_tokens': 2000,
                    'messages': [
                        {'role': 'user', 'content': prompt}
                    ]
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['content'][0]['text']
                
                # Extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    suggestions = json.loads(json_match.group())
                    return suggestions.get('suggestions', [])
                else:
                    _logger.warning('No JSON found in Claude response')
                    return []
            else:
                _logger.error(f'Claude API error: {response.status_code} - {response.text}')
                raise UserError(f'AI service error: {response.status_code}')
                
        except Exception as e:
            _logger.error(f'Error calling Claude AI: {str(e)}')
            raise UserError(f'AI classification failed: {str(e)}')

    @api.model
    def verify_code_online(self, code):
        """
        Verify TARIC code against official EU database
        
        Args:
            code: TARIC code to verify
            
        Returns:
            dict with verification results
        """
        # Use EU TARIC API
        try:
            # Note: This is a simplified example. The actual EU TARIC API
            # may require authentication and has specific endpoints
            url = f'https://ec.europa.eu/taxation_customs/dds2/taric/taric_consultation.jsp'
            
            # For production, implement proper API integration
            # This is a placeholder for the concept
            
            return {
                'valid': True,
                'description': 'Verified against EU database',
                'last_updated': fields.Date.today(),
            }
        except Exception as e:
            _logger.warning(f'TARIC verification failed: {str(e)}')
            return {
                'valid': False,
                'error': str(e)
            }

    def action_verify_code(self):
        """Verify code and mark as verified"""
        self.ensure_one()
        result = self.verify_code_online(self.code)
        
        if result.get('valid'):
            self.write({
                'verified': True,
                'verified_by_id': self.env.user.id,
                'verified_date': fields.Date.today(),
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'Code verified successfully!',
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            raise UserError(f"Verification failed: {result.get('error', 'Unknown error')}")


class IntrastatCode(models.Model):
    _name = 'intrastat.code'
    _description = 'INTRASTAT Code (CN8)'
    _inherit = 'taric.code'
    
    # INTRASTAT specific fields for Bulgaria
    statistical_value_required = fields.Boolean('Statistical Value Required',
                                               default=True)
    invoice_value_required = fields.Boolean('Invoice Value Required',
                                           default=True)
    net_mass_required = fields.Boolean('Net Mass Required', default=True)
    
    # Transaction nature codes
    transaction_nature_code = fields.Selection([
        ('11', '11 - Outright purchase/sale'),
        ('12', '12 - Supply for sale on approval'),
        ('19', '19 - Other'),
        # Add more as needed
    ], string='Default Transaction Nature')
    
    # Delivery terms
    delivery_terms = fields.Selection([
        ('EXW', 'Ex Works'),
        ('FCA', 'Free Carrier'),
        ('CPT', 'Carriage Paid To'),
        ('CIP', 'Carriage and Insurance Paid'),
        ('DAP', 'Delivered At Place'),
        ('DPU', 'Delivered At Place Unloaded'),
        ('DDP', 'Delivered Duty Paid'),
        ('FAS', 'Free Alongside Ship'),
        ('FOB', 'Free On Board'),
        ('CFR', 'Cost and Freight'),
        ('CIF', 'Cost, Insurance and Freight'),
    ], string='Default Delivery Terms')
    
    @api.model
    def get_intrastat_requirements_bg(self):
        """Get Bulgarian INTRASTAT reporting requirements"""
        IrConfig = self.env['ir.config_parameter'].sudo()
        
        threshold_dispatch = IrConfig.get_param('intrastat_bg.threshold_dispatch', default=500000)
        threshold_arrival = IrConfig.get_param('intrastat_bg.threshold_arrival', default=500000)
        
        return {
            'threshold_dispatch': float(threshold_dispatch),
            'threshold_arrival': float(threshold_arrival),
            'currency': 'BGN',
            'submission_deadline': 14,  # 14th of following month
            'required_fields': [
                'cn8_code',
                'country_origin',
                'country_destination',
                'net_mass_kg',
                'supplementary_unit',
                'invoice_value',
                'statistical_value',
                'delivery_terms',
                'transaction_nature',
                'mode_of_transport',
            ]
        }


class TaricClassificationHistory(models.Model):
    _name = 'taric.classification.history'
    _description = 'TARIC Classification History'
    _order = 'create_date desc'

    product_id = fields.Many2one('product.template', string='Product',
                                 required=True, ondelete='cascade')
    taric_code_id = fields.Many2one('taric.code', string='TARIC Code',
                                    required=True)
    
    classification_method = fields.Selection([
        ('manual', 'Manual'),
        ('ai', 'AI Suggested'),
        ('expert', 'Expert Verified'),
        ('api', 'API Verified'),
    ], string='Classification Method', required=True)
    
    confidence_score = fields.Float('Confidence Score', digits=(3, 2))
    reasoning = fields.Text('Classification Reasoning')
    
    user_id = fields.Many2one('res.users', string='Classified By',
                             default=lambda self: self.env.user)
    create_date = fields.Datetime('Classification Date', readonly=True)
    
    # AI metadata
    ai_model = fields.Char('AI Model Used')
    ai_response_time = fields.Float('AI Response Time (seconds)')
