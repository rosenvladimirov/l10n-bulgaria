#!/usr/bin/env python3
# Copyright 2026 Rosen Vladimirov
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Standalone verification that the myPOS sign/verify logic is correct.

Run without Odoo:    python3 standalone_signature_check.py

Mirrors the PHP SDK behaviour (IPC/Base.php::_createSignature):
    base64_encode( openssl_sign(
        base64_encode(implode('-', $params)),
        $privKey,
        OPENSSL_ALGO_SHA256,
    ) )
"""

import base64
import sys
from collections import OrderedDict
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID


def canonicalize(params):
    joined = "-".join("" if v is None else str(v) for v in params.values())
    return base64.b64encode(joined.encode("utf-8"))


def sign(params, priv_pem):
    priv = serialization.load_pem_private_key(priv_pem.encode(), password=None)
    sig = priv.sign(canonicalize(params), padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(sig).decode("ascii")


def verify(params, sig_b64, cert_pem):
    cert = x509.load_pem_x509_certificate(cert_pem.encode())
    try:
        cert.public_key().verify(
            base64.b64decode(sig_b64),
            canonicalize(params),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except InvalidSignature:
        return False


def make_keypair():
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "myPOS test")]))
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "myPOS test")]))
        .public_key(priv.public_key())
        .serial_number(1)
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=30))
        .sign(priv, hashes.SHA256())
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    return priv_pem, cert_pem


def run():
    failures = 0

    def check(name, cond):
        nonlocal failures
        status = "PASS" if cond else "FAIL"
        if not cond:
            failures += 1
        print(f"  [{status}] {name}")

    print("=== myPOS signature algorithm — standalone check ===\n")

    print("[1] Canonicalization parity with PHP SDK")
    check(
        "base64(implode('-', ['1','two','']))",
        canonicalize(OrderedDict([("a", "1"), ("b", "two"), ("c", "")]))
        == base64.b64encode(b"1-two-"),
    )
    check(
        "None and ints serialised correctly",
        canonicalize(OrderedDict([("a", None), ("b", 42), ("c", "x")]))
        == base64.b64encode(b"-42-x"),
    )
    check(
        "order matters",
        canonicalize(OrderedDict([("x", "1"), ("y", "2")]))
        != canonicalize(OrderedDict([("y", "2"), ("x", "1")])),
    )

    print("\n[2] Sign/verify round trip")
    priv, cert = make_keypair()
    payload = OrderedDict(
        [
            ("IPCmethod", "IPCPurchase"),
            ("IPCVersion", "1.4"),
            ("SID", "000000000000010"),
            ("OrderID", "TEST-1"),
            ("Amount", "1.00"),
            ("Currency", "EUR"),
        ]
    )
    sig = sign(payload, priv)
    check("verify accepts genuine signature", verify(payload, sig, cert))
    check(
        "verify rejects tampered amount",
        not verify(
            OrderedDict(list(payload.items())[:-2] + [("Amount", "999.99"), ("Currency", "EUR")]),
            sig,
            cert,
        ),
    )
    check(
        "verify rejects garbage signature",
        not verify(payload, base64.b64encode(b"not-a-real-sig").decode(), cert),
    )

    print("\n[3] Signature length & encoding")
    raw = base64.b64decode(sig)
    check("sig is 256 bytes (RSA-2048)", len(raw) == 256)
    check("sig is valid base64 ASCII", all(c < 128 for c in sig.encode()))

    print("\n[4] Sandbox sample (no real network call)")
    sandbox = OrderedDict(
        [
            ("IPCmethod", "IPCPurchase"),
            ("IPCVersion", "1.4"),
            ("SID", "000000000000010"),
            ("WalletNumber", "61938166610"),
            ("KeyIndex", "1"),
            ("OrderID", "SANDBOX-001"),
            ("Amount", "12.50"),
            ("Currency", "EUR"),
        ]
    )
    sig2 = sign(sandbox, priv)
    check("sandbox payload signs cleanly", verify(sandbox, sig2, cert))

    print(f"\n=== Result: {'OK' if failures == 0 else f'{failures} FAILED'} ===")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
