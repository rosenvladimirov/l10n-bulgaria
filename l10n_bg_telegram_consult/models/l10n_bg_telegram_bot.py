# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class L10nBgTelegramBot(models.Model):
    _inherit = "l10n.bg.telegram.bot"

    consult_manager_id = fields.Many2one(
        "l10n.bg.telegram.user",
        string="Consultation Manager",
        domain="[('bot_id', '=', id)]",
        help="Telegram user (who has sent /start to the bot) notified about new "
        "consultation requests; only this user can approve them from Telegram.",
    )

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
            self._prepaid_lines(partner)
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
