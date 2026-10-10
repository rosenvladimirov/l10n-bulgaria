# Copyright 2026 Rosen Vladimirov, Terraros Commerce Ltd.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import api, fields, models

# Видове идентификатор от l10n_bg_config, които значат „юридическо лице или
# ЕТ“ (ЕИК / БУЛСТАТ). ЕТ има ЕИК, затова е тук.
B2B_UIC_TYPES = ("bg_uic",)
# Видове идентификатор на физическо лице: ДДС полето може да носи ЕГН/ЛНЧ,
# без лицето да е фирма — то НЕ е B2B купувач (котвата §8.1, В10 е отворен
# за свободните професии и ЕТ като лице).
PERSONAL_UIC_TYPES = ("bg_egn", "bg_pnf")

# Кодове на липсите по ЗДДС чл. 114 — фронтендът ги превежда в съобщения.
MISSING_NAME = "name"
MISSING_ADDRESS = "address"
MISSING_UIC = "uic"


class ResPartner(models.Model):
    # TODO(котвата §8.1): признакът и проверките са нужни и на е-магазина и
    # на моста към Shopify (gaps P0-4) — мястото им е в l10n_bg_config.
    # Временно са тук; преместването иска ADR и миграция на колоната.
    _inherit = "res.partner"

    l10n_bg_force_invoice = fields.Boolean(
        string="Always Invoice",
        help="Treat this customer as a business buyer: every sale in the "
        "Point of Sale is invoiced, even if the customer is not a company "
        "and has no VAT number.",
    )
    l10n_bg_is_b2b_buyer = fields.Boolean(
        string="Business Buyer (B2B)",
        compute="_compute_l10n_bg_is_b2b_buyer",
        store=True,
        index=True,
        help="Business buyers (companies, sole traders, legal entities) must "
        "always receive an invoice (VAT Act, Art. 113, para. 1).",
    )
    l10n_bg_invoice_missing = fields.Char(
        string="Missing Invoice Data",
        compute="_compute_l10n_bg_invoice_missing",
        help="Technical: comma-separated codes of the invoice details "
        "required by Art. 114 of the VAT Act that are missing.",
    )
    l10n_bg_b2b_route = fields.Selection(
        selection=[
            ("pos", "Point of Sale"),
            ("backoffice", "Back office"),
        ],
        string="Invoicing Channel",
        compute="_compute_l10n_bg_b2b_route",
        help="Foreign customers (intra-EU supplies, exports) are invoiced "
        "from the back office, not from the Point of Sale.",
    )
    # Кредитът за касата. Касиерът няма счетоводна група и не може да чете
    # `credit_limit` / `credit` на account — затова отделни полета, смятани
    # със sudo() само за записите, които касата така или иначе зарежда.
    l10n_bg_pos_credit_limit = fields.Float(
        string="POS Credit Limit",
        compute="_compute_l10n_bg_pos_credit",
        help="Credit limit of the commercial partner (0 = no limit).",
    )
    l10n_bg_pos_total_due = fields.Float(
        string="POS Total Due",
        compute="_compute_l10n_bg_pos_credit",
        help="Open receivable of the commercial partner in the company.",
    )
    l10n_bg_pos_overdue = fields.Float(
        string="POS Overdue",
        compute="_compute_l10n_bg_pos_credit",
        help="Part of the open receivable that is past its due date.",
    )
    l10n_bg_pos_orders_amount_due = fields.Float(
        string="POS Orders on Account",
        compute="_compute_l10n_bg_pos_credit",
        help="Customer account payments of orders in open sessions that are "
        "not invoiced yet.",
    )
    l10n_bg_pos_represent_name = fields.Char(
        string="Representative Name",
        compute="_compute_l10n_bg_pos_display",
    )
    l10n_bg_pos_payment_term = fields.Char(
        string="Payment Terms Name",
        compute="_compute_l10n_bg_pos_display",
    )

    # ------------------------------------------------------------------
    # Признак и проверки
    # ------------------------------------------------------------------

    @api.depends(
        "commercial_partner_id.is_company",
        "commercial_partner_id.vat",
        "commercial_partner_id.l10n_bg_uic_type",
        "commercial_partner_id.l10n_bg_force_invoice",
    )
    def _compute_l10n_bg_is_b2b_buyer(self):
        for partner in self:
            partner.l10n_bg_is_b2b_buyer = partner._l10n_bg_b2b_buyer_flag()

    def _l10n_bg_b2b_buyer_flag(self):
        """Признакът се взима от търговския партньор: лицето за контакт на
        фирма купува от името на фирмата."""
        self.ensure_one()
        commercial = self.commercial_partner_id or self
        if commercial.l10n_bg_force_invoice or commercial.is_company:
            return True
        if commercial.l10n_bg_uic_type in B2B_UIC_TYPES:
            return True
        return bool(
            commercial.vat
            and commercial.l10n_bg_uic_type not in PERSONAL_UIC_TYPES
        )

    def _l10n_bg_check_invoice_data(self):
        """Липсите по ЗДДС чл. 114, ал. 1 за фактура към този купувач.

        :return: списък от кодове (MISSING_*) — празен, когато всичко е налице
        """
        self.ensure_one()
        commercial = self.commercial_partner_id or self
        address = self.browse(self.address_get(["invoice"])["invoice"])
        missing = []
        if not (commercial.name or "").strip():
            missing.append(MISSING_NAME)
        if not (address.street and address.city and address.country_id):
            missing.append(MISSING_ADDRESS)
        if not (commercial.l10n_bg_uic or commercial.vat):
            missing.append(MISSING_UIC)
        return missing

    @api.depends(
        "name", "street", "city", "country_id", "vat", "l10n_bg_uic",
        "commercial_partner_id", "child_ids",
    )
    def _compute_l10n_bg_invoice_missing(self):
        for partner in self:
            partner.l10n_bg_invoice_missing = ",".join(
                partner._l10n_bg_check_invoice_data()
            )

    def _l10n_bg_b2b_document_route(self, company=None):
        """Откъде се фактурира този купувач: от касата или от бекенда.

        Бекенд: държава, различна от тази на фирмата (ВОД, износ, чужд
        купувач), или фискална позиция, вързана за друга държава/група
        държави (котвата §10.3, ЗДДС чл. 113, ал. 5 и чл. 117).
        """
        self.ensure_one()
        company = company or self.env.company
        commercial = self.commercial_partner_id or self
        home = company.account_fiscal_country_id or company.country_id
        if commercial.country_id and home and commercial.country_id != home:
            return "backoffice"
        # Автоматичната позиция се търси само при попълнена държава: без
        # държава би паднала на общата позиция „извън ЕС“ — липсата на
        # държава вече е хваната от проверката на данните за фактурата.
        position = commercial.with_company(company).property_account_position_id
        if not position and commercial.country_id:
            position = self.env["account.fiscal.position"].with_company(
                company
            )._get_fiscal_position(commercial)
        if position and home and self._l10n_bg_is_foreign_position(position, home):
            return "backoffice"
        return "pos"

    @api.model
    def _l10n_bg_is_foreign_position(self, position, home):
        """Позиция за ЕС/износ: вързана за друга държава или за група, в
        която домашната държава не влиза."""
        if position.country_id:
            return position.country_id != home
        if position.country_group_id:
            return home not in position.country_group_id.country_ids
        return False

    @api.depends_context("company")
    @api.depends("country_id", "property_account_position_id")
    def _compute_l10n_bg_b2b_route(self):
        for partner in self:
            partner.l10n_bg_b2b_route = partner._l10n_bg_b2b_document_route()

    # ------------------------------------------------------------------
    # Кредит за касата
    # ------------------------------------------------------------------

    @api.depends_context("company")
    def _compute_l10n_bg_pos_credit(self):
        values = self._l10n_bg_pos_credit_values(self.env.company)
        for partner in self:
            vals = values.get(partner.commercial_partner_id.id or partner.id, {})
            partner.l10n_bg_pos_credit_limit = vals.get("limit", 0.0)
            partner.l10n_bg_pos_total_due = vals.get("total_due", 0.0)
            partner.l10n_bg_pos_overdue = vals.get("overdue", 0.0)
            partner.l10n_bg_pos_orders_amount_due = vals.get("orders_due", 0.0)

    def _l10n_bg_pos_credit_values(self, company):
        """Кредитът по търговски партньор, във валутата на фирмата.

        Използван кредит = отворено вземане (счетоводно) + плащанията
        „на сметка“ в отворени сесии по още нефактурирани поръчки
        (котвата §15.2). Фактурираната поръчка вече е във вземането —
        не се брои втори път. sudo() е ограничен до партньорите в self и
        до фирмата: касиерът няма счетоводна група.
        """
        commercial = (self.commercial_partner_id | self.filtered(
            lambda p: not p.commercial_partner_id)).sudo()
        if not commercial:
            return {}
        result = {pid: {"limit": 0.0, "total_due": 0.0, "overdue": 0.0, "orders_due": 0.0}
                  for pid in commercial.ids}
        if company.sudo().account_use_credit_limit:
            for partner in commercial.with_company(company):
                result[partner.id]["limit"] = partner.credit_limit or 0.0
        base_domain = [
            ("company_id", "=", company.id),
            ("parent_state", "=", "posted"),
            ("account_id.account_type", "=", "asset_receivable"),
            ("reconciled", "=", False),
            ("partner_id", "in", commercial.ids),
        ]
        Line = self.env["account.move.line"].sudo()
        for partner, residual in Line._read_group(
            base_domain, groupby=["partner_id"], aggregates=["amount_residual:sum"]
        ):
            result[partner.id]["total_due"] = residual or 0.0
        today = fields.Date.context_today(self)
        for partner, residual in Line._read_group(
            base_domain + [("date_maturity", "<", today)],
            groupby=["partner_id"], aggregates=["amount_residual:sum"],
        ):
            result[partner.id]["overdue"] = residual or 0.0
        # `type` на метода не е stored — филтрира се след търсенето
        payments = self.env["pos.payment"].sudo().search([
            ("pos_order_id.state", "=", "paid"),
            ("pos_order_id.account_move", "=", False),
            ("pos_order_id.session_id.state", "!=", "closed"),
            ("pos_order_id.company_id", "=", company.id),
            ("pos_order_id.partner_id", "child_of", commercial.ids),
        ]).filtered(lambda p: p.payment_method_id.type == "pay_later")
        for payment in payments:
            pid = payment.pos_order_id.partner_id.commercial_partner_id.id
            if pid in result:
                amount = payment.currency_id._convert(
                    payment.amount, company.currency_id, company,
                    payment.payment_date or today,
                ) if payment.currency_id != company.currency_id else payment.amount
                result[pid]["orders_due"] += amount
        return result

    def _compute_l10n_bg_pos_display(self):
        for partner in self:
            commercial = partner.commercial_partner_id or partner
            partner.l10n_bg_pos_represent_name = (
                commercial.sudo().l10n_bg_represent_contact_id.name or False
            )
            partner.l10n_bg_pos_payment_term = (
                commercial.sudo().property_payment_term_id.name or False
            )

    # ------------------------------------------------------------------
    # Зареждане в касата
    # ------------------------------------------------------------------

    @api.model
    def _load_pos_data_fields(self, config):
        fields_list = super()._load_pos_data_fields(config)
        if not fields_list:
            # Празен списък = всички полета; не го стеснявай.
            return fields_list
        return fields_list + [
            "l10n_bg_uic",
            "l10n_bg_uic_type",
            "l10n_bg_is_b2b_buyer",
            "l10n_bg_invoice_missing",
            "l10n_bg_b2b_route",
            "l10n_bg_pos_credit_limit",
            "l10n_bg_pos_total_due",
            "l10n_bg_pos_overdue",
            "l10n_bg_pos_orders_amount_due",
            "l10n_bg_pos_represent_name",
            "l10n_bg_pos_payment_term",
        ]

    @api.model
    def _load_pos_data_read(self, records, config):
        # Кредитът и пътят на документа зависят от фирмата на касата, не от
        # текущата фирма на потребителя.
        company = config.company_id
        return super(ResPartner, self.with_company(company))._load_pos_data_read(
            records.with_company(company), config
        )
