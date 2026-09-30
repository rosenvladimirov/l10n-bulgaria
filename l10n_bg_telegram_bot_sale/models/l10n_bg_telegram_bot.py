# Copyright 2026 Rosen Vladimirov <vladimirov.rosen@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models

ORDERS_SHOWN = 5


class L10nBgTelegramBot(models.Model):
    _inherit = "l10n.bg.telegram.bot"

    website_id = fields.Many2one(
        "website",
        help="Shop where orders from the bot are created and paid.",
    )
    package_ids = fields.One2many(
        "l10n.bg.telegram.package", "bot_id", string="Packages", copy=True
    )

    # --- помощни -----------------------------------------------------------

    def _format_amount(self, amount, currency):
        return f"{amount:.2f} {currency.symbol or currency.name}"

    def _pay_keyboard(self, order):
        return {
            "inline_keyboard": [
                [
                    {
                        "text": self.env._("Pay %s", order.name),
                        "url": order._l10n_bg_telegram_pay_url(),
                    }
                ]
            ]
        }

    def _last_draft_order(self, tg_user):
        return self.env["sale.order"].search(
            [
                ("l10n_bg_telegram_user_id", "=", tg_user.id),
                ("state", "=", "draft"),
            ],
            order="id desc",
            limit=1,
        )

    # --- /buy --------------------------------------------------------------

    def _command_buy(self, tg_user, args):
        if not self.package_ids or not self.website_id:
            return tg_user._reply(self.env._("Nothing is on sale yet."))
        keyboard = [
            [{"text": package.name, "callback_data": f"buy:{package.id}"}]
            for package in self.package_ids
        ]
        return tg_user._reply(
            self.env._("Choose a package:"),
            reply_markup={"inline_keyboard": keyboard},
        )

    def _callback_buy(self, tg_user, arg):
        package = self.package_ids.filtered(lambda p: str(p.id) == arg)
        if not package:
            return tg_user._reply(self.env._("This package is no longer available."))
        partner = tg_user._ensure_partner()
        website = self.website_id
        # Webhook-ът върви като публичния потребител ⇒ продавачът идва от сайта,
        # иначе „Public user“ става отговорник на поръчката
        order = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "company_id": website.company_id.id,
                "website_id": website.id,
                "user_id": website.salesperson_id.id,
                "team_id": website.salesteam_id.id,
                "l10n_bg_telegram_user_id": tg_user.id,
                "order_line": [
                    fields.Command.create(
                        {
                            "product_id": package.product_id.id,
                            "product_uom_qty": package.quantity,
                        }
                    )
                ],
            }
        )
        return tg_user._reply(
            self.env._(
                "Order %(order)s: %(package)s, total %(total)s.\n"
                "Pay in the shop; you can add a voucher with /voucher CODE first.",
                order=order.name,
                package=package.name,
                total=self._format_amount(order.amount_total, order.currency_id),
            ),
            reply_markup=self._pay_keyboard(order),
        )

    # --- /voucher ------------------------------------------------------------

    def _command_voucher(self, tg_user, args):
        code = args.strip()
        if not code:
            return tg_user._reply(self.env._("Send the code like this: /voucher CODE"))
        order = self._last_draft_order(tg_user)
        if not order:
            return tg_user._reply(
                self.env._("There is no unpaid order to apply it to. Use /buy first.")
            )
        status = order._try_apply_code(code)
        if "error" in status:
            return tg_user._reply(status["error"])
        # Същото като в магазина (website_sale_loyalty): една награда се прилага
        # веднага; избор между няколко остава за количката
        applied = False
        if len(status) == 1:
            coupon, rewards = next(iter(status.items()))
            if len(rewards) == 1 and not rewards.multi_product:
                result = order._apply_program_reward(rewards, coupon)
                if "error" in result:
                    return tg_user._reply(result["error"])
                applied = True
        order._update_programs_and_rewards()
        if not applied:
            return tg_user._reply(
                self.env._("The code is accepted; choose the reward in the shop."),
                reply_markup=self._pay_keyboard(order),
            )
        return tg_user._reply(
            self.env._(
                "Voucher applied to %(order)s. New total: %(total)s.",
                order=order.name,
                total=self._format_amount(order.amount_total, order.currency_id),
            ),
            reply_markup=self._pay_keyboard(order),
        )

    # --- /balance ------------------------------------------------------------

    def _customer_orders(self, tg_user):
        """Поръчките на клиента: вързаните с неговия Telegram потребител и тези
        на контакта му.

        Магазинът сменя партньора на количката, когато клиентът влезе като
        потребител (website_sale, `_get_and_cache_current_cart`) ⇒ платената
        поръчка може да е на друг контакт, но връзката с Telegram остава.
        """
        domain = [("l10n_bg_telegram_user_id", "=", tg_user.id)]
        if tg_user.partner_id:
            commercial = tg_user.partner_id.commercial_partner_id
            domain = ["|", *domain, ("partner_id", "child_of", commercial.id)]
        return self.env["sale.order"].search(domain, order="id desc")

    def _prepaid_lines(self, tg_user):
        # ordered_prepaid = фактуриране по поръчка + отчитане с таймшийт
        return self.env["sale.order.line"].search(
            [
                ("order_id", "in", self._customer_orders(tg_user).ids),
                ("state", "=", "sale"),
                ("product_id.type", "=", "service"),
                ("product_id.invoice_policy", "=", "order"),
                ("product_id.service_type", "=", "timesheet"),
            ]
        )

    def _command_balance(self, tg_user, args):
        partner = tg_user.partner_id
        if not partner:
            return tg_user._reply(self.env._("Send /start first."))
        orders = self._customer_orders(tg_user)
        lines = self._prepaid_lines(tg_user)
        bought = sum(lines.mapped("product_uom_qty"))
        used = sum(lines.mapped("qty_delivered"))
        text = [
            self.env._(
                "Prepaid hours: %(left)s left (bought %(bought)s, used %(used)s).",
                left=f"{bought - used:.2f}",
                bought=f"{bought:.2f}",
                used=f"{used:.2f}",
            )
        ]
        wallets = self.env["loyalty.card"].search(
            [
                ("partner_id", "in", (partner | orders.partner_id).ids),
                ("program_id.program_type", "=", "ewallet"),
            ]
        )
        for wallet in wallets:
            text.append(
                self.env._(
                    "%(wallet)s: %(amount)s",
                    wallet=wallet.program_id.name,
                    amount=self._format_amount(wallet.points, wallet.currency_id),
                )
            )
        return tg_user._reply("\n".join(text))

    # --- /orders -------------------------------------------------------------

    def _command_orders(self, tg_user, args):
        orders = self._customer_orders(tg_user)[:ORDERS_SHOWN]
        if not orders:
            return tg_user._reply(self.env._("You have no orders yet."))
        states = dict(orders._fields["state"]._description_selection(self.env))
        lines = [
            " — ".join(
                [
                    order.name,
                    self._format_amount(order.amount_total, order.currency_id),
                    states.get(order.state, order.state),
                ]
            )
            for order in orders
        ]
        unpaid = orders.filtered(lambda o: o.state == "draft")
        keyboard = [
            [
                {
                    "text": self.env._("Pay %s", order.name),
                    "url": order._l10n_bg_telegram_pay_url(),
                }
            ]
            for order in unpaid
        ]
        return tg_user._reply(
            "\n".join(lines),
            **({"reply_markup": {"inline_keyboard": keyboard}} if keyboard else {}),
        )
