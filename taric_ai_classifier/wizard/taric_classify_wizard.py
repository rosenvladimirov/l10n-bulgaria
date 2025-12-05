# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class TaricClassifyWizard(models.TransientModel):
    _name = 'taric.classify.wizard'
    _description = 'TARIC Classification Wizard'

    product_id = fields.Many2one('product.template', string='Product',
                                 required=True)
    suggestion_ids = fields.One2many('taric.classify.suggestion',
                                     'wizard_id',
                                     string='AI Suggestions')

    selected_suggestion_id = fields.Many2one('taric.classify.suggestion',
                                            string='Selected Code')

    custom_code = fields.Char('Custom TARIC Code', size=10,
                             help='Enter code manually if not in suggestions')

    notes = fields.Char('Classification Notes')

    @api.model
    def default_get(self, fields_list):
        """Load AI suggestions from context"""
        res = super().default_get(fields_list)

        ai_suggestions = self.env.context.get('ai_suggestions', [])

        if ai_suggestions:
            suggestions = []
            for idx, suggestion in enumerate(ai_suggestions):
                suggestions.append((0, 0, {
                    'code': suggestion.get('code'),
                    'description_en': suggestion.get('description_en'),
                    'description_bg': suggestion.get('description_bg'),
                    'confidence': suggestion.get('confidence', 0),
                    'supplementary_unit': suggestion.get('supplementary_unit'),
                    'reasoning': suggestion.get('reasoning'),
                    'sequence': idx + 1,
                }))

            res['suggestion_ids'] = suggestions

        return res

    def action_apply_classification(self):
        """Apply selected classification to product"""
        self.ensure_one()

        # Determine which code to use
        if self.selected_suggestion_id:
            code = self.selected_suggestion_id.code
            confidence = self.selected_suggestion_id.confidence
            description_bg = self.selected_suggestion_id.description_bg
            description_en = self.selected_suggestion_id.description_en
            reasoning = self.selected_suggestion_id.reasoning
            classification_method = 'ai'
        elif self.custom_code:
            code = self.custom_code
            confidence = 0
            description_bg = None
            description_en = None
            reasoning = self.notes or 'Manual classification'
            classification_method = 'manual'
        else:
            raise UserError('Please select a suggestion or enter a custom code!')

        # Find or create TARIC code
        TaricCode = self.env['taric.code']
        taric_record = TaricCode.search([('code', '=', code)], limit=1)

        if not taric_record:
            # Create a new TARIC code record
            vals = {
                'code': code,
                'cn8_code': code[:8] if len(code) >= 8 else code,
                'confidence_score': confidence,
            }

            if description_en:
                vals['description_en'] = description_en
            if description_bg:
                vals['description_bg'] = description_bg

            taric_record = TaricCode.create(vals)

        # Apply to product
        self.product_id.write({
            'taric_code_id': taric_record.id,
        })

        # Create classification history
        self.env['taric.classification.history'].create({
            'product_id': self.product_id.id,
            'taric_code_id': taric_record.id,
            'classification_method': classification_method,
            'confidence_score': confidence,
            'reasoning': reasoning,
            'ai_model': 'claude-sonnet-4-20250514',
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'Product classified with code {code}',
                'type': 'success',
                'sticky': False,
            }
        }


class TaricClassifySuggestion(models.TransientModel):
    _name = 'taric.classify.suggestion'
    _description = 'TARIC Classification Suggestion'
    _order = 'confidence desc, sequence'

    wizard_id = fields.Many2one('taric.classify.wizard', required=True,
                                ondelete='cascade')

    sequence = fields.Integer('Sequence', default=10)
    code = fields.Char('Code', required=True)
    description_en = fields.Text('Description (EN)')
    description_bg = fields.Text('Описание (BG)')
    confidence = fields.Float('Confidence %', digits=(5, 2))
    supplementary_unit = fields.Char('Unit')
    reasoning = fields.Text('AI Reasoning')


class BatchClassifyWizard(models.TransientModel):
    _name = 'batch.classify.wizard'
    _description = 'Batch Product Classification'

    product_ids = fields.Many2many('product.template', string='Products')

    filter_unclassified = fields.Boolean('Only Unclassified',
                                        default=True,
                                        help='Process only products without TARIC codes')

    category_id = fields.Many2one('product.category', string='Category Filter',
                                 help='Process only products in this category')

    auto_apply_high_confidence = fields.Boolean('Auto-apply High Confidence',
                                               default=False,
                                               help='Automatically apply suggestions with >90% confidence')

    progress = fields.Float('Progress %', readonly=True)
    status = fields.Text('Status', readonly=True)

    result_ids = fields.One2many('batch.classify.result', 'wizard_id',
                                 string='Results', readonly=True)

    @api.model
    def default_get(self, fields_list):
        """Load selected products from context"""
        res = super().default_get(fields_list)

        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            res['product_ids'] = [(6, 0, active_ids)]

        return res

    def action_classify_batch(self):
        """Run batch classification"""
        self.ensure_one()

        # Get products to process
        domain = []
        if self.filter_unclassified:
            domain.append(('taric_code_id', '=', False))
        if self.category_id:
            domain.append(('categ_id', 'child_of', self.category_id.id))

        if self.product_ids:
            domain.append(('id', 'in', self.product_ids.ids))

        products = self.env['product.template'].search(domain)

        if not products:
            raise UserError('No products found to classify!')

        total = len(products)
        processed = 0
        results = []

        TaricCode = self.env['taric.code']

        for product in products:
            try:
                # Get product description
                description = f"{product.name}"
                if product.description_sale:
                    description += f" - {product.description_sale}"

                # AI classification
                suggestions = TaricCode.search_by_ai(
                    product_description=description,
                    product_category=product.categ_id.name if product.categ_id else None
                )

                if suggestions:
                    best_suggestion = suggestions[0]

                    # Auto-apply if confidence is high
                    if self.auto_apply_high_confidence and best_suggestion.get('confidence', 0) > 90:
                        code = best_suggestion['code']

                        # Find or create TARIC code
                        taric_record = TaricCode.search([('code', '=', code)], limit=1)
                        if not taric_record:
                            taric_record = TaricCode.create({
                                'code': code,
                                'cn8_code': code[:8],
                                'description_en': best_suggestion.get('description_en'),
                                'description_bg': best_suggestion.get('description_bg'),
                                'confidence_score': best_suggestion.get('confidence'),
                            })

                        product.taric_code_id = taric_record

                        results.append((0, 0, {
                            'product_id': product.id,
                            'status': 'success',
                            'taric_code': code,
                            'confidence': best_suggestion.get('confidence'),
                            'message': 'Auto-applied',
                        }))
                    else:
                        results.append((0, 0, {
                            'product_id': product.id,
                            'status': 'pending',
                            'taric_code': best_suggestion['code'],
                            'confidence': best_suggestion.get('confidence'),
                            'message': 'Manual review needed',
                        }))
                else:
                    results.append((0, 0, {
                        'product_id': product.id,
                        'status': 'error',
                        'message': 'No suggestions from AI',
                    }))

                processed += 1
                self.write({
                    'progress': (processed / total) * 100,
                    'status': f'Processed {processed}/{total} products',
                })
                self.env.cr.commit()  # Commit after each product

            except Exception as e:
                _logger.error(f'Error classifying product {product.name}: {str(e)}')
                results.append((0, 0, {
                    'product_id': product.id,
                    'status': 'error',
                    'message': str(e),
                }))

        # Save results
        self.write({
            'result_ids': results,
            'status': f'Completed: {processed}/{total} products processed',
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'batch.classify.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class BatchClassifyResult(models.TransientModel):
    _name = 'batch.classify.result'
    _description = 'Batch Classification Result'
    _order = 'confidence desc'

    wizard_id = fields.Many2one('batch.classify.wizard', required=True,
                                ondelete='cascade')
    product_id = fields.Many2one('product.template', string='Product')
    status = fields.Selection([
        ('success', 'Success'),
        ('pending', 'Pending Review'),
        ('error', 'Error'),
    ], string='Status')
    taric_code = fields.Char('Suggested Code')
    confidence = fields.Float('Confidence %')
    message = fields.Text('Message')
