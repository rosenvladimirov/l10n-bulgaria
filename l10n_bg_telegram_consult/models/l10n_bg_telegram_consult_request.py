# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models
from odoo.exceptions import UserError


class L10nBgTelegramConsultRequest(models.Model):
    _name = "l10n.bg.telegram.consult.request"
    _description = "Telegram Consultation Request"
    _inherit = "mail.thread"
    _order = "id desc"

    name = fields.Char(readonly=True, copy=False, default="/")
    bot_id = fields.Many2one("l10n.bg.telegram.bot", required=True, ondelete="cascade")
    company_id = fields.Many2one(related="bot_id.company_id", store=True)
    tg_user_id = fields.Many2one(
        "l10n.bg.telegram.user", string="Requested by", required=True, readonly=True
    )
    partner_id = fields.Many2one(related="tg_user_id.partner_id", store=True)
    topic = fields.Text(required=True)
    participants = fields.Char(
        help="Telegram usernames to add to the group, separated by spaces."
    )
    state = fields.Selection(
        [
            ("new", "New"),
            ("approved", "Approved"),
            ("group", "Group Created"),
            ("done", "Done"),
            ("rejected", "Rejected"),
        ],
        default="new",
        required=True,
        tracking=True,
    )
    sale_line_id = fields.Many2one(
        "sale.order.line",
        string="Prepaid Hours",
        help="Order line whose prepaid hours are consumed by this consultation.",
    )
    task_id = fields.Many2one(related="sale_line_id.task_id", store=True)
    remaining_hours = fields.Float(related="sale_line_id.remaining_hours")
    group_chat_id = fields.Char(
        readonly=True, copy=False, help="Telegram group of the consultation."
    )
    group_invite_link = fields.Char(readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "l10n.bg.telegram.consult.request"
                )
        return super().create(vals_list)

    def _check_state(self, *allowed):
        for request in self:
            if request.state not in allowed:
                raise UserError(
                    self.env._(
                        "%(request)s is %(state)s; this step is not possible.",
                        request=request.name,
                        state=dict(
                            self._fields["state"]._description_selection(self.env)
                        )[request.state],
                    )
                )

    def action_approve(self):
        """Одобрението е на човека (ADR 0001); групата се прави след него (ADR 0002)."""
        self._check_state("new")
        self.state = "approved"
        for request in self:
            request.tg_user_id._reply(
                self.env._(
                    "%(request)s is approved. You will get an invitation to the "
                    "consultation group shortly.",
                    request=request.name,
                )
            )
        return True

    def action_reject(self):
        self._check_state("new", "approved")
        self.state = "rejected"
        for request in self:
            request.tg_user_id._reply(
                self.env._("%s was not accepted. Contact us for details.", request.name)
            )
        return True

    def action_done(self):
        self._check_state("group")
        self.state = "done"
        return True

    def l10n_bg_set_group(self, chat_id, invite_link=False):
        """Вика се по RPC от MCP инструмента `telegram_create_group` (ADR 0002).

        Акаунтът на Росен е създал групата и е добавил бота; тук записваме чата,
        а ботът праща линка за покана на клиента.
        """
        self.ensure_one()
        self._check_state("approved")
        self.write(
            {
                "group_chat_id": str(chat_id),
                "group_invite_link": invite_link or False,
                "state": "group",
            }
        )
        text = self.env._("The group for %s is ready.", self.name)
        kwargs = {}
        if invite_link:
            kwargs["reply_markup"] = {
                "inline_keyboard": [
                    [{"text": self.env._("Join the group"), "url": invite_link}]
                ]
            }
        self.tg_user_id._reply(text, **kwargs)
        return True

    def _consult_payload(self):
        """Данните, които MCP инструментът чете, за да направи групата."""
        self.ensure_one()
        return {
            "id": self.id,
            "name": self.name,
            "title": " — ".join(
                [self.name, self.partner_id.name or self.tg_user_id.display_label]
            ),
            "bot_username": self.bot_id.username,
            "members": [
                p.lstrip("@") for p in (self.participants or "").split() if p.strip("@")
            ]
            + ([self.tg_user_id.username] if self.tg_user_id.username else []),
        }

    def l10n_bg_consult_payload(self):
        """RPC вход за MCP: списък със заявките за група."""
        self._check_state("approved")
        return [request._consult_payload() for request in self]
