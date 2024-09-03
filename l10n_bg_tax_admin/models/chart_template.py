#  Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from odoo.addons.base.models.res_lang import intersperse
from odoo.addons.l10n_bg_config.models.account_move import get_doc_type, get_type_vat

_logger = logging.getLogger(__name__)


def _grouping(new_code, code_digits, grouping="[]"):
    if grouping.replace("[", "").replace("]", ""):
        grouping = list(map(int, grouping.replace("[", "").replace("]", "").split(",")))
        new_code = intersperse(new_code.ljust(code_digits, "0"), grouping, ".")[0]
    return new_code


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    grouping = fields.Char(
        string="Separator Format",
        default="[]",
        help="The Separator Format should be like [,n] where 0 < n :starting from Unit digit. "
        "-1 will end the separation. e.g. [3,2,-1] will represent 106500 to be 1.06.500; "
        "[1,2,-1] will represent it to be 106.50.0;[3] will represent it as 106.500",
    )

    @api.model
    def _prepare_transfer_account_template(self, prefix=None):
        """Prepare values to create the transfer account that is an intermediary account used when moving money
        from a liquidity account to another.

        :return:    A dictionary of values to create a new account.account.
        """
        digits = self.code_digits
        # grouping = self.grouping
        prefix = str(prefix or self.transfer_account_code_prefix or "")
        # Flatten the hierarchy of chart templates.
        chart_template = self
        chart_templates = self
        while chart_template.parent_id:
            chart_templates += chart_template.parent_id
            chart_template = chart_template.parent_id
        max_digits = digits - len(prefix)
        for num in range(1, int("".ljust(max_digits, "9"))):
            new_code = prefix + str(num).ljust(max_digits, "0")
            # new_code = _grouping(new_code, digits, grouping)
            rec = self.env["account.account.template"].search(
                [
                    ("code", "=", new_code),
                    ("chart_template_id", "in", chart_templates.ids),
                ],
                limit=1,
            )
            if not rec:
                break
        else:
            raise UserError(_("Cannot generate an unused account code."))

        return {
            "name": _("Liquidity Transfer"),
            "code": new_code,
            "account_type": "asset_current",
            "reconcile": True,
            "chart_template_id": self.id,
        }

    @api.model
    def _create_liquidity_journal_suspense_account(
        self, company, code_digits, grouping="[]"
    ):
        return self.env["account.account"].create(
            {
                "name": _("Bank Suspense Account"),
                "code": self.env["account.account"]._search_new_account_code(
                    company,
                    code_digits,
                    company.bank_account_code_prefix or "",
                    grouping="[]",
                ),
                "account_type": "asset_current",
                "company_id": company.id,
            }
        )

    @api.model
    def _create_cash_discount_loss_account(self, company, code_digits, grouping="[]"):
        new_code = "".ljust(code_digits - 1, "9") + "8"
        # new_code = _grouping(new_code, code_digits, grouping)
        return self.env["account.account"].create(
            {
                "name": _("Cash Discount Loss"),
                "code": new_code,
                "account_type": "expense",
                "company_id": company.id,
            }
        )

    @api.model
    def _create_cash_discount_gain_account(self, company, code_digits, grouping="[]"):
        new_code = "".ljust(code_digits - 1, "9") + "7"
        # new_code = _grouping(new_code, code_digits, grouping)
        return self.env["account.account"].create(
            {
                "name": _("Cash Discount Gain"),
                "code": new_code,
                "account_type": "income_other",
                "company_id": company.id,
            }
        )

    def _get_template_ref(self, position, fp, template_ref, company_id):
        if 'type_ids' not in position._fields:
            return template_ref

        type_invoice_ref = []
        for type_account in position.type_ids:
            fiscal_position_id = self.env["account.fiscal.position"]
            if type_account.position_dest_id:
                self.env.cr.execute(
                    f"""SELECT name
FROM ir_model_data
    WHERE model = '{type_account.position_dest_id._name}'
        AND res_id = {type_account.position_dest_id.id}
        AND module = 'l10n_bg'"""
                )
                position_fiscal = self.env.cr.fetchone()
                if position_fiscal:
                    fiscal_position_id = self.env.ref(
                        f"l10n_bg.{company_id.id}_{position_fiscal[0]}",
                        raise_if_not_found=False,
                    )
            type_invoice_ref.append(
                (
                    type_account,
                    {
                        "position_dest_id": fiscal_position_id.id,
                        "invoice_type": type_account.invoice_type,
                        "l10n_bg_type_vat": type_account.l10n_bg_type_vat,
                        "l10n_bg_doc_type": type_account.l10n_bg_doc_type,
                        "l10n_bg_narration": type_account.l10n_bg_narration,
                        "new_account_entry": type_account.new_account_entry,
                        "position_id": fp.id,
                    },
                )
            )
        template_ref.update(
            {
                "type_invoice_ref": type_invoice_ref,
            }
        )
        return template_ref

    def _get_templates(self, position, fp, **kwargs):
        template_vals = {}
        for key, template_ref in kwargs.items():
            if key == "tax_template_ref":
                tax_template_vals = []
                for tax in position.tax_ids:
                    tax_template_vals.append(
                        (
                            tax,
                            {
                                "tax_src_id": template_ref[tax.tax_src_id].id,
                                "tax_dest_id": tax.tax_dest_id
                                and template_ref[tax.tax_dest_id].id
                                or False,
                                "position_id": fp.id,
                            },
                        )
                    )
                template_vals["account.fiscal.position.tax"] = tax_template_vals
            if key == "acc_template_ref":
                account_template_vals = []
                for acc in position.account_ids:
                    account_template_vals.append(
                        (
                            acc,
                            {
                                "account_src_id": template_ref[acc.account_src_id].id,
                                "account_dest_id": template_ref[acc.account_dest_id].id,
                                "position_id": fp.id,
                            },
                        )
                    )
                template_vals["account.fiscal.position.account"] = account_template_vals
            if key == "type_invoice_ref":
                # _logger.info(template_ref)
                template_vals["account.fiscal.position.type"] = template_ref
                # for type_account in position.type_ids:
                #     template_vals["account.fiscal.position.type"].append(
                #         (
                #             type_account,
                #             {
                #                 "position_id": fp.id,
                #                 "invoice_type": type_account.invoice_type,
                #                 "l10n_bg_type_vat": type_account.l10n_bg_type_vat,
                #                 "l10n_bg_doc_type": type_account.l10n_bg_doc_type,
                #                 "l10n_bg_narration": type_account.l10n_bg_narration,
                #             },
                #         )
                #     )
        return template_vals

    def generate_fiscal_position(self, tax_template_ref, acc_template_ref, company_id):
        """This method generates Fiscal Position, Fiscal Position Accounts
        and Fiscal Position Taxes from templates.

        :param tax_template_ref: Taxes templates reference for generating account.fiscal.position.tax.
        :param acc_template_ref: Account templates reference for generating account.fiscal.position.account.
        :param company_id: the company to generate fiscal position data for
        :returns: True
        """
        self.ensure_one()
        positions = self.env["account.fiscal.position.template"].search(
            [("chart_template_id", "=", self.id)]
        )

        # first create fiscal positions in batch
        template_vals = []
        for position in positions:
            fp_vals = self._get_fp_vals(company_id, position)
            template_vals.append((position, fp_vals))
        fps = self._create_records_with_xmlid(
            "account.fiscal.position", template_vals, company_id
        )

        # then create fiscal position taxes and accounts
        todo_template_vals = {}
        for position, fp in zip(positions, fps):
            template_ref = {
                "tax_template_ref": tax_template_ref,
                "acc_template_ref": acc_template_ref,
            }
            kwargs = self._get_template_ref(position, fp, template_ref, company_id)
            todo_template_vals = self._get_templates(position, fp, **kwargs)
        for model_name, to_template_vals in todo_template_vals.items():
            self._create_records_with_xmlid(model_name, to_template_vals, company_id)

        return True

    def _load(self, company):
        """Installs this chart of accounts on the current company, replacing
        the existing one if it had already one defined. If some accounting entries
        had already been made, this function fails instead, triggering a UserError.

        Also, note that this function can only be run by someone with administration
        rights.
        """
        self.ensure_one()
        # do not use `request.env` here, it can cause deadlocks
        # Ensure everything is translated to the company's language, not the user's one.
        self = self.with_context(lang=company.partner_id.lang).with_company(company)
        if not self.env.is_admin():
            raise AccessError(_("Only administrators can load a chart of accounts"))

        existing_accounts = self.env["account.account"].search(
            [("company_id", "=", company.id)]
        )
        if existing_accounts:
            # we tolerate switching from accounting package (localization module) as long as there isn't yet any
            # accounting entries created for the company.
            if self.existing_accounting(company):
                raise UserError(
                    _(
                        "Could not install new chart of account as there are already accounting entries existing."
                    )
                )

            # delete accounting properties
            prop_values = [
                "account.account,%s" % (account_id,)
                for account_id in existing_accounts.ids
            ]
            existing_journals = self.env["account.journal"].search(
                [("company_id", "=", company.id)]
            )
            if existing_journals:
                prop_values.extend(
                    [
                        "account.journal,%s" % (journal_id,)
                        for journal_id in existing_journals.ids
                    ]
                )
            self.env["ir.property"].sudo().search(
                [("value_reference", "in", prop_values)]
            ).unlink()

            # delete account, journal, tax, fiscal position and reconciliation model
            models_to_delete = [
                "account.reconcile.model",
                "account.fiscal.position",
                "account.move.line",
                "account.move",
                "account.journal",
                "account.tax",
                "account.group",
            ]
            for model in models_to_delete:
                res = self.env[model].sudo().search([("company_id", "=", company.id)])
                if len(res):
                    res.with_context(force_delete=True).unlink()
            existing_accounts.unlink()

        company.write(
            {
                "currency_id": self.currency_id.id,
                "anglo_saxon_accounting": self.use_anglo_saxon,
                "account_storno": self.use_storno_accounting,
                "bank_account_code_prefix": self.bank_account_code_prefix,
                "cash_account_code_prefix": self.cash_account_code_prefix,
                "transfer_account_code_prefix": self.transfer_account_code_prefix,
                "chart_template_id": self.id,
            }
        )

        # set the coa currency to active
        self.currency_id.write({"active": True})

        # When we install the CoA of first company, set the currency to price types and pricelists
        if company.id == 1:
            for reference in [
                "product.list_price",
                "product.standard_price",
                "product.list0",
            ]:
                try:
                    tmp2 = self.env.ref(reference).write(
                        {"currency_id": self.currency_id.id}
                    )
                except ValueError:
                    pass

        # Set the fiscal country before generating taxes in case the company does not have a country_id set yet
        if self.country_id:
            # If this CoA is made for only one country, set it as the fiscal country of the company.
            company.account_fiscal_country_id = self.country_id
        elif not company.account_fiscal_country_id:
            company.account_fiscal_country_id = self.env.ref("base.us")

        # Install all the templates objects and generate the real objects
        acc_template_ref, taxes_ref = self._install_template(
            company, code_digits=self.code_digits
        )

        # Set default cash discount write-off accounts
        if not company.account_journal_early_pay_discount_loss_account_id:
            company.account_journal_early_pay_discount_loss_account_id = (
                self._create_cash_discount_loss_account(
                    company, self.code_digits, self.grouping
                )
            )
        if not company.account_journal_early_pay_discount_gain_account_id:
            company.account_journal_early_pay_discount_gain_account_id = (
                self._create_cash_discount_gain_account(
                    company, self.code_digits, self.grouping
                )
            )

        # Set default cash difference account on company
        if not company.account_journal_suspense_account_id:
            company.account_journal_suspense_account_id = (
                self._create_liquidity_journal_suspense_account(
                    company, self.code_digits, self.grouping
                )
            )

        if not company.account_journal_payment_debit_account_id:
            company.account_journal_payment_debit_account_id = self.env[
                "account.account"
            ].create(
                {
                    "name": _("Outstanding Receipts"),
                    "code": self.env["account.account"]._search_new_account_code(
                        company,
                        self.code_digits,
                        company.bank_account_code_prefix or "",
                        self.grouping,
                    ),
                    "reconcile": True,
                    "account_type": "asset_current",
                    "company_id": company.id,
                }
            )

        if not company.account_journal_payment_credit_account_id:
            company.account_journal_payment_credit_account_id = self.env[
                "account.account"
            ].create(
                {
                    "name": _("Outstanding Payments"),
                    "code": self.env["account.account"]._search_new_account_code(
                        company,
                        self.code_digits,
                        company.bank_account_code_prefix or "",
                        self.grouping,
                    ),
                    "reconcile": True,
                    "account_type": "asset_current",
                    "company_id": company.id,
                }
            )

        if not company.default_cash_difference_expense_account_id:
            company.default_cash_difference_expense_account_id = self.env[
                "account.account"
            ].create(
                {
                    "name": _("Cash Difference Loss"),
                    "code": self.env["account.account"]._search_new_account_code(
                        company, self.code_digits, "999", self.grouping
                    ),
                    "account_type": "expense",
                    "tag_ids": [
                        (6, 0, self.env.ref("account.account_tag_investing").ids)
                    ],
                    "company_id": company.id,
                }
            )

        if not company.default_cash_difference_income_account_id:
            company.default_cash_difference_income_account_id = self.env[
                "account.account"
            ].create(
                {
                    "name": _("Cash Difference Gain"),
                    "code": self.env["account.account"]._search_new_account_code(
                        company, self.code_digits, "999", self.grouping
                    ),
                    "account_type": "income_other",
                    "tag_ids": [
                        (6, 0, self.env.ref("account.account_tag_investing").ids)
                    ],
                    "company_id": company.id,
                }
            )

        # Set the transfer account on the company
        company.transfer_account_id = self.env["account.account"].search(
            [
                ("code", "=like", self.transfer_account_code_prefix + "%"),
                ("company_id", "=", company.id),
            ],
            limit=1,
        )

        # Create Bank journals
        self._create_bank_journals(company, acc_template_ref)

        # Create the current year earning account if it wasn't present in the CoA
        company.get_unaffected_earnings_account()

        # set the default taxes on the company
        company.account_sale_tax_id = (
            self.env["account.tax"]
            .search(
                [
                    ("type_tax_use", "in", ("sale", "all")),
                    ("company_id", "=", company.id),
                ],
                limit=1,
            )
            .id
        )
        company.account_purchase_tax_id = (
            self.env["account.tax"]
            .search(
                [
                    ("type_tax_use", "in", ("purchase", "all")),
                    ("company_id", "=", company.id),
                ],
                limit=1,
            )
            .id
        )

        return {}


class AccountAccountTemplate(models.Model):
    _inherit = "account.account.template"

    @api.model
    def _load_records(self, data_list, update=False):
        for data in data_list:
            vals = data["values"]
            if not vals.get("chart_template_id", False):
                continue
            account_template_id = self.env["account.chart.template"].browse(
                vals["chart_template_id"]
            )
            digits = account_template_id.code_digits
            grouping = account_template_id.grouping
            if grouping:
                data["values"]["code"] = _grouping(
                    data["values"]["code"], digits, grouping
                )
        return super()._load_records(data_list, update=update)

class AccountTaxTemplate(models.Model):
    _inherit = 'account.tax.template'

    l10n_bg_reverse_charge_vat =  fields.Boolean('Reverse charge with VAT')
