import io
import logging
import re

from odoo import _, api, models
from odoo.exceptions import UserError
from .bank_custom_tags import (
    BankTransactionParser,
    ProCreditCustomerReference,
    UniCreditCustomerReference,
    UBBCustomerReference,
)

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
    def _detect_bank_format(self, account_identification):
        """Detect bank format based on IBAN or BIC codes in the statement."""
        # UBB (ОББ) has BIC starting with UBBS
        if account_identification and "UBBS" in account_identification.upper():
            return "ubb"
        # ProCredit has BIC starting with BUIN or PRCB
        if account_identification and ("BUIN" in account_identification.upper() or "PRCB" in account_identification.upper()):
            return "procredit"
        # Unicredit Bulbank has BIC starting with UNCR
        if account_identification and "UNCR" in account_identification.upper():
            return "procredit"  # Uses same format as ProCredit (+ separator, fields 21/30/31/32)
        # Default to ProCredit format for backward compatibility
        return "procredit"

    @api.model
    def _get_bank_parser(self, bank_format, tag_data):
        """Get appropriate bank transaction parser based on bank format."""
        if bank_format == "ubb":
            return UBBCustomerReference(tag_data)
        elif "UNCR" in tag_data.upper():
            return UniCreditCustomerReference(tag_data)
        else:
            return ProCreditCustomerReference(tag_data)

    @api.model
    def _get_detail_data_procredit(self, transaction_details, bank_format="procredit"):
        """Parse ProCredit/UniCredit bank format (uses ^ or + as separator)."""
        res = {}
        # Detect separator: ^ or +
        separator = "^" if "^" in transaction_details else "+"

        for detail in transaction_details.split(separator):
            detail = detail.strip()
            _logger.info(f"Bank Detail ({bank_format}): {detail}")
            if detail.startswith("20"):
                res.update({"20": detail.replace("20", "", 1)})
            elif detail.startswith("21"):
                detail_21 = detail.replace("21", "", 1)
                res.update({"21": detail_21})
            elif detail.startswith("22"):
                detail_row_22 = detail.replace("22", "", 1)
                # Parse the detail using appropriate bank parser
                parser = self._get_bank_parser(bank_format, detail_row_22)
                parsed_data = parser.get_data()
                res.update(
                    {
                        "22": detail_row_22,
                        "bank_customer_data": parsed_data
                    }
                )
            elif detail.startswith("30"):
                res.update({"30": detail.replace("30", "", 1)})
            elif detail.startswith("31"):
                res.update({"31": detail.replace("31", "", 1)})
            elif detail.startswith("32"):
                res.update({"32": detail.replace("32", "", 1)})
            elif detail.startswith("33"):
                res.update({"33": detail.replace("33", "", 1)})
            elif detail.startswith("38"):
                res.update({"38": detail.replace("38", "", 1)})
        return res

    @api.model
    def _get_detail_data_ubb(self, transaction_details):
        """Parse UBB (ОББ) bank format (uses // and / as separators).

        Format: Business_Code//Description//Data/Data/IBAN//Reference/Bank////Date//
        Example: 245//PLASHTANE DANAK// TEST POLUCHATEL/ STSABGSF/ BG00STSA00000000000000//171030065/ BANKA DSK////20240201/ /
        """
        res = {}
        _logger.info(f"UBB Detail: {transaction_details}")

        # Extract business code (1-4 digits at the beginning)
        business_code_match = re.match(r'^(\d{1,4})', transaction_details.strip())
        if business_code_match:
            res["business_code"] = business_code_match.group(1)
            transaction_details = transaction_details[len(res["business_code"]):]

        # Split by // for major sections
        parts = transaction_details.split("//")

        # Extract data from parts
        description_parts = []
        iban_pattern = re.compile(r'BG\d{2}[A-Z]{4}\d{14}')
        bic_pattern = re.compile(r'[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?')

        for i, part in enumerate(parts):
            if not part.strip():
                continue

            # Split by / for sub-parts
            subparts = part.split("/")

            for subpart in subparts:
                subpart = subpart.strip()
                if not subpart:
                    continue

                # Try to extract IBAN
                iban_match = iban_pattern.search(subpart)
                if iban_match and "38" not in res:
                    res["38"] = iban_match.group(0)
                    continue

                # Try to extract BIC (8 or 11 characters)
                bic_match = bic_pattern.search(subpart)
                if bic_match and len(subpart) in [8, 11] and "30" not in res:
                    res["30"] = subpart
                    continue

                # Collect description parts (partner name, payment reference, etc.)
                description_parts.append(subpart)

        # Combine description parts for partner_name and payment_ref
        if description_parts:
            # First meaningful part is usually payment reference
            res["20"] = description_parts[0] if len(description_parts) > 0 else ""
            # Second part is usually partner name
            res["32"] = description_parts[1] if len(description_parts) > 1 else ""
            # Store all for debugging
            res["description_full"] = " ".join(description_parts)

        return res

    @api.model
    def _get_detail_data(self, transaction_details, bank_format="procredit"):
        """Parse transaction details based on bank format."""
        if bank_format == "ubb":
            return self._get_detail_data_ubb(transaction_details)
        else:
            return self._get_detail_data_procredit(transaction_details, bank_format)

    @api.model
    def _prepare_mt940_transaction_line(self, transaction, bank_format="procredit"):
        detail_data = {}
        transaction_details = transaction["transaction_details"]
        detail_data = self._get_detail_data(transaction_details, bank_format)

        account_number = ""
        partner_name = ""
        payment_ref = transaction.get("customer_reference", "")

        if bank_format == "ubb":
            # UBB format: IBAN in field 38, partner name in field 32, payment ref in field 20
            account_number = detail_data.get("38", "")
            partner_name = detail_data.get("32", "")
            payment_ref = detail_data.get("20", payment_ref)
            # If no partner name, try to get from description
            if not partner_name:
                partner_name = detail_data.get("description_full", "")[:35]
        else:
            # ProCredit/UniCredit format
            account_number = detail_data.get("31", "")
            partner_name = detail_data.get("33", "")
            if detail_data.get("32"):
                partner_name = detail_data.get("32", partner_name)

            # Use generic bank_customer_data from parser (works for all banks)
            if detail_data.get("bank_customer_data"):
                bank_data = detail_data.get("bank_customer_data")
                partner_name = bank_data.get('ПОЛУЧАТЕЛ:', partner_name)
                account_number = bank_data.get('СМЕТКА:', account_number)

            payment_ref = detail_data.get("21", payment_ref)

        vals = {
            "date": transaction["date"],
            "payment_ref": payment_ref,
            "amount": float(transaction["amount"].amount),
            "unique_import_id": f"{transaction['id']}"
            f"-{transaction.get('customer_reference', '')}",
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

            # Detect bank format based on account identification
            account_identification = mt940_transactions_data.get("account_identification", "")
            bank_format = self._detect_bank_format(account_identification)
            _logger.info(f"Detected bank format: {bank_format} for account: {account_identification}")

            for account in mt940_transactions:
                if not account:
                    continue

                vals = self._prepare_mt940_transaction_line(account.data, bank_format)
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
