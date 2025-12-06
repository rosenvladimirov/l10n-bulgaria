# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # TARIC classification
    taric_code_id = fields.Many2one('taric.code', string='TARIC Code',
                                    help='10-digit TARIC code for customs')

    # AI classification fields
    ai_classification_confidence = fields.Float('AI Confidence',
                                                related='taric_code_id.confidence_score',
                                                readonly=True)
    classification_verified = fields.Boolean('Classification Verified',
                                             related='taric_code_id.verified',
                                             readonly=True)

    # History
    classification_history_ids = fields.One2many('taric.classification.history',
                                                 'product_id',
                                                 string='Classification History')


    # Classification method
    classification_method = fields.Selection([
        ('manual', 'Manual'),
        ('ai', 'AI Suggested'),
        ('expert', 'Expert Verified'),
        ('api', 'API Verified'),
    ], string='Classification Method', readonly=True,
        help='How was the current TARIC code assigned')

    def action_classify_with_ai(self):
        """Open wizard to classify product using AI"""
        self.ensure_one()

        if not self.name and not self.description_sale:
            raise UserError('Product must have a name or description for AI classification!')

        # Get product description
        description = f"{self.name}"
        if self.description_sale:
            description += f" - {self.description_sale}"
        if self.categ_id:
            description += f" (Category: {self.categ_id.display_name})"

        # Call AI to get suggestions
        TaricCode = self.env['taric.code']
        suggestions = TaricCode.search_by_ai(
            product_description=description,
            product_category=self.categ_id.name if self.categ_id else None
        )

        if not suggestions:
            raise UserError('AI could not suggest any codes. Please try manual classification.')

        # Show suggestions in a wizard
        return {
            'name': 'AI Classification Suggestions',
            'type': 'ir.actions.act_window',
            'res_model': 'taric.classify.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_id': self.id,
                'ai_suggestions': suggestions,
            }
        }

    def action_verify_taric_code(self):
        """Verify the current TARIC code online"""
        self.ensure_one()

        if not self.taric_code_id:
            raise UserError('No TARIC code assigned to verify!')

        return self.taric_code_id.action_verify_code()

    def action_view_classification_history(self):
        """View classification history for this product"""
        self.ensure_one()

        return {
            'name': f'Classification History - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'taric.classification.history',
            'view_mode': 'list,form',
            'domain': [('product_id', '=', self.id)],
            'context': {'default_product_id': self.id}
        }

    @api.onchange('taric_code_id')
    def _onchange_taric_code(self):
        """Auto-set INTRASTAT code and HS code when TARIC code changes"""
        if self.taric_code_id:
            # Set HS code (base Odoo field)
            self.hs_code = self.taric_code_id.code

    def write(self, vals):
        """Log classification history when TARIC code changes"""
        result = super().write(vals)

        if 'taric_code_id' in vals and vals['taric_code_id']:
            # Determine classification method
            method = 'manual'
            if self.env.context.get('ai_classification'):
                method = 'ai'
            elif self.env.context.get('expert_verification'):
                method = 'expert'

            for product in self:
                # Save classification history
                self.env['taric.classification.history'].create({
                    'product_id': product.id,
                    'taric_code_id': vals['taric_code_id'],
                    'classification_method': method,
                    'user_id': self.env.user.id,
                })

                # Update product classification method
                product.classification_method = method

        return result
