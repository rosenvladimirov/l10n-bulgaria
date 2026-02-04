import io
import logging
import re

from odoo import _, api, models
from odoo.exceptions import UserError
from .bank_custom_tags import ProCreditCustomerReference

_logger = logging.getLogger(__name__)

try:
    import mt940
    from mt940 import tags
except ImportError:
    _logger.debug("mt-940 not found.")
    mt940 = None


class AccountStatementImport(models.TransientModel):
    _inherit = "account.statement.import"

    @api.model
    def _check_mt940(self, data_file):
        if not data_file:
            return []

        try:
            for encoding in ["utf-8", "windows-1251", "iso-8859-5"]:
                try:
                    _logger.debug(f"Опит за декодиране с {encoding}")
                    data = io.BytesIO(data_file).read().decode(encoding)
                    # Създаваме инстанция на MT940 с декодираните данни
                    return mt940.parse(data)

                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    _logger.error(f"Грешка при парсване на MT940: {str(e)}")
                    return []

            _logger.error("Неуспешно декодиране с всички опитани кодировки")
            return []

        except Exception as e:
            _logger.error(f"Обща грешка при обработка на MT940: {str(e)}")
            return []

    @api.model
    def _get_detail_data(self, transaction_details):
        res = {}
        for detail in transaction_details.split("+"):
            _logger.info(f"Detail: {detail}")
            if detail.startswith("21"):
                res.update({"21": detail.replace("21", "")})
            elif detail.startswith("22"):
                detail_row_22 = detail.replace("22", "")
                res.update(
                    {
                        "22": detail_row_22,
                        "pro_credit_customer_data": ProCreditCustomerReference(detail_row_22).get_data()
                    }
                )
                # if len(detail_row_22.split(":")) > 1:
                #     detail_row_22_customer = detail_row_22.split(":")
                #     detail_row_22_customer_data = dict(
                #         zip(detail_row_22_customer[::2], detail_row_22_customer[1::2])
                #     )
                #     _logger.debug(f"Customer data: {detail_row_22_customer_data}")
            elif detail.startswith("30"):
                res.update(
                    {
                        "30": detail.replace("30", ""),
                    }
                )
            elif detail.startswith("31"):
                res.update(
                    {
                        "31": detail.replace("31", ""),
                    }
                )
            elif detail.startswith("32"):
                res.update(
                    {
                        "32": detail.replace("32", ""),
                    }
                )
            elif detail.startswith("33"):
                res.update(
                    {
                        "33": detail.replace("33", ""),
                    }
                )
        return res

    @api.model
    def _prepare_mt940_transaction_line(self, transaction):
        detail_data = {}
        transaction_details = transaction["transaction_details"]
        detail_data = self._get_detail_data(transaction_details)

        account_number = detail_data.get("31", "")
        partner_name = detail_data.get("33", "")
        if detail_data.get("32"):
            partner_name = detail_data.get("32", partner_name)

        if detail_data.get("pro_credit_customer_data"):
            partner_name = detail_data.get("pro_credit_customer_data").get('ПОЛУЧАТЕЛ:', partner_name)
            account_number = detail_data.get("pro_credit_customer_data").get('СМЕТКА:', account_number)

        vals = {
            "date": transaction["date"],
            "payment_ref": detail_data.get(
                "21", f"{transaction['customer_reference']}"
            ),
            "amount": float(transaction["amount"].amount),
            "unique_import_id": f"{transaction['id']}"
            f"-{transaction['customer_reference']}",
            "account_number": account_number,
            "partner_name": partner_name,
        }
        return vals

    def _parse_file(self, data_file):
        mt940_transactions = self._check_mt940(data_file)
        _logger.info(f"MT940 transactions: {mt940_transactions}")
        if not mt940_transactions:
            return super()._parse_file(data_file)

        result = []
        try:
            transactions = []
            total_amt = 0.00

            mt940_transactions_data = mt940_transactions.data
            for account in mt940_transactions:
                if not account:
                    continue

                vals = self._prepare_mt940_transaction_line(account.data)
                if vals:
                    transactions.append(vals)
                    total_amt += vals["amount"]
            balance = float(
                mt940_transactions_data["final_closing_balance"].amount.amount
            )
            vals_bank_statement = {
                "name": mt940_transactions_data["statement_number"],
                "reference": mt940_transactions_data["transaction_reference"],
                "transactions": transactions,
                "balance_start": balance - total_amt,
                "balance_end_real": balance,
            }
            result.append(
                (
                    mt940_transactions_data["final_opening_balance"].amount.currency,
                    mt940_transactions_data["account_identification"],
                    [vals_bank_statement],
                )
            )
        except Exception as e:
            raise UserError(
                _(
                    "The following problem occurred during import. "
                    "The file might not be valid.\n\n %s"
                )
                % str(e)
            ) from e
        return result
