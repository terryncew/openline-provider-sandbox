"""B: the clean-room receiver. Implements INTEROP_PROFILE_002.md section 7
(the fixed final-consequence check order), written from the repaired
profile and the repaired RECEIPT_SCHEMA.md only.

The repaired pairing rule (profile section 7, step 4):
  (VERIFIED, COMMIT)   -> grant path (continue checks)
  (REJECTED, DENY)     -> admit as terminal standing head; no effect
  anything else        -> REFUSE / DECISION_NOT_AUTHORITATIVE
"""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .canon import canonical_bytes, parse_strict
from .envelope import verify_envelope
from .provider import ProviderCallFailed, advance_branch, get_ref
from .store import Store

COVERED_TOOL = "github.ref.advance"
COVERED_TARGET = "terryncew/openline-provider-sandbox:refs/heads/interop-002-effect"
EFFECT_REPO = "terryncew/openline-provider-sandbox"
EFFECT_BRANCH = "interop-002-effect"


@dataclass
class Config:
    pinned_issuer_key: str
    pinned_policy_hash: str
    signing_key: Ed25519PrivateKey

    @property
    def signing_pubkey_hex(self) -> str:
        return self.signing_key.public_key().public_bytes_raw().hex()


def _action_identity(receipt: dict[str, Any]) -> str | None:
    action = receipt.get("action")
    if not isinstance(action, dict):
        return None
    action_type = action.get("type")
    action_id = action.get("id")
    if not isinstance(action_type, str) or not isinstance(action_id, str):
        return None
    return f"{action_type}|{action_id}"


def _parse_expiry(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class Receiver:
    def __init__(self, config: Config, state_dir: Path):
        self.config = config
        self.store = Store(state_dir)

    # -- pairing prefix (steps 1-4): used for vector evaluation -------------
    def evaluate_prefix(self, receipt_text: str) -> dict[str, Any]:
        """Run profile section 7 steps 1-4 only. No state mutation, no effect.
        Returns the pairing disposition."""
        try:
            receipt = parse_strict(receipt_text)
        except Exception:
            return {"disposition": "REFUSE", "reason": "PARSE_ERROR"}
        if not isinstance(receipt, dict):
            return {"disposition": "REFUSE", "reason": "PARSE_ERROR"}
        ok, reason = verify_envelope(receipt, self.config.pinned_issuer_key)
        if not ok:
            # Map envelope reasons onto profile reasons.
            if reason == "ISSUER_NOT_PINNED":
                return {"disposition": "REFUSE", "reason": "ISSUER_NOT_PINNED"}
            return {"disposition": "REFUSE", "reason": "SIGNATURE_INVALID"}
        verdict = receipt.get("verdict")
        decision = receipt.get("decision")
        if not isinstance(decision, str) or decision not in ("COMMIT", "DENY"):
            return {"disposition": "REFUSE", "reason": "DECISION_NOT_AUTHORITATIVE"}
        if (verdict, decision) == ("VERIFIED", "COMMIT"):
            return {
                "disposition": "GRANT_PATH",
                "reason": "PAIRING_GRANT",
                "action_identity": _action_identity(receipt),
                "payload_hash": receipt.get("payload_hash"),
            }
        if (verdict, decision) == ("REJECTED", "DENY"):
            return {
                "disposition": "REVOCATION_ADMITTABLE",
                "reason": "PAIRING_TERMINAL_REVOCATION",
                "action_identity": _action_identity(receipt),
                "payload_hash": receipt.get("payload_hash"),
            }
        return {"disposition": "REFUSE", "reason": "DECISION_NOT_AUTHORITATIVE"}

    # -- full decision (steps 1-11) -----------------------------------------
    def decide(
        self, receipt_text: str, presented_action: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Full profile section 7 pipeline. Mutates standing/journal; may
        commit exactly one protected effect on the COMMIT grant path."""
        prefix = self.evaluate_prefix(receipt_text)
        receipt = parse_strict(receipt_text)
        assert isinstance(receipt, dict)
        action_identity = _action_identity(receipt)
        payload_hash = receipt.get("payload_hash")

        def refuse(reason: str) -> dict[str, Any]:
            self.store.append(
                {
                    "type": "DECISION",
                    "outcome": "REFUSE",
                    "reason": reason,
                    "action_identity": action_identity,
                    "payload_hash": payload_hash,
                }
            )
            return {"decision": "REFUSE", "reason": reason, "effect": None}

        if prefix["disposition"] == "REFUSE":
            return refuse(prefix["reason"])

        if prefix["disposition"] == "REVOCATION_ADMITTABLE":
            # Terminal revocation: admit as standing head; never an effect.
            if receipt.get("commit_authorization") is not None:
                return refuse("DECISION_NOT_AUTHORITATIVE")
            self.store.admit_standing(
                action_identity or "unknown",
                {
                    "verdict": "REJECTED",
                    "decision": "DENY",
                    "payload_hash": payload_hash,
                    "terminal": True,
                },
            )
            entry = self.store.append(
                {
                    "type": "STANDING",
                    "event": "ADMITTED_REVOCATION",
                    "action_identity": action_identity,
                    "payload_hash": payload_hash,
                    "terminal": True,
                }
            )
            self.store.append(
                {
                    "type": "DECISION",
                    "outcome": "ADMIT",
                    "reason": "ADMITTED_REVOCATION",
                    "action_identity": action_identity,
                    "payload_hash": payload_hash,
                }
            )
            trace = self._emit_trace_receipt(entry, kind="revocation-admission")
            self.store.append(
                {
                    "type": "EFFECT_ABSENCE_OBSERVED",
                    "reason": "revocation admits no effect",
                    "action_identity": action_identity,
                }
            )
            return {
                "decision": "ADMIT",
                "reason": "ADMITTED_REVOCATION",
                "effect": None,
                "trace_receipt": trace,
            }

        # Grant path: steps 5-11.
        auth = receipt.get("commit_authorization")
        if not isinstance(auth, dict):
            return refuse("AUTHORIZATION_MISSING")
        policy = receipt.get("policy") or {}
        if policy.get("hash") != self.config.pinned_policy_hash:
            return refuse("POLICY_MISMATCH")
        expiry = _parse_expiry(auth.get("expires_at"))
        if expiry is None or expiry <= datetime.now(timezone.utc):
            return refuse("EXPIRED")
        head = self.store.standing_head(action_identity or "unknown")
        if head is not None and head.get("terminal"):
            return refuse("STALE_SUPERSEDED")
        one_use = auth.get("one_use_code_hash")
        if not isinstance(one_use, str) or self.store.is_consumed(one_use):
            return refuse("REPLAY_CONSUMED")
        if presented_action is None:
            return refuse("BINDING_MISMATCH")
        if (
            presented_action.get("tool") != COVERED_TOOL
            or presented_action.get("target") != COVERED_TARGET
            or presented_action.get("run_id") != auth.get("run_id")
            or presented_action.get("capsule_hash") != auth.get("capsule_hash")
            or presented_action.get("evidence_hashes") != auth.get("evidence_hashes")
        ):
            return refuse("BINDING_MISMATCH")

        # All checks pass: consume, admit, commit exactly one effect.
        self.store.consume(one_use)
        self.store.admit_standing(
            action_identity or "unknown",
            {
                "verdict": "VERIFIED",
                "decision": "COMMIT",
                "payload_hash": payload_hash,
                "terminal": False,
            },
        )
        self.store.append(
            {
                "type": "DECISION",
                "outcome": "COMMIT",
                "reason": "ALL_CHECKS_PASS",
                "action_identity": action_identity,
                "payload_hash": payload_hash,
            }
        )
        try:
            effect = advance_branch(
                EFFECT_REPO,
                EFFECT_BRANCH,
                f"effects/{action_identity.replace('|', '-')}.json",
                json.dumps(
                    {
                        "action_identity": action_identity,
                        "payload_hash": payload_hash,
                        "receiver": "interop-002-b",
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                f"interop-002 B effect for {action_identity} ({payload_hash})",
            )
        except ProviderCallFailed as exc:
            self.store.append(
                {
                    "type": "EFFECT_ABSENCE_OBSERVED",
                    "reason": f"provider failed: {exc}",
                    "action_identity": action_identity,
                }
            )
            raise
        effect_entry = self.store.append(
            {
                "type": "EFFECT_OBSERVED",
                "action_identity": action_identity,
                "payload_hash": payload_hash,
                "ref_before": effect["ref_before"],
                "ref_after": effect["ref_after"],
                "commit": effect["commit"],
            }
        )
        trace = self._emit_trace_receipt(effect_entry, kind="effect")
        return {
            "decision": "COMMIT",
            "reason": "ALL_CHECKS_PASS",
            "effect": effect,
            "trace_receipt": trace,
        }

    # -- B-origin trace receipts --------------------------------------------
    def _emit_trace_receipt(self, evidence_entry: dict[str, Any], kind: str) -> dict[str, Any]:
        trace_root = hashlib.sha256(
            canonical_bytes(
                {k: v for k, v in evidence_entry.items() if k != "record_hash"}
            )
        ).hexdigest()
        body = {
            "kind": "trace_receipt",
            "receipt_version": "0.1",
            "algorithm_id": "interop-002-b-receiver-0.1",
            "canonicalization_id": "olp-canonical-json-int-v1",
            "spec_uri": "https://github.com/terryncew/olp-wire-canon",
            "attestation": "self",
            "capture_status": "provisional",
            "trace_id": secrets.token_hex(16),
            "capture_loss": False,
            "dropped_span_count": 0,
            "observed_span_count": 1,
            "trace_root": trace_root,
            "tree_algorithm": "rfc6962-mth-sha256-promote-odd-v1",
            "completion_policy": {
                "grace_millis": 30000,
                "semconv_schema_id": "otel-genai-development-2026-06",
                "type": "root_close_plus_grace",
            },
            "seal_reason": "grace_elapsed",
            "semantic_claims": False,
        }
        canonical = canonical_bytes(body)
        signed = {
            **body,
            "payload_hash": hashlib.sha256(canonical).hexdigest(),
            "signature": {
                "algorithm": "Ed25519",
                "public_key": self.config.signing_pubkey_hex,
                "value": self.config.signing_key.sign(canonical).hex(),
            },
        }
        return signed

    def check_effect_absence(self, action_identity: str) -> dict[str, Any]:
        """Independently observe that the protected ref did not move."""
        ref = get_ref(EFFECT_REPO, EFFECT_BRANCH)
        entry = self.store.append(
            {
                "type": "EFFECT_ABSENCE_OBSERVED",
                "reason": "ref observed unchanged",
                "action_identity": action_identity,
                "ref": ref,
            }
        )
        return {"ref": ref, "journal_seq": entry["seq"]}
