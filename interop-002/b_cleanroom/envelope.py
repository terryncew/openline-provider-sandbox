"""Receipt envelope verification, written from olp-wire-canon SPEC.md
sections 2-4 and the repaired RECEIPT_SCHEMA.md.

The signed body is the receipt minus exactly `payload_hash` and
`signature`. `payload_hash` MUST equal lowercase-hex SHA-256 over the
canonical body bytes. The Ed25519 signature MUST verify over the canonical
body bytes (not over the hash, not over the envelope).
"""

from __future__ import annotations

import hashlib
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .canon import canonical_bytes

KIND = "proof_to_policy_decision_receipt"
RECEIPT_VERSION = "0.4"
CANON_ID = "olp-canonical-json-int-v1"


def verify_envelope(receipt: dict[str, Any], pinned_pubkey_hex: str) -> tuple[bool, str]:
    """Returns (True, 'OK') or (False, reason_code)."""
    for field, expected in (
        ("kind", KIND),
        ("receipt_version", RECEIPT_VERSION),
        ("canonicalization_id", CANON_ID),
    ):
        if receipt.get(field) != expected:
            return False, "ENVELOPE_FIELD_MISMATCH"
    signature = receipt.get("signature")
    payload_hash = receipt.get("payload_hash")
    if not isinstance(signature, dict) or signature.get("algorithm") != "Ed25519":
        return False, "SIGNATURE_INVALID"
    body = {k: v for k, v in receipt.items() if k not in ("payload_hash", "signature")}
    try:
        canonical = canonical_bytes(body)
    except Exception:
        return False, "SIGNATURE_INVALID"
    if not isinstance(payload_hash, str) or payload_hash != hashlib.sha256(canonical).hexdigest():
        return False, "SIGNATURE_INVALID"
    try:
        embedded = str(signature["public_key"])
        if embedded.lower() != pinned_pubkey_hex.lower():
            return False, "ISSUER_NOT_PINNED"
        public = Ed25519PublicKey.from_public_bytes(bytes.fromhex(pinned_pubkey_hex))
        public.verify(bytes.fromhex(str(signature["value"])), canonical)
    except (InvalidSignature, ValueError, KeyError, TypeError):
        return False, "SIGNATURE_INVALID"
    return True, "OK"
