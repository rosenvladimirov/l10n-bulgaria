# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

"""Дежурство по консултация: Claude слуша групата, пише чернови, човекът ги
одобрява (ADR telegram-consult-bot/0001, вариант А); времето се мери върху
предплатените часове и дежурството спира само, когато изтекат.
"""

import math

from odoo import api, fields, models
from odoo.exceptions import UserError

WARN_MINUTES = 15
STEP_HOURS = 0.25  # продуктът се отчита на стъпки от 15 минути


class L10nBgTelegramConsultRequest(models.Model):
    _inherit = "l10n.bg.telegram.consult.request"

    consult_message_ids = fields.One2many(
        "l10n.bg.telegram.consult.message", "request_id", string="Messages"
    )
    duty_state = fields.Selection(
        [("off", "Off"), ("on", "On Duty")], default="off", required=True, tracking=True
    )
    duty_started = fields.Datetime(readonly=True, copy=False)
    duty_warned = fields.Boolean(readonly=True, copy=False)

    # --- помощни -----------------------------------------------------------

    def _duty_elapsed_minutes(self):
        self.ensure_one()
        if self.duty_state != "on" or not self.duty_started:
            return 0.0
        return (fields.Datetime.now() - self.duty_started).total_seconds() / 60

    def _duty_remaining_minutes(self):
        """Оставащото време: остатъкът по реда минус тече­щото, още незаписано."""
        self.ensure_one()
        return (self.remaining_hours or 0.0) * 60 - self._duty_elapsed_minutes()

    def _group_say(self, text):
        """Съобщение от бота в групата на консултацията."""
        self.ensure_one()
        if not self.group_chat_id:
            return False
        client_lang = self.tg_user_id._get_lang()
        return self.bot_id.with_context(lang=client_lang).send_message(
            self.group_chat_id, text
        )

    def _duty_employee(self):
        employee = self.bot_id.consult_employee_id
        if not employee:
            raise UserError(
                self.env._(
                    "Set the consultant employee on bot %s to log the time.",
                    self.bot_id.name,
                )
            )
        return employee

    # --- RPC вход за дежурството (скриптът / Claude) -------------------------

    def l10n_bg_duty_start(self):
        """Застава на дежурство; връща данните, нужни на скрипта."""
        self.ensure_one()
        self._check_state("group")
        self._duty_employee()
        if self.remaining_hours <= 0:
            raise UserError(self.env._("%s has no prepaid hours left.", self.name))
        if self.duty_state != "on":
            self.write(
                {
                    "duty_state": "on",
                    "duty_started": fields.Datetime.now(),
                    "duty_warned": False,
                }
            )
        return self._duty_status()

    def _duty_status(self, after_id=0):
        self.ensure_one()
        inbound = self.consult_message_ids.filtered(
            lambda m: m.direction == "in" and m.id > after_id
        )
        return {
            "request": self.name,
            "request_id": self.id,
            "order": self.sale_line_id.order_id.name,
            "topic": self.topic,
            "duty_state": self.duty_state,
            "remaining_minutes": round(self._duty_remaining_minutes(), 1),
            "messages": [
                {
                    "id": m.id,
                    "author": m.author,
                    "text": m.text,
                    "date": fields.Datetime.to_string(m.create_date),
                }
                for m in inbound
            ],
        }

    def l10n_bg_duty_poll(self, after_id=0):
        """Новите съобщения от групата след `after_id` и оставащите минути."""
        self.ensure_one()
        return self._duty_status(int(after_id or 0))

    def l10n_bg_duty_draft(self, text, reply_to_id=False):
        """Черновата на Claude отива при отговорника за одобрение — не в групата."""
        self.ensure_one()
        if self.duty_state != "on":
            raise UserError(self.env._("%s is not on duty.", self.name))
        draft = self.env["l10n.bg.telegram.consult.message"].create(
            {
                "request_id": self.id,
                "direction": "out",
                "state": "draft",
                "author": "Claude",
                "text": text,
                "reply_to_id": reply_to_id or False,
            }
        )
        self.bot_id._send_draft_for_approval(draft)
        return draft.id

    def l10n_bg_duty_stop(self, reason="manual"):
        """Слиза от дежурство и записва времето в таймшита на задачата."""
        for request in self.filtered(lambda r: r.duty_state == "on"):
            minutes = request._duty_elapsed_minutes()
            # Нагоре до 15 минути, но не повече от оставащото по реда
            hours = max(STEP_HOURS, math.ceil(minutes / 60 / STEP_HOURS) * STEP_HOURS)
            hours = min(hours, max(request.remaining_hours, 0.0)) or hours
            start = request.duty_started
            request.env["account.analytic.line"].create(
                {
                    "name": request.env._(
                        "%(request)s: consultation on duty %(start)s – %(end)s UTC (%(reason)s)",  # noqa: E501
                        request=request.name,
                        start=fields.Datetime.to_string(start),
                        end=fields.Datetime.to_string(fields.Datetime.now()),
                        reason=reason,
                    ),
                    "task_id": request.task_id.id,
                    "project_id": request.task_id.project_id.id,
                    "employee_id": request._duty_employee().id,
                    "unit_amount": hours,
                    "date": fields.Date.context_today(request),
                }
            )
            request.write({"duty_state": "off", "duty_started": False})
        return True

    # --- следене на времето --------------------------------------------------

    @api.model
    def _cron_duty_watch(self):
        """Предупреждава 15 мин преди края и спира дежурството, когато изтече."""
        for request in self.search([("duty_state", "=", "on")]):
            left = request._duty_remaining_minutes()
            if left <= 0:
                request.l10n_bg_duty_stop(reason="prepaid hours used up")
                request._group_say(
                    request.env._(
                        "The prepaid hours for %s are used up. "
                        "Buy more with /buy in the bot to continue.",
                        request.name,
                    )
                )
                request.bot_id._notify_manager(
                    request.env._(
                        "%s: prepaid hours used up, duty stopped.", request.name
                    )
                )
            elif left <= WARN_MINUTES and not request.duty_warned:
                request.duty_warned = True
                request._group_say(
                    request.env._(
                        "About %(minutes)s minutes of prepaid time are left for %(request)s.",  # noqa: E501
                        minutes=max(int(left), 1),
                        request=request.name,
                    )
                )
