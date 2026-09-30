# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

"""Дежурство по поръчка: „работиш за S00001“.

Групата в Telegram е консултантът и клиентът (без бот); Claude на консултанта
я слуша през неговия акаунт и пише отговори, които той одобрява. Тук Odoo
държи часовника върху предплатените часове на поръчката: старт, остатък,
запис в таймшийта и спиране, когато часовете свършат.
"""

import math

from odoo import api, fields, models
from odoo.exceptions import UserError

WARN_MINUTES = 15
STEP_HOURS = 0.25  # продуктът се отчита на стъпки от 15 минути


class SaleOrder(models.Model):
    _inherit = "sale.order"

    l10n_bg_telegram_group_chat_id = fields.Char(
        string="Telegram Group",
        copy=False,
        help="Telegram group of the consultant and the client for this order.",
    )
    l10n_bg_telegram_group_link = fields.Char(string="Group Invite Link", copy=False)
    l10n_bg_duty_state = fields.Selection(
        [("off", "Off"), ("on", "On Duty")],
        string="Consultation Duty",
        default="off",
        copy=False,
        tracking=True,
    )
    l10n_bg_duty_started = fields.Datetime(string="Duty Started", copy=False)
    l10n_bg_duty_warned = fields.Boolean(string="Duty Warned", copy=False)
    l10n_bg_duty_remaining_hours = fields.Float(
        string="Prepaid Hours Left", compute="_compute_l10n_bg_duty_remaining_hours"
    )

    # --- предплатените часове ------------------------------------------------

    def _l10n_bg_duty_lines(self):
        """Редовете с предплатени часове (по поръчка + таймшийт)."""
        self.ensure_one()
        return self.order_line.filtered(
            lambda line: (
                line.product_id.type == "service"
                and line.product_id.invoice_policy == "order"
                and line.product_id.service_type == "timesheet"
                and line.remaining_hours_available
            )
        )

    @api.depends("order_line.remaining_hours")
    def _compute_l10n_bg_duty_remaining_hours(self):
        for order in self:
            order.l10n_bg_duty_remaining_hours = sum(
                order._l10n_bg_duty_lines().mapped("remaining_hours")
            )

    def _l10n_bg_duty_line(self):
        """Редът, върху който тече времето: първият с остатък."""
        line = self._l10n_bg_duty_lines().filtered(lambda l: l.remaining_hours > 0)[:1]
        if not line.task_id:
            raise UserError(
                self.env._(
                    "%s has no task for the prepaid hours to log time on.", self.name
                )
            )
        return line

    def _l10n_bg_duty_elapsed_minutes(self):
        self.ensure_one()
        if self.l10n_bg_duty_state != "on" or not self.l10n_bg_duty_started:
            return 0.0
        return (fields.Datetime.now() - self.l10n_bg_duty_started).total_seconds() / 60

    def _l10n_bg_duty_remaining_minutes(self):
        self.ensure_one()
        return (
            self.l10n_bg_duty_remaining_hours * 60
            - self._l10n_bg_duty_elapsed_minutes()
        )

    def _l10n_bg_duty_employee(self):
        bot = self.env["l10n.bg.telegram.bot"].search(
            [
                ("consult_employee_id", "!=", False),
                ("company_id", "=", self.company_id.id),
            ],
            limit=1,
        )
        employee = bot.consult_employee_id or self.env.user.employee_id
        if not employee:
            raise UserError(
                self.env._(
                    "Set the consultant employee on the Telegram bot to log the time."
                )
            )
        return employee

    def _l10n_bg_client(self):
        """Клиентът в Telegram, в неговия език — ако е купил през бота."""
        tg_user = self.l10n_bg_telegram_user_id
        return tg_user._in_own_language() if tg_user else tg_user

    def _l10n_bg_manager(self):
        """Отговорникът за консултациите на бота на фирмата, в неговия език."""
        bot = self.env["l10n.bg.telegram.bot"].search(
            [
                ("consult_manager_id", "!=", False),
                ("company_id", "=", self.company_id.id),
            ],
            limit=1,
        )
        manager = bot.consult_manager_id
        return manager._in_own_language() if manager else manager

    # --- RPC вход (скриптът на дежурството / Claude) -------------------------

    def l10n_bg_duty_payload(self):
        """Заглавие и членове за групата (без бот) — за `telegram_create_group`."""
        self.ensure_one()
        tg_user = self.l10n_bg_telegram_user_id
        members = []
        if tg_user.username:
            members.append(f"@{tg_user.username}")
        elif self.partner_id.phone:
            members.append(self.partner_id.phone)
        return {
            "order": self.name,
            "title": f"{self.name} — {self.partner_id.name}",
            "members": members,
            "bot_username": "",
        }

    def l10n_bg_set_duty_group(self, chat_id, invite_link=False):
        """Връзва групата към поръчката; клиентът получава линка от бота."""
        self.ensure_one()
        self.write(
            {
                "l10n_bg_telegram_group_chat_id": str(chat_id),
                "l10n_bg_telegram_group_link": invite_link or False,
            }
        )
        if invite_link and self.l10n_bg_telegram_user_id:
            client = self.l10n_bg_telegram_user_id._in_own_language()
            client._reply(
                client.env._("The consultation group for %s is ready.", self.name),
                reply_markup={
                    "inline_keyboard": [
                        [{"text": client.env._("Join the group"), "url": invite_link}]
                    ]
                },
            )
        return True

    def l10n_bg_duty_start(self):
        """Застава на дежурство: часовникът тръгва върху предплатените часове."""
        self.ensure_one()
        if self.state != "sale":
            raise UserError(self.env._("%s is not a confirmed order.", self.name))
        if not self.l10n_bg_telegram_group_chat_id:
            raise UserError(self.env._("%s has no Telegram group yet.", self.name))
        self._l10n_bg_duty_line()
        self._l10n_bg_duty_employee()
        if self.l10n_bg_duty_remaining_hours <= 0:
            raise UserError(self.env._("%s has no prepaid hours left.", self.name))
        if self.l10n_bg_duty_state != "on":
            self.write(
                {
                    "l10n_bg_duty_state": "on",
                    "l10n_bg_duty_started": fields.Datetime.now(),
                    "l10n_bg_duty_warned": False,
                }
            )
        return self.l10n_bg_duty_status()

    def l10n_bg_duty_status(self):
        self.ensure_one()
        return {
            "order": self.name,
            "order_id": self.id,
            "partner": self.partner_id.name,
            "chat_id": self.l10n_bg_telegram_group_chat_id,
            "duty_state": self.l10n_bg_duty_state,
            "remaining_minutes": round(self._l10n_bg_duty_remaining_minutes(), 1),
        }

    def l10n_bg_duty_stop(self, reason="manual"):
        """Слиза от дежурство и записва времето в таймшийта на задачата."""
        for order in self.filtered(lambda o: o.l10n_bg_duty_state == "on"):
            line = order._l10n_bg_duty_line()
            minutes = order._l10n_bg_duty_elapsed_minutes()
            # Нагоре до 15 минути, но не повече от оставащото по поръчката
            hours = max(STEP_HOURS, math.ceil(minutes / 60 / STEP_HOURS) * STEP_HOURS)
            if order.l10n_bg_duty_remaining_hours > 0:
                hours = min(hours, order.l10n_bg_duty_remaining_hours)
            order.env["account.analytic.line"].create(
                {
                    "name": order.env._(
                        "%(order)s: consultation on duty %(start)s – %(end)s UTC (%(reason)s)",  # noqa: E501
                        order=order.name,
                        start=fields.Datetime.to_string(order.l10n_bg_duty_started),
                        end=fields.Datetime.to_string(fields.Datetime.now()),
                        reason=reason,
                    ),
                    "task_id": line.task_id.id,
                    "project_id": line.task_id.project_id.id,
                    "employee_id": order._l10n_bg_duty_employee().id,
                    "unit_amount": hours,
                    "date": fields.Date.context_today(order),
                }
            )
            order.write({"l10n_bg_duty_state": "off", "l10n_bg_duty_started": False})
        return True

    @api.model
    def _cron_l10n_bg_duty_watch(self):
        """15 мин преди края — известие; при изчерпване — спиране и запис."""
        for order in self.search([("l10n_bg_duty_state", "=", "on")]):
            left = order._l10n_bg_duty_remaining_minutes()
            if left <= 0:
                order.l10n_bg_duty_stop(reason="prepaid hours used up")
                if client := order._l10n_bg_client():
                    client._reply(
                        client.env._(
                            "The prepaid hours for %s are used up. "
                            "Buy more with /buy to continue.",
                            order.name,
                        )
                    )
                if manager := order._l10n_bg_manager():
                    manager._reply(
                        manager.env._(
                            "%s: prepaid hours used up, duty stopped.", order.name
                        )
                    )
            elif left <= WARN_MINUTES and not order.l10n_bg_duty_warned:
                order.l10n_bg_duty_warned = True
                if client := order._l10n_bg_client():
                    client._reply(
                        client.env._(
                            "About %(minutes)s minutes of prepaid consultation time "
                            "are left for %(order)s.",
                            minutes=max(int(left), 1),
                            order=order.name,
                        )
                    )
