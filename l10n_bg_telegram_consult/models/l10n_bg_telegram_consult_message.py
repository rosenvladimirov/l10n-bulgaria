# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class L10nBgTelegramConsultMessage(models.Model):
    _name = "l10n.bg.telegram.consult.message"
    _description = "Telegram Consultation Message"
    _order = "id"

    request_id = fields.Many2one(
        "l10n.bg.telegram.consult.request",
        required=True,
        ondelete="cascade",
        index=True,
    )
    direction = fields.Selection(
        [("in", "From the group"), ("out", "Reply")], required=True, default="in"
    )
    state = fields.Selection(
        [
            ("received", "Received"),
            ("draft", "Waiting for Approval"),
            ("sent", "Sent"),
            ("rejected", "Rejected"),
        ],
        required=True,
        default="received",
    )
    tg_user_id = fields.Many2one("l10n.bg.telegram.user", string="Author")
    author = fields.Char()
    text = fields.Text()
    telegram_message_id = fields.Char(
        help="Id of the message in the group (reply target for answers)."
    )
    reply_to_id = fields.Many2one(
        "l10n.bg.telegram.consult.message", string="Answers", ondelete="set null"
    )
