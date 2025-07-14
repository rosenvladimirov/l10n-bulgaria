from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.addons.l10n_bg_config.models.chart_template import BASE_MODULE, PLUGINS_SUFFIX


class AccountPluginsWizard(models.TransientModel):
    _name = 'account.plugins.wizard'
    _description = 'Wizard for accounting plugins'

    plugin_line_ids = fields.One2many(
        'account.plugins.wizard.line',
        'wizard_id',
        string='Plugins'
    )
    force_update = fields.Boolean(
        string='Force Update',
        help='Force update of plugins even if they are already installed'
    )
    company_id =  fields.Many2one(
        'res.company',
        'Company',
        default=lambda self: self.env.company
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        plugins = self.env['ir.module.module'].search([
            ('name', 'like', f"{BASE_MODULE}{PLUGINS_SUFFIX}%")
        ])

        plugin_lines = []
        for plugin in plugins:
            plugin_lines.append((0, 0, {
                'plugin_id': plugin.id,
                'name': plugin.shortdesc or plugin.name,
                'state': plugin.state,
                'to_install': False,
                'to_uninstall': False
            }))

        res['plugin_line_ids'] = plugin_lines
        res['company_id'] = self.env.company.id
        return res

    def action_apply(self):
        """
        Processes the installation and uninstallation of plugins based on the user's selection.

        The method identifies plugins marked for installation, as well as plugins marked
        for uninstallation and processes them accordingly. It performs the installation
        or uninstallation actions immediately. If force updating is enabled, it reloads
        the template settings. The method ensures at least one plugin is selected for
        installation or uninstallation. If no plugins are selected, an exception is raised.
        It returns an action to reload the client interface upon successful execution.

        :raises UserError: If no plugins are selected for installation or uninstallation
                           or if an error occurs during processing.
        :return: A dictionary containing the action of type 'ir.actions.client' with
                 a 'reload' tag.
        :rtype: dict
        """
        self.ensure_one()
        to_install = self.plugin_line_ids.filtered(
            lambda l: l.to_install and l.plugin_id.state == 'uninstalled'
        ).mapped('plugin_id')

        to_uninstall = self.plugin_line_ids.filtered(
            lambda l: l.to_uninstall and l.plugin_id.state == 'installed'
        ).mapped('plugin_id')

        if to_install:
            for plugin in to_install:
                plugin.button_immediate_install()
        if to_uninstall:
            for plugins in to_uninstall:
                plugins.button_immediate_uninstall()

        if self.force_update:
            self.env['account.chart.template'].try_loading(self.company_id.chart_template, company=self.company_id)

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'views': [[self.env.ref('l10n_bg_config.view_account_plugins_wizard_form').id, 'form']],
            'res_id': self.id,
            'target': 'main',
        }

class AccountPluginsWizardLine(models.TransientModel):
    _name = 'account.plugins.wizard.line'
    _description = 'Plugins Wizard Line'

    wizard_id = fields.Many2one(
        'account.plugins.wizard',
        string='Wizard'
    )
    plugin_id = fields.Many2one(
        'ir.module.module',
        string='Plugin',
        readonly=True
    )
    name = fields.Text(
        string='Name',
        readonly=True
    )
    state = fields.Selection([
        ('uninstalled', 'Not installed'),
        ('installed', 'Installed'),
        ('to install', 'For installation'),
        ('to remove', 'To remove')
    ],
        string='State',
        readonly=True)
    to_install = fields.Boolean(
        string='Install',
        help='Mark for installation'
    )
    to_uninstall = fields.Boolean(
        string='Uninstall',
        help='Mark for uninstallation'
    )

    @api.onchange('to_install')
    def _onchange_to_install(self):
        if self.to_install:
            self.to_uninstall = False

    @api.onchange('to_uninstall')
    def _onchange_to_uninstall(self):
        if self.to_uninstall:
            self.to_install = False
