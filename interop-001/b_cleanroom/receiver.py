"""B: clean-room receiver. Implements the frozen INTEROP_PROFILE.md section 7
final consequence check from the profile and its referenced public documents
only. No OpenLine implementation code is read or imported here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .canon import CanonError, canonical_json, strict_json_loads
from .envelope import EnvelopeError, sha256_hex, split_envelope, verify_envelope
from .provider import ProviderCallFailed, advance_branch, get_ref
from .store import ChainStore, ConsumedRegistry

EXPECTED_KIND = "proof_to_policy_decision_receipt"
EXPECTED_VERSION = "0.4"
EXPECTED_CANON = "olp-canonical-json-int-v1"

TERMINAL_DECISIONS = {"DENY"}
GRANT_DECISIONS = {"COMMIT"}


class ApparatusFailure(RuntimeError):
    """B itself is broken (unreadable state, provider failure). Fail closed."""


def parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class Receiver:
    def __init__(self, state_dir: str, config: dict[str, Any]):
        self.state_dir = state_dir
        self.config = config
        os.makedirs(state_dir, exist_ok=True)
        try:
            self.journal = ChainStore(os.path.join(state_dir, "journal.jsonl"))
            self.standing = ChainStore(os.path.join(state_dir, "standing.jsonl"))
            self.consumed = ConsumedRegistry(os.path.join(state_dir, "consumed.txt"))
        except Exception as exc:
            raise ApparatusFailure(f"state unreadable: {exc}") from exc
        ok, reason = self.journal.verify_chain()
        if not ok:
            raise ApparatusFailure(f"journal chain broken: {reason}")
        ok, reason = self.standing.verify_chain()
        if not ok:
            raise ApparatusFailure(f"standing chain broken: {reason}")
        try:
            self.b_key = Ed25519PrivateKey.from_private_bytes(
                bytes.fromhex(config["b_private_key"])
            )
        except Exception as exc:
            raise ApparatusFailure(f"B key unusable: {exc}") from exc

    # -- helpers ---------------------------------------------------------
    def _refuse(self, reason: str, detail: dict[str, Any] | None = None) -> dict[str, Any]:
        rec = self.journal.append(
            {"type": "DECISION", "decision": "REFUSE", "reason": reason,
             "detail": detail or {}}
        )
        return {"decision": "REFUSE", "reason": reason,
                "journal_seq": rec["seq"], "effect": None}

    def current_head(self, action_identity: str) -> dict[str, Any] | None:
        head = None
        for rec in self.standing.records():
            if rec.get("action_identity") == action_identity:
                head = rec
        return head

    # -- main entry ------------------------------------------------------
    def decide(self, receipt_text: str, action: dict[str, Any]) -> dict[str, Any]:
        # Step 1-2: envelope
        try:
            body, _canonical, signature = verify_envelope(receipt_text)
        except (EnvelopeError, CanonError) as exc:
            return self._refuse("SIGNATURE_INVALID", {"error": str(exc)})
        if body.get("kind") != EXPECTED_KIND:
            return self._refuse("SIGNATURE_INVALID", {"error": "unexpected kind"})
        if body.get("receipt_version") != EXPECTED_VERSION:
            return self._refuse("SIGNATURE_INVALID", {"error": "unexpected version"})
        if body.get("canonicalization_id") != EXPECTED_CANON:
            return self._refuse("SIGNATURE_INVALID", {"error": "unexpected canon"})

        # Step 3: issuer pin (key comes from B's config, never the receipt)
        if signature["public_key"] != self.config["pinned_issuer_key"]:
            return self._refuse("ISSUER_NOT_PINNED", {})

        # Step 4: verdict / decision
        verdict = body.get("verdict")
        decision = body.get("decision")
        action_obj = body.get("action") or {}
        action_identity = f"{action_obj.get('type')}|{action_obj.get('id')}"
        if verdict != "VERIFIED" or decision not in (GRANT_DECISIONS | TERMINAL_DECISIONS):
            return self._refuse("DECISION_NOT_AUTHORITATIVE",
                                {"verdict": verdict, "decision": decision})

        receipt_hash = sha256_hex(canonical_json(body))

        if decision in TERMINAL_DECISIONS:
            # Revocation admission: new standing head, never an effect grant.
            rec = self.standing.append(
                {"type": "STANDING", "action_identity": action_identity,
                 "decision": decision, "receipt_hash": receipt_hash,
                 "issuer": signature["public_key"]}
            )
            jrec = self.journal.append(
                {"type": "DECISION", "decision": "ADMITTED_REVOCATION",
                 "reason": "TERMINAL_HEAD_ADMITTED",
                 "detail": {"action_identity": action_identity,
                            "standing_seq": rec["seq"]}}
            )
            return {"decision": "ADMITTED_REVOCATION",
                    "reason": "TERMINAL_HEAD_ADMITTED",
                    "journal_seq": jrec["seq"], "effect": None}

        # Steps 5-10 for COMMIT
        auth = body.get("commit_authorization")
        required = {"profile", "tool", "target", "settings_hash", "run_id",
                    "capsule_hash", "evidence_hashes", "policy_hash",
                    "expires_at", "one_use_code_hash", "action_hash",
                    "authorization_hash"}
        if not isinstance(auth, dict) or not required.issubset(auth.keys()):
            return self._refuse("AUTHORIZATION_MISSING", {})

        if (body.get("policy") or {}).get("hash") != self.config["pinned_policy_hash"]:
            return self._refuse("POLICY_MISMATCH", {})

        expires_at = parse_ts(auth.get("expires_at"))
        now = datetime.now(timezone.utc)
        if expires_at is None or expires_at <= now:
            return self._refuse("EXPIRED", {"expires_at": auth.get("expires_at")})

        head = self.current_head(action_identity)
        if head is not None and head.get("decision") in TERMINAL_DECISIONS:
            return self._refuse("STALE_SUPERSEDED",
                                {"head_seq": head["seq"],
                                 "head_decision": head["decision"]})

        code_hash = auth.get("one_use_code_hash")
        if not isinstance(code_hash, str) or not code_hash:
            return self._refuse("AUTHORIZATION_MISSING", {"field": "one_use_code_hash"})
        if self.consumed.is_consumed(code_hash):
            return self._refuse("REPLAY_CONSUMED", {})

        covered = self.config["covered_effect"]
        if action.get("tool") != covered["tool"] or action.get("target") != covered["target"]:
            return self._refuse("BINDING_MISMATCH", {"effect": "tool/target"})
        for field in ("run_id", "capsule_hash", "evidence_hashes"):
            if action.get(field) != auth.get(field):
                return self._refuse("BINDING_MISMATCH", {"effect": field})

        # Step 11: commit-or-refuse in one step. Consume first, then effect.
        try:
            self.consumed.consume(code_hash)
        except ValueError:
            return self._refuse("REPLAY_CONSUMED", {"race": True})
        srec = self.standing.append(
            {"type": "STANDING", "action_identity": action_identity,
             "decision": "COMMIT", "receipt_hash": receipt_hash,
             "issuer": signature["public_key"]})
        jrec = self.journal.append(
            {"type": "DECISION", "decision": "ADMIT", "reason": "ALL_CHECKS_PASS",
             "detail": {"action_identity": action_identity,
                        "standing_seq": srec["seq"]}})

        effect_record = {
            "action_identity": action_identity,
            "receipt_hash": receipt_hash,
            "one_use_code_hash": code_hash,
            "decision_seq": jrec["seq"],
        }
        try:
            result = self._commit_effect(effect_record)
        except ProviderCallFailed as exc:
            self.journal.append(
                {"type": "DECISION", "decision": "REFUSE",
                 "reason": "EFFECT_COMMIT_FAILED",
                 "detail": {"error": str(exc)}})
            raise ApparatusFailure(f"effect commit failed: {exc}") from exc

        self.journal.append(
            {"type": "EFFECT_OBSERVED",
             "detail": {"action_identity": action_identity, **result}})
        return {"decision": "COMMIT", "reason": "ALL_CHECKS_PASS",
                "journal_seq": jrec["seq"], "effect": result}

    # -- protected effect -------------------------------------------------
    def _commit_effect(self, effect_record: dict[str, Any]) -> dict[str, Any]:
        covered = self.config["covered_effect"]
        repo = covered["repo"]
        branch = covered["branch"]
        n = effect_record["decision_seq"]
        file_path = f"interop-001/effect-{n:04d}.json"
        content = json.dumps(
            {"effect_record": effect_record,
             "receiver": "independent-interop-001-b",
             "covered_effect": {"tool": covered["tool"], "target": covered["target"]}},
            sort_keys=True, indent=2) + "\n"
        message = (
            f"interop-001: effect for {effect_record['action_identity']} "
            f"(receipt {effect_record['receipt_hash'][:12]})"
        )
        return advance_branch(repo, branch, file_path, content, message)

    # -- B-origin receipt ---------------------------------------------------
    def emit_trace_receipt(self, effect: dict[str, Any],
                           action_identity: str) -> dict[str, Any]:
        evidence_record = {
            "receiver": "independent-interop-001-b",
            "action_identity": action_identity,
            "ref_before": effect["ref_before"],
            "ref_after": effect["ref_after"],
            "commit": effect["commit"],
        }
        trace_root = sha256_hex(canonical_json(evidence_record))
        trace_id = hashlib.sha256(
            f"{action_identity}:{effect['commit']}".encode()
        ).hexdigest()[:32]
        body = {
            "kind": "trace_receipt",
            "receipt_version": "0.1",
            "algorithm_id": "interop-001-b-effect-attestation-0.1",
            "canonicalization_id": "olp-canonical-json-int-v1",
            "spec_uri": "https://github.com/terryncew/olp-wire-canon",
            "attestation": "self",
            "capture_status": "provisional",
            "trace_id": trace_id,
            "trace_root": trace_root,
            "tree_algorithm": "rfc6962-mth-sha256-promote-odd-v1",
            "observed_span_count": 1,
            "dropped_span_count": 0,
            "capture_loss": False,
            "completion_policy": {
                "type": "root_close_plus_grace",
                "grace_millis": 0,
                "semconv_schema_id": "interop-001-b-0.1",
            },
            "seal_reason": "grace_elapsed",
            "semantic_claims": False,
        }
        canonical = canonical_json(body)
        public_hex = self.b_key.public_key().public_bytes_raw().hex()
        receipt = {
            **body,
            "payload_hash": sha256_hex(canonical),
            "signature": {
                "algorithm": "Ed25519",
                "public_key": public_hex,
                "value": self.b_key.sign(canonical).hex(),
            },
        }
        self.journal.append(
            {"type": "RECEIPT_EMITTED",
             "detail": {"trace_id": trace_id,
                        "payload_hash": receipt["payload_hash"]}})
        return receipt


def _load_config(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="b_receiver")
    parser.add_argument("--state", required=True)
    parser.add_argument("--config", required=True)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_decide = sub.add_parser("decide")
    p_decide.add_argument("--receipt", required=True)
    p_decide.add_argument("--action", required=True)

    p_receipt = sub.add_parser("emit-receipt")
    p_receipt.add_argument("--effect", required=True)
    p_receipt.add_argument("--action-identity", required=True)
    p_receipt.add_argument("--out", required=True)

    args = parser.parse_args(argv)
    try:
        config = _load_config(args.config)
        receiver = Receiver(args.state, config)
    except ApparatusFailure as exc:
        print(json.dumps({"apparatus_failure": str(exc)}))
        return 2

    if args.cmd == "decide":
        with open(args.receipt, "r", encoding="utf-8") as fh:
            receipt_text = fh.read()
        with open(args.action, "r", encoding="utf-8") as fh:
            action = json.load(fh)
        try:
            result = receiver.decide(receipt_text, action)
        except ApparatusFailure as exc:
            print(json.dumps({"apparatus_failure": str(exc)}))
            return 2
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    if args.cmd == "emit-receipt":
        with open(args.effect, "r", encoding="utf-8") as fh:
            effect = json.load(fh)
        try:
            receipt = receiver.emit_trace_receipt(effect, args.action_identity)
        except ApparatusFailure as exc:
            print(json.dumps({"apparatus_failure": str(exc)}))
            return 2
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(receipt, fh, indent=2, sort_keys=True)
            fh.write("\n")
        print(json.dumps({"emitted": args.out,
                          "payload_hash": receipt["payload_hash"]}))
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
