# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models
from odoo.exceptions import UserError


class L10nBgTelegramBot(models.Model):
    _inherit = "l10n.bg.telegram.bot"

    consult_manager_id = fields.Many2one(
        "l10n.bg.telegram.user",
        string="Consultation Manager",
        domain="[('bot_id', '=', id)]",
        help="Telegram user (who has sent /start to the bot) notified about new "
        "consultation requests; only this user can approve them from Telegram.",
    )

    consult_employee_id = fields.Many2one(
        "hr.employee",
        string="Consultant Employee",
        help="Employee whose timesheet receives the time logged by consultation duty.",
    )

    # --- дежурство: групата, черновите, известията ---------------------------

    def _process_group_message(self, tg_user, message):
        """Съобщенията в групата на консултация се пазят за дежурството."""
        chat_id = str(message["chat"]["id"])
        request = self.env["l10n.bg.telegram.consult.request"].search(
            [("bot_id", "=", self.id), ("group_chat_id", "=", chat_id)], limit=1
        )
        if not request:
            return super()._process_group_message(tg_user, message)
        text = (message.get("text") or message.get("caption") or "").strip()
        self.env["l10n.bg.telegram.consult.message"].create(
            {
                "request_id": request.id,
                "direction": "in",
                "state": "received",
                "tg_user_id": tg_user.id,
                "author": tg_user.display_label,
                "text": text or self.env._("(non-text message)"),
                "telegram_message_id": str(message.get("message_id") or ""),
            }
        )
        return True

    def _notify_manager(self, text, **kwargs):
        if not self.consult_manager_id:
            return False
        return self.consult_manager_id._in_own_language()._reply(text, **kwargs)

    def _send_draft_for_approval(self, draft):
        """Черновата при отговорника с бутони; в групата отива само след „Изпрати“."""
        manager = self.consult_manager_id
        if not manager:
            raise UserError(
                self.env._("Set the consultation manager on bot %s first.", self.name)
            )
        manager = manager._in_own_language()
        question = draft.reply_to_id.text if draft.reply_to_id else ""
        header = manager.env._("Draft reply for %s", draft.request_id.name)
        body = f"{header}\n\n{draft.text}"
        if question:
            body = f"{header}\n» {question}\n\n{draft.text}"
        return manager._reply(
            body,
            reply_markup={
                "inline_keyboard": [
                    [
                        {
                            "text": manager.env._("Send"),
                            "callback_data": f"cds:{draft.id}",
                        },
                        {
                            "text": manager.env._("Discard"),
                            "callback_data": f"cdx:{draft.id}",
                        },
                    ]
                ]
            },
        )

    def _manager_draft(self, tg_user, arg):
        if not self.consult_manager_id or tg_user != self.consult_manager_id:
            return self.env["l10n.bg.telegram.consult.message"]
        return self.env["l10n.bg.telegram.consult.message"].search(
            [
                ("id", "=", int(arg) if arg.isdigit() else 0),
                ("request_id.bot_id", "=", self.id),
                ("state", "=", "draft"),
            ]
        )

    def _callback_cds(self, tg_user, arg):
        draft = self._manager_draft(tg_user, arg)
        if not draft:
            return
        request = draft.request_id
        kwargs = {}
        if draft.reply_to_id.telegram_message_id:
            kwargs["reply_parameters"] = {
                "message_id": int(draft.reply_to_id.telegram_message_id),
                "allow_sending_without_reply": True,
            }
        self.send_message(request.group_chat_id, draft.text, **kwargs)
        draft.state = "sent"
        tg_user._reply(self.env._("Sent to %s.", request.name))

    def _callback_cdx(self, tg_user, arg):
        draft = self._manager_draft(tg_user, arg)
        if draft:
            draft.state = "rejected"
            tg_user._reply(self.env._("Draft discarded."))

    def _command_consult(self, tg_user, args):
        """/consult тема @човек1 @човек2 — заявка върху предплатените часове."""
        partner = tg_user.partner_id
        if not partner:
            return tg_user._reply(self.env._("Send /start first."))
        words = args.split()
        participants = " ".join(w for w in words if w.startswith("@") and len(w) > 1)
        topic = " ".join(w for w in words if not w.startswith("@")).strip()
        if not topic:
            return tg_user._reply(
                self.env._("Describe the topic: /consult topic @colleague1 @colleague2")
            )
        line = (
            self._prepaid_lines(tg_user)
            .filtered(lambda l: l.remaining_hours > 0)
            .sorted("id")[:1]
        )
        if not line:
            return tg_user._reply(
                self.env._("You have no prepaid hours left. Buy a package with /buy.")
            )
        request = self.env["l10n.bg.telegram.consult.request"].create(
            {
                "bot_id": self.id,
                "tg_user_id": tg_user.id,
                "topic": topic,
                "participants": participants,
                "sale_line_id": line.id,
            }
        )
        tg_user._reply(
            self.env._(
                "%(request)s is registered (%(hours)s prepaid hours left). "
                "You will be notified when it is approved.",
                request=request.name,
                hours=f"{line.remaining_hours:.2f}",
            )
        )
        self._notify_consult_manager(request)
        return request

    def _notify_consult_manager(self, request):
        if not self.consult_manager_id:
            return
        # Известието е на езика на отговорника, не на клиента, който е писал
        manager = self.consult_manager_id._in_own_language()
        manager._reply(
            manager.env._(
                "New consultation %(request)s from %(client)s:\n%(topic)s\n"
                "Participants: %(participants)s",
                request=request.name,
                client=request.partner_id.name,
                topic=request.topic,
                participants=request.participants or "-",
            ),
            reply_markup={
                "inline_keyboard": [
                    [
                        {
                            "text": manager.env._("Approve"),
                            "callback_data": f"cok:{request.id}",
                        },
                        {
                            "text": manager.env._("Reject"),
                            "callback_data": f"cno:{request.id}",
                        },
                    ]
                ]
            },
        )

    def _manager_request(self, tg_user, arg):
        """Заявката от бутона — само ако бутонът е натиснат от отговорника."""
        if not self.consult_manager_id or tg_user != self.consult_manager_id:
            return self.env["l10n.bg.telegram.consult.request"]
        return self.env["l10n.bg.telegram.consult.request"].search(
            [("id", "=", int(arg) if arg.isdigit() else 0), ("bot_id", "=", self.id)]
        )

    def _callback_cok(self, tg_user, arg):
        request = self._manager_request(tg_user, arg)
        if request.state == "new":
            request.action_approve()
            tg_user._reply(self.env._("%s approved.", request.name))

    def _callback_cno(self, tg_user, arg):
        request = self._manager_request(tg_user, arg)
        if request.state in ("new", "approved"):
            request.action_reject()
            tg_user._reply(self.env._("%s rejected.", request.name))
