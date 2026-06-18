# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    discuss_proxy_centrifugo_url = fields.Char(
        string="Centrifugo API URL",
        config_parameter="discuss_proxy.centrifugo_url",
        help="Base API, e.g. https://centrifugo.mcpworks.net/api "
             "(publish = <base>/publish).")
    discuss_proxy_centrifugo_api_key = fields.Char(
        string="Centrifugo API Key",
        config_parameter="discuss_proxy.centrifugo_api_key")
    discuss_proxy_tenant_code = fields.Char(
        string="Stack / Tenant Code",
        config_parameter="discuss_proxy.tenant_code",
        help="Per-stack identity used in the channel name "
             "discuss:<tenant>:<login> so logins never collide across stacks. "
             "Leave empty to use the database name.")
