"""Signed-envelope verification, from olp-wire-canon SPEC.md section 2/4
and the receipt-gate v0.4 decision-receipt profile (RECEIPT_SCHEMA.md).

A receipt is one JSON object. The signed body is the receipt after removing
exactly two top-level members: payload_hash and signature.
payload_hash = lowercase hex SHA-256 over the canonical JSON bytes of the body.
signature = {algorithm: "Ed25519", public_key: 64 lowercase hex chars,
             value: 128 lowercase hex chars}, computed directly over the
canonical body bytes.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .canon import CanonError, canonical_json, strict_json_loads

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_PUBKEY_RE = re.compile(r"^[0-9a-f]{64}$")
_SIG_RE = re.compile(r"^[0-9a-f]{128}$")


class EnvelopeError(ValueError):
    pass


def split_envelope(receipt: dict[str, Any]) -> tuple[dict[str, Any], str, dict[str, Any]]:
    """Return (body, payload_hash, signature_dict)."""
    if not isinstance(receipt, dict):
        raise EnvelopeError("receipt is not a JSON object")
    payload_hash = receipt.get("payload_hash")
    signature = receipt.get("signature")
    if not isinstance(payload_hash, str) or not _HASH_RE.match(payload_hash):
        raise EnvelopeError("payload_hash missing or malformed")
    if not isinstance(signature, dict):
        raise EnvelopeError("signature missing or malformed")
    if signature.get("algorithm") != "Ed25519":
        raise EnvelopeError("signature algorithm is not Ed25519")
    if not isinstance(signature.get("public_key"), str) or not _PUBKEY_RE.match(
        signature["public_key"]
    ):
        raise EnvelopeError("signature public_key malformed")
    if not isinstance(signature.get("value"), str) or not _SIG_RE.match(
        signature["value"]
    ):
        raise EnvelopeError("signature value malformed")
    body = {k: v for k, v in receipt.items() if k not in ("payload_hash", "signature")}
    return body, payload_hash, signature


def verify_envelope(receipt_text: str) -> tuple[dict[str, Any], bytes, dict[str, Any]]:
    """Parse, recompute payload_hash, verify Ed25519 signature.

    Returns (body, canonical_body_bytes, signature). Raises EnvelopeError
    or CanonError on any failure.
    """
    receipt = strict_json_loads(receipt_text)
    body, payload_hash, signature = split_envelope(receipt)
    try:
        canonical = canonical_json(body)
    except CanonError as exc:
        raise EnvelopeError(f"body not canonicalizable: {exc}") from exc
    recomputed = hashlib.sha256(canonical).hexdigest()
    if recomputed != payload_hash:
        raise EnvelopeError("payload_hash mismatch")
    try:
        pubkey = Ed25519PublicKey.from_public_bytes(
            bytes.fromhex(signature["public_key"])
        )
        pubkey.verify(bytes.fromhex(signature["value"]), canonical)
    except (InvalidSignature, ValueError) as exc:
        raise EnvelopeError("signature verification failed") from exc
    return body, canonical, signature


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
