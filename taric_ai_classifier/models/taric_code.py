# -*- coding: utf-8 -*-
import json
import logging
import os
import re

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

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

    def action_view_products(self):
        """View products using this TARIC code"""
        self.ensure_one()
        return {
            'name': f'Products - {self.code}',
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': [('taric_code_id', '=', self.id)],
            'context': {'default_taric_code_id': self.id}
        }

    @api.model
    def search_by_ai(self, product_description, product_category=None):
        """
        Ползва ai_agent_core за AI класификация на продукти.
        Изпраща заявка към Claude Code CLI чрез ядрото.

        Args:
            product_description: Име и описание на продукта
            product_category: Категория (опционално)

        Returns:
            Списък с предложени HS кодове с confidence scores
        """
        # Изграждаме въпрос за Claude
        question = f"""Analyze this product and suggest appropriate HS commodity codes.

Product: {product_description}
"""
        if product_category:
            question += f"Category: {product_category}\n"

        question += """
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

        # Намираме пътя на модула за контекст
        module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Създаваме заявка към ai_agent_core
        agent_request = self.env['ai.agent.request'].create({
            'module_path': module_path,
            'question': question,
            'permission_mode': 'plan',  # read-only — няма нужда от write
            'allowed_tools': 'Read,Grep,Glob',
        })

        try:
            # Синхронно изпълнение — чакаме резултат
            agent_request._validate_request()
            agent_request._generate_context()
            agent_request.env.cr.commit()
            agent_request._run_claude()

            if agent_request.state == 'error':
                raise UserError(
                    'AI classification failed: %s' % agent_request.error_message
                )

            # Парсваме резултата
            result_text = agent_request.result_text or ''
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return data.get('suggestions', [])
            else:
                _logger.warning('No JSON in AI agent response')
                return []

        except UserError:
            raise
        except Exception as e:
            _logger.error('AI classification error: %s', e)
            raise UserError('AI classification failed: %s' % str(e))

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
