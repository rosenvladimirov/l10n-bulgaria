import re
import logging

_logger = logging.getLogger(__name__)


class BankTransactionParser(object):
    """Base class for parsing bank transaction descriptions in Bulgarian MT940 files."""

    # Common patterns for Bulgarian bank statements
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
        """Parse transaction description and extract structured data."""
        self.parsed_data = self._extract_common_fields()
        return self.parsed_data

    def _extract_common_fields(self):
        """Extract common fields from transaction description."""
        data = {}

        # Try to extract recipient/partner name
        for pattern in self.RECIPIENT_PATTERNS:
            recipient = self._extract_after_pattern(pattern)
            if recipient:
                data["ПОЛУЧАТЕЛ:"] = recipient
                break

        # Try to extract account number
        for pattern in self.ACCOUNT_PATTERNS:
            account = self._extract_after_pattern(pattern)
            if account:
                data["СМЕТКА:"] = account
                break

        # Try to extract BIC
        for pattern in self.BIC_PATTERNS:
            bic = self._extract_after_pattern(pattern)
            if bic:
                data["BIC:"] = bic
                break

        # Try to extract exchange rate
        for pattern in self.RATE_PATTERNS:
            rate = self._extract_after_pattern(pattern)
            if rate:
                data["КУРС:"] = rate
                break

        return data

    def _extract_after_pattern(self, pattern):
        """Extract text after a pattern until next pattern or end."""
        if pattern not in self.tag_data:
            return None

        # Find the position after the pattern
        start_pos = self.tag_data.find(pattern) + len(pattern)
        remaining_text = self.tag_data[start_pos:]

        # Find the next pattern or end of string
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
        """Return parsed data (for backward compatibility)."""
        if not self.parsed_data:
            self.parse()
        return self.parsed_data


class ProCreditCustomerReference(BankTransactionParser):
    """ProCredit Bank specific parser."""

    def __init__(self, tag_data):
        super().__init__(tag_data, bank_swift_id="PRCBBGSF")


class UniCreditCustomerReference(BankTransactionParser):
    """UniCredit Bulbank specific parser."""

    def __init__(self, tag_data):
        super().__init__(tag_data, bank_swift_id="UNCRBGSF")


class UBBCustomerReference(BankTransactionParser):
    """United Bulgarian Bank (UBB/ОББ) specific parser."""

    def __init__(self, tag_data):
        super().__init__(tag_data, bank_swift_id="UBBSBGSF")
