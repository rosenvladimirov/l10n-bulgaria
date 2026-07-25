# Copyright 2025 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

# Парсери за банкови транзакции в български MT940 файлове.
# Поддържа ProCredit, UniCredit Bulbank и UBB (ОББ).

import logging

_logger = logging.getLogger(__name__)


class BankTransactionParser(object):
    """Базов клас за парсване на описания в български MT940 файлове."""

    RECIPIENT_PATTERNS = [
        "ПОЛУЧАТЕЛ:",
        "получател:",
        "Получател:",
    ]
    ACCOUNT_PATTERNS = [
        "СМЕТКА:",
        "сметка:",
        "Сметка:",
    ]
    BIC_PATTERNS = [
        "BIC:",
        "bic:",
        "Bic:",
    ]
    RATE_PATTERNS = [
        "КУРС:",
        "курс:",
        "Курс:",
    ]

    def __init__(self, tag_data, bank_swift_id=None):
        self.tag_data = tag_data
        self.bank_swift_id = bank_swift_id
        self.parsed_data = {}

    def get_version(self):
        return self.bank_swift_id

    def parse(self):
        """Парсва описанието и извлича структурирани данни."""
        self.parsed_data = self._extract_common_fields()
        return self.parsed_data

    def _extract_common_fields(self):
        """Извлича общи полета: ПОЛУЧАТЕЛ, СМЕТКА, BIC, КУРС."""
        data = {}

        for pattern in self.RECIPIENT_PATTERNS:
            recipient = self._extract_after_pattern(pattern)
            if recipient:
                data["ПОЛУЧАТЕЛ:"] = recipient
                break

        for pattern in self.ACCOUNT_PATTERNS:
            account = self._extract_after_pattern(pattern)
            if account:
                data["СМЕТКА:"] = account
                break

        for pattern in self.BIC_PATTERNS:
            bic = self._extract_after_pattern(pattern)
            if bic:
                data["BIC:"] = bic
                break

        for pattern in self.RATE_PATTERNS:
            rate = self._extract_after_pattern(pattern)
            if rate:
                data["КУРС:"] = rate
                break

        return data

    def _extract_after_pattern(self, pattern):
        """Извлича текст след шаблон до следващия шаблон или край."""
        if pattern not in self.tag_data:
            return None

        start_pos = self.tag_data.find(pattern) + len(pattern)
        remaining_text = self.tag_data[start_pos:]

        end_pos = len(remaining_text)
        all_patterns = (
            self.RECIPIENT_PATTERNS
            + self.ACCOUNT_PATTERNS
            + self.BIC_PATTERNS
            + self.RATE_PATTERNS
        )

        for next_pattern in all_patterns:
            if next_pattern == pattern:
                continue
            if next_pattern in remaining_text:
                pos = remaining_text.find(next_pattern)
                if pos < end_pos:
                    end_pos = pos

        result = remaining_text[:end_pos].strip()
        return result if result else None

    def get_data(self):
        """Връща парснатите данни."""
        if not self.parsed_data:
            self.parse()
        return self.parsed_data


class ProCreditCustomerReference(BankTransactionParser):
    """ПроКредит Банк."""

    def __init__(self, tag_data):
        super().__init__(tag_data, bank_swift_id="PRCBBGSF")


class UniCreditCustomerReference(BankTransactionParser):
    """УниКредит Булбанк."""

    def __init__(self, tag_data):
        super().__init__(tag_data, bank_swift_id="UNCRBGSF")


class UBBCustomerReference(BankTransactionParser):
    """Обединена Българска Банка (ОББ/UBB)."""

    def __init__(self, tag_data):
        super().__init__(tag_data, bank_swift_id="UBBSBGSF")
