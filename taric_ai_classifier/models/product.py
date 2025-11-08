# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # TARIC & INTRASTAT classification
    taric_code_id = fields.Many2one('taric.code', string='TARIC Code',
                                    help='10-digit TARIC code for customs')
    cn8_code = fields.Char('CN8 Code', related='taric_code_id.cn8_code',
                          store=True, readonly=True)
    intrastat_code_id = fields.Many2one('intrastat.code',
                                       string='INTRASTAT Code',
                                       help='CN8 code for INTRASTAT reporting')
    
    # Additional customs information
    country_of_origin_id = fields.Many2one('res.country',
                                          string='Country of Origin')
    supplementary_unit = fields.Char('Supplementary Unit',
                                    related='taric_code_id.supplementary_unit',
                                    readonly=True)
    supplementary_quantity = fields.Float('Supplementary Quantity',
                                         help='Quantity in supplementary units')
    
    # AI classification
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
    
    # Statistics for INTRASTAT
    intrastat_transaction_code = fields.Selection([
        ('11', '11 - Outright purchase/sale'),
        ('12', '12 - Supply for sale on approval'),
        ('13', '13 - Barter trade'),
        ('14', '14 - Financial leasing'),
        ('19', '19 - Other'),
        ('21', '21 - Return of goods'),
        ('22', '22 - Replacement for returned goods'),
        ('23', '23 - Replacement for goods not returned'),
        ('29', '29 - Other returns'),
        ('31', '31 - Transfer from HQ to subsidiary'),
        ('32', '32 - Transfer from subsidiary to HQ'),
        ('33', '33 - Transfer between subsidiaries'),
        ('39', '39 - Other transfers'),
    ], string='Transaction Nature',
       help='Nature of transaction for INTRASTAT reporting')

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
        """Verify current TARIC code online"""
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
            'view_mode': 'tree,form',
            'domain': [('product_id', '=', self.id)],
            'context': {'default_product_id': self.id}
        }

    @api.onchange('taric_code_id')
    def _onchange_taric_code(self):
        """Auto-set INTRASTAT code when TARIC code changes"""
        if self.taric_code_id and self.taric_code_id.cn8_code:
            # Try to find matching INTRASTAT code
            intrastat = self.env['intrastat.code'].search([
                ('cn8_code', '=', self.taric_code_id.cn8_code)
            ], limit=1)
            
            if intrastat:
                self.intrastat_code_id = intrastat

    def write(self, vals):
        """Log classification history when TARIC code changes"""
        result = super().write(vals)
        
        if 'taric_code_id' in vals and vals['taric_code_id']:
            for product in self:
                self.env['taric.classification.history'].create({
                    'product_id': product.id,
                    'taric_code_id': vals['taric_code_id'],
                    'classification_method': 'manual',
                    'user_id': self.env.user.id,
                })
        
        return result


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def get_intrastat_data(self):
        """
        Get formatted INTRASTAT data for this product
        Used in INTRASTAT declaration generation
        """
        self.ensure_one()
        
        if not self.product_tmpl_id.intrastat_code_id:
            raise UserError(f'Product {self.name} has no INTRASTAT code assigned!')
        
        return {
            'product_id': self.id,
            'cn8_code': self.cn8_code,
            'description': self.name,
            'country_of_origin': self.country_of_origin_id.code if self.country_of_origin_id else False,
            'supplementary_unit': self.supplementary_unit,
            'supplementary_quantity': self.supplementary_quantity,
            'net_weight_kg': self.weight,
            'transaction_code': self.intrastat_transaction_code or '11',
        }
