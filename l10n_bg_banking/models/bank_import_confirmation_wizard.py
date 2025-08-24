from odoo import fields, models, api


class BankImportConfirmationWizard(models.TransientModel):
    _name = 'bank.import.confirmation.wizard'
    _description = 'Bank Import Confirmation Wizard'

    config_id = fields.Many2one('res.config.settings', string='Configuration', required=True)
    period_display = fields.Char(string='Period', readonly=True)
    start_date = fields.Char(string='Start Date', readonly=True)
    end_date = fields.Char(string='End Date', readonly=True)
    
    def action_confirm_import(self):
        """Confirm and proceed with the import"""
        return self.config_id.with_context(skip_confirmation=True).action_import_infopay_statements()
    
    def action_cancel(self):
        """Cancel the import operation"""
        return {'type': 'ir.actions.act_window_close'}
