# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import requests
import json
import logging

_logger = logging.getLogger(__name__)


class TaricCode(models.Model):
    """
    TARIC Code model for AI-powered HS code classification.
    Suggests HS codes via AI and stores classification metadata.
    """
    _name = 'taric.code'
    _description = 'TARIC Code'
    _order = 'code'
    _rec_names_search = ['code', 'description']

    code = fields.Char('HS/TARIC Code', required=True, index=True,
                       help='8-10 digit HS or TARIC code')
    description = fields.Text('Description', translate=True)

    # Duty information
    duty_rate = fields.Float('Duty Rate %', digits=(5, 2))

    # Validity period
    valid_from = fields.Date('Valid From')
    valid_to = fields.Date('Valid To')
    active = fields.Boolean('Active', default=True)

    # Relations
    product_ids = fields.One2many('product.template', 'taric_code_id', string='Products')
    classification_history_ids = fields.One2many('taric.classification.history', 'taric_code_id', string='History')

    # AI classification metadata
    confidence_score = fields.Float('AI Confidence', digits=(3, 2),
                                    help='AI confidence level (0-100)')
    verified = fields.Boolean('Verified', help='Verified by customs expert')
    verified_by_id = fields.Many2one('res.users', string='Verified By')
    verified_date = fields.Date('Verification Date')

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'HS/TARIC code must be unique!'),
    ]

    @api.depends('code', 'description')
    def _compute_display_name(self):
        """Display as 'CODE - Description'"""
        for record in self:
            if record.description:
                record.display_name = f'{record.code} - {record.description[:50]}'
            else:
                record.display_name = record.code or 'New'

    @api.constrains('code')
    def _check_code_format(self):
        """Validate HS/TARIC code format"""
        for record in self:
            if record.code:
                if not record.code.isdigit():
                    raise ValidationError('HS/TARIC code must contain only digits!')
                if len(record.code) not in [6, 8, 10]:
                    raise ValidationError('HS/TARIC code must be 6, 8 or 10 digits!')

    @api.model
    def search_by_ai(self, product_description, product_category=None):
        """
        Use Claude AI to suggest HS codes based on product description

        Args:
            product_description: Product name and description
            product_category: Optional product category

        Returns:
            List of suggested HS codes with confidence scores
        """
        api_key = self.env['ir.config_parameter'].sudo().get_param('taric_ai.anthropic_api_key')
        if not api_key:
            raise UserError('Anthropic API key not configured in Settings!')

        prompt = f"""Analyze this product and suggest appropriate HS commodity codes.

Product: {product_description}
"""
        if product_category:
            prompt += f"Category: {product_category}\n"

        prompt += """
Suggest the 3-5 most appropriate HS commodity codes (8 digits for EU/CN8 codes).

Respond ONLY with valid JSON:
{
    "suggestions": [
        {
            "code": "12345678",
            "description": "Product description",
            "confidence": 95,
            "reasoning": "Why this code fits"
        }
    ]
}
"""

        try:
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
                    'messages': [{'role': 'user', 'content': prompt}]
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                content = result['content'][0]['text']

                # Extract JSON
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    suggestions = json.loads(json_match.group())
                    return suggestions.get('suggestions', [])
                else:
                    _logger.warning('No JSON in Claude response')
                    return []
            else:
                _logger.error(f'Claude API error: {response.status_code}')
                raise UserError(f'AI service error: {response.status_code}')

        except Exception as e:
            _logger.error(f'AI classification error: {str(e)}')
            raise UserError(f'AI classification failed: {str(e)}')

    def action_verify_code(self):
        """Verify code and mark as verified"""
        self.ensure_one()

        self.write({
            'verified': True,
            'verified_by_id': self.env.user.id,
            'verified_date': fields.Date.today(),
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'Code {self.code} verified successfully!',
                'type': 'success',
                'sticky': False,
            }
        }


class TaricClassificationHistory(models.Model):
    """Track all product classification changes"""
    _name = 'taric.classification.history'
    _description = 'TARIC Classification History'
    _order = 'create_date desc'

    product_id = fields.Many2one('product.template', required=True, ondelete='cascade', index=True)
    taric_code_id = fields.Many2one('taric.code', required=True, index=True)
    classification_method = fields.Selection([
        ('manual', 'Manual'),
        ('ai', 'AI Suggested'),
        ('expert', 'Expert Verified'),
    ], required=True, index=True)
    confidence_score = fields.Float('Confidence %', digits=(3, 2))
    reasoning = fields.Text('Reasoning')
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user, index=True)
    create_date = fields.Datetime('Date', readonly=True, index=True)
    ai_model = fields.Char('AI Model')
