# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

API_URL_TEST = "https://3dsgate-dev.borica.bg/cgi-bin/cgi_link"
API_URL_PROD = "https://3dsgate.borica.bg/cgi-bin/cgi_link"

# Order MUST match the spec for MAC_GENERAL signing of TRTYPE=1 (Sale).
# Reference: P-OM-41 v4.0 §5.7, page 32.
SALE_SIGN_FIELDS = (
    "TERMINAL",
    "TRTYPE",
    "AMOUNT",
    "CURRENCY",
    "ORDER",
    "TIMESTAMP",
    "NONCE",
    "RFU",
)

SALE_RESPONSE_SIGN_FIELDS = (
    "ACTION",
    "RC",
    "APPROVAL",
    "TERMINAL",
    "TRTYPE",
    "AMOUNT",
    "CURRENCY",
    "ORDER",
    "RRN",
    "INT_REF",
    "PARES_STATUS",
    "ECI",
    "TIMESTAMP",
    "NONCE",
    "RFU",
)
