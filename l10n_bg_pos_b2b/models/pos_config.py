# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

B2B_GROUP = "l10n_bg_pos_b2b.group_pos_b2b"


class PosConfig(models.Model):
    _inherit = "pos.config"

    l10n_bg_b2b_mode = fields.Selection(
        selection=[
            ("off", "Off"),
            ("button", "Wholesale button"),
            ("auto_on_company", "Automatic for business customers"),
        ],
        string="Wholesale Mode",
        default="button",
        required=True,
        help="Off: no wholesale block in this Point of Sale (business "
        "customers are still always invoiced).\n"
        "Wholesale button: the cashier switches between Retail and Wholesale.\n"
        "Automatic: selecting a business customer switches to Wholesale.",
    )
    l10n_bg_b2b_default_doc_mode = fields.Selection(
        selection=[
            ("odoo_invoice", "Odoo invoice + fiscal receipt"),
            ("fd_invoice", "Fiscal device invoice (locked)"),
        ],
        string="Wholesale Invoice Document",
        default="odoo_invoice",
        required=True,
        help="The invoice of a wholesale sale is always the Odoo invoice. "
        "Invoices issued by the fiscal device are not available yet.",
    )
    l10n_bg_b2b_credit_policy = fields.Selection(
        selection=[("warn", "Warn"), ("block", "Block")],
        string="Credit Limit Policy",
        default="warn",
        required=True,
        help="What happens when a sale on account exceeds the credit limit "
        "of the customer: the cashier confirms (Warn) or the sale is "
        "stopped (Block).",
    )
    l10n_bg_b2b_offline_order_cap = fields.Monetary(
        string="Offline Credit Cap",
        currency_field="currency_id",
        help="Maximum amount on account for one wholesale order while the "
        "Point of Sale is offline (0 = no cap).",
    )
    l10n_bg_b2b_guard_mode = fields.Selection(
        selection=[("warn", "Warn"), ("block", "Block")],
        string="Invoice Data Check",
        default="warn",
        required=True,
        help="What happens when the invoice details of a business customer "
        "are incomplete (name, address, company ID): the cashier confirms "
        "(Warn) or the sale is stopped (Block).",
    )
    l10n_bg_b2b_user_allowed = fields.Boolean(
        string="Wholesale Allowed for Current User",
        compute="_compute_l10n_bg_b2b_user_allowed",
        help="Technical: the current user may use the Wholesale button.",
    )

    @api.depends_context("uid")
    def _compute_l10n_bg_b2b_user_allowed(self):
        # Касата чете pos.config като текущия потребител — флагът казва на
        # фронтенда дали да покаже бутона. Гардът „фирма без фактура“ не
        # зависи от него (котвата §21).
        allowed = self.env.user.has_group(B2B_GROUP)
        for config in self:
            config.l10n_bg_b2b_user_allowed = allowed

    @api.constrains("l10n_bg_b2b_default_doc_mode")
    def _check_l10n_bg_b2b_doc_mode(self):
        # Режим Б (фактура от ФУ) е заключен до фаза 3: журнал по ФУ,
        # регистър на диапазоните, писмено становище (котвата §7.2,
        # ADR l10n-bulgaria-erpnet/0022).
        for config in self:
            if config.l10n_bg_b2b_default_doc_mode == "fd_invoice":
                raise ValidationError(_(
                    "Invoices issued by the fiscal device are not available "
                    "yet. Wholesale sales are invoiced in Odoo."
                ))

    @api.constrains("l10n_bg_b2b_mode", "invoice_journal_id")
    def _check_l10n_bg_b2b_invoice_journal(self):
        for config in self:
            if config.l10n_bg_b2b_mode != "off" and not config.invoice_journal_id:
                raise ValidationError(_(
                    "Wholesale mode needs an invoice journal on the Point of "
                    "Sale '%s'.", config.name,
                ))

    def _check_before_creating_new_session(self):
        # Без журнал за фактури ядрото вдига UserError при синхронизацията на
        # ВСЯКА поръчка (pos.order._process_saved_order) — платената поръчка
        # остава завинаги несинхронизирана. Затова касата с B2B режим не се
        # отваря без журнал (котвата §10.2).
        for config in self:
            if config.l10n_bg_b2b_mode != "off" and not config.invoice_journal_id:
                raise UserError(_(
                    "The Point of Sale '%s' cannot be opened: wholesale mode "
                    "needs an invoice journal.", config.name,
                ))
        return super()._check_before_creating_new_session()

    def get_limited_partners_loading(self, offset=0):
        # Офлайн касата трябва да има всички B2B купувачи на фирмата, не само
        # най-честите 100 (котвата §9). Добавят се само при първото
        # зареждане, за да не се повтарят при страницирането.
        res = super().get_limited_partners_loading(offset)
        if offset:
            return res
        loaded = {row[0] for row in res}
        b2b = self.env["res.partner"].search([
            ("l10n_bg_is_b2b_buyer", "=", True),
            ("parent_id", "=", False),
            ("company_id", "in", [False, self.company_id.id]),
        ])
        res = list(res)
        res.extend((pid,) for pid in b2b.ids if pid not in loaded)
        return res
