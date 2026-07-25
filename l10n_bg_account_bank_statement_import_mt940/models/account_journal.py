# Copyright 2025 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import hashlib
import io
import logging
import re

from odoo import _, models
from odoo.exceptions import UserError

from ..lib.bank_custom_tags import (
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


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _get_bank_statements_available_import_formats(self):
        """Добавя MT940 към списъка с поддържани формати."""
        rslt = super()._get_bank_statements_available_import_formats()
        rslt.append("MT940")
        return rslt

    # ------------------------------------------------------------------
    # Парсване на MT940 файл
    # ------------------------------------------------------------------

    def _check_mt940(self, data_file):
        """Парсва MT940 файл с fallback по кодировки."""
        if not data_file:
            _logger.info("MT940: empty file")
            return None
        if not mt940:
            _logger.warning("MT940: mt-940 library not installed, skipping")
            return None

        for encoding in ("utf-8", "windows-1251", "iso-8859-5"):
            try:
                data = data_file.decode(encoding)
                # MT940 файловете започват с {:  (напр. {1: или {4:)
                # или директно с тага :20: / :25:
                stripped = data.lstrip()
                if not (stripped.startswith('{') or stripped.startswith(':20:') or stripped.startswith(':25:')):
                    _logger.info("MT940: file does not look like MT940 (starts with: %r)", stripped[:40])
                    return None
                result = mt940.parse(data)
                if result:
                    _logger.info("MT940: parsed successfully with encoding %s", encoding)
                return result
            except UnicodeDecodeError:
                continue
            except Exception as e:
                _logger.error("MT940 parse error (%s): %s", encoding, e)
                return None

        _logger.error("MT940: all encoding attempts failed")
        return None

    # ------------------------------------------------------------------
    # Определяне на банков формат
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_bank_format(account_identification):
        """Определя банковия формат по IBAN/BIC от извлечението."""
        if not account_identification:
            return "procredit"
        upper = account_identification.upper()
        if "UBBS" in upper:
            return "ubb"
        # ProCredit, UniCredit — ползват един формат (+ separator, полета 21/30/31/32)
        return "procredit"

    @staticmethod
    def _get_bank_parser(bank_format, tag_data):
        """Връща подходящия парсер за конкретната банка."""
        if bank_format == "ubb":
            return UBBCustomerReference(tag_data)
        if "UNCR" in tag_data.upper():
            return UniCreditCustomerReference(tag_data)
        return ProCreditCustomerReference(tag_data)

    # ------------------------------------------------------------------
    # Парсване на детайли по банков формат
    # ------------------------------------------------------------------

    def _get_detail_data_procredit(self, transaction_details, bank_format="procredit"):
        """Парсва ProCredit/UniCredit формат (разделител ^ или +)."""
        res = {}
        separator = "^" if "^" in transaction_details else "+"

        for detail in transaction_details.split(separator):
            detail = detail.strip()
            if detail.startswith("00"):
                res["00"] = detail[2:]
            elif detail.startswith("20"):
                res["20"] = detail[2:]
            elif detail.startswith("21"):
                res["21"] = detail[2:]
            elif detail.startswith("22"):
                detail_22 = detail[2:]
                parser = self._get_bank_parser(bank_format, detail_22)
                parsed_data = parser.get_data()
                res.update({"22": detail_22, "bank_customer_data": parsed_data})
            elif detail.startswith("30"):
                res["30"] = detail[2:]
            elif detail.startswith("31"):
                res["31"] = detail[2:]
            elif detail.startswith("32"):
                res["32"] = detail[2:]
            elif detail.startswith("33"):
                res["33"] = detail[2:]
            elif detail.startswith("38"):
                res["38"] = detail[2:]
        return res

    def _get_detail_data_ubb(self, transaction_details):
        """Парсва UBB (ОББ) формат (разделители // и /)."""
        res = {}

        # Бизнес код в началото (1-4 цифри)
        business_code_match = re.match(r'^(\d{1,4})', transaction_details.strip())
        if business_code_match:
            res["business_code"] = business_code_match.group(1)
            transaction_details = transaction_details[len(res["business_code"]):]

        parts = transaction_details.split("//")
        description_parts = []
        iban_pattern = re.compile(r'BG\d{2}[A-Z]{4}\d{14}')
        bic_pattern = re.compile(r'[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?')

        for part in parts:
            if not part.strip():
                continue
            for subpart in part.split("/"):
                subpart = subpart.strip()
                if not subpart:
                    continue

                iban_match = iban_pattern.search(subpart)
                if iban_match and "38" not in res:
                    res["38"] = iban_match.group(0)
                    continue

                bic_match = bic_pattern.search(subpart)
                if bic_match and len(subpart) in (8, 11) and "30" not in res:
                    res["30"] = subpart
                    continue

                description_parts.append(subpart)

        if description_parts:
            res["20"] = description_parts[0] if description_parts else ""
            res["32"] = description_parts[1] if len(description_parts) > 1 else ""
            res["description_full"] = " ".join(description_parts)

        return res

    def _get_detail_data(self, transaction_details, bank_format="procredit"):
        """Делегира парсването към съответния банков формат."""
        if bank_format == "ubb":
            return self._get_detail_data_ubb(transaction_details)
        return self._get_detail_data_procredit(transaction_details, bank_format)

    # ------------------------------------------------------------------
    # Подготовка на транзакционен ред
    # ------------------------------------------------------------------

    def _prepare_mt940_transaction_line(self, transaction, bank_format="procredit", transaction_index=0):
        """Подготвя dict за един транзакционен ред от MT940 извлечение.

        Връща формат съвместим с EE account_bank_statement_import:
        name, date, amount, unique_import_id, account_number, partner_name, ref
        """
        transaction_details = transaction.get("transaction_details", "")
        detail_data = self._get_detail_data(transaction_details, bank_format)

        account_number = ""
        partner_name = ""
        payment_ref = transaction.get("customer_reference", "")

        if bank_format == "ubb":
            account_number = detail_data.get("38", "")
            partner_name = detail_data.get("32", "")
            payment_ref = detail_data.get("20", payment_ref)
            if not partner_name:
                partner_name = detail_data.get("description_full", "")[:35]
        else:
            account_number = detail_data.get("31", "")
            partner_name = detail_data.get("33", "")
            if detail_data.get("32"):
                partner_name = detail_data["32"]

            if detail_data.get("bank_customer_data"):
                bank_data = detail_data["bank_customer_data"]
                partner_name = bank_data.get('ПОЛУЧАТЕЛ:', partner_name)
                account_number = bank_data.get('СМЕТКА:', account_number)

            payment_ref = detail_data.get("21", payment_ref)

        # Fallback за payment_ref
        if not payment_ref:
            payment_ref = (
                detail_data.get("20", "") or
                detail_data.get("00", "") or
                transaction.get("id", "") or
                transaction.get("customer_reference", "") or
                "/"
            )

        # Генериране на уникален ID
        date_str = str(transaction["date"]).replace("-", "")
        amount_str = str(abs(float(transaction["amount"].amount))).replace(".", "")
        customer_ref = transaction.get("customer_reference", "")
        trans_id = transaction.get("id", "")
        details_hash = hashlib.md5(transaction_details.encode('utf-8')).hexdigest()[:8]

        unique_import_id = f"{date_str}-{amount_str}-{trans_id}-{transaction_index}-{details_hash}"
        if customer_ref:
            unique_import_id += f"-{customer_ref}"

        # В Odoo 16 account.bank.statement.line използва _inherits от account.move,
        # затова 'name' отива в account.move.name (journal entry number).
        # Описанието на транзакцията трябва да е в 'payment_ref'.
        return {
            "payment_ref": payment_ref,
            "date": transaction["date"],
            "amount": float(transaction["amount"].amount),
            "unique_import_id": unique_import_id,
            "account_number": account_number,
            "partner_name": partner_name,
            "ref": customer_ref or payment_ref,
        }

    # ------------------------------------------------------------------
    # Главен метод за EE import chain
    # ------------------------------------------------------------------

    def _parse_bank_statement_file(self, attachment):
        """Парсва MT940 файл за Odoo Enterprise bank statement import.

        Връща: (currency_code, account_number, [statement_vals])
        """
        mt940_data = self._check_mt940(attachment.raw)
        if mt940_data is None:
            return super()._parse_bank_statement_file(attachment)

        try:
            data = mt940_data.data
            account_identification = data.get("account_identification", "")
            bank_format = self._detect_bank_format(account_identification)
            _logger.info("MT940 bank format: %s, account: %s", bank_format, account_identification)

            transactions = []
            total_amt = 0.0

            for idx, account in enumerate(mt940_data):
                if not account:
                    continue
                vals = self._prepare_mt940_transaction_line(account.data, bank_format, idx)
                if vals:
                    transactions.append(vals)
                    total_amt += vals["amount"]

            balance = float(data["final_closing_balance"].amount.amount)
            currency_code = data["final_opening_balance"].amount.currency

            if not transactions:
                opening = float(data["final_opening_balance"].amount.amount)
                raise UserError(_(
                    "MT940 файлът е валиден, но не съдържа транзакции.\n\n"
                    "Сметка: %(account)s\n"
                    "Период: %(opening_date)s → %(closing_date)s\n"
                    "Opening balance: %(opening)s %(currency)s\n"
                    "Closing balance: %(closing)s %(currency)s\n\n"
                    "Файлът е балансово извлечение (без движения).\n"
                    "От онлайн banking-а на банката изберете "
                    "'Извлечение с операции' / 'Statement with transactions' "
                    "за избран период с движение и опитайте отново.",
                    account=account_identification,
                    opening_date=data["final_opening_balance"].date,
                    closing_date=data["final_closing_balance"].date,
                    opening="{:,.2f}".format(opening),
                    closing="{:,.2f}".format(balance),
                    currency=currency_code,
                ))

            stmt_vals = {
                "name": data.get("statement_number", ""),
                "reference": data.get("transaction_reference", ""),
                "transactions": transactions,
                "balance_start": balance - total_amt,
                "balance_end_real": balance,
            }

            return currency_code, account_identification, [stmt_vals]

        except UserError:
            raise
        except Exception as e:
            raise UserError(_(
                "Error importing MT940 file. The file might not be valid.\n\n%s",
                str(e),
            )) from e
