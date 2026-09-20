"""A-side for INDEPENDENT-INTEROP-002: issue genuine signed v0.4 decision
receipts through the real openline-receipt-gate implementation
(olp_gate.gateway.evaluate_request @ d618ce8), adapting the repo's own
issuance test harness.

Same mechanism as 001's driver; differences are mechanical only:
  - action id namespace: interop-002-*
  - covered effect branch: refs/heads/interop-002-effect
  - run id: run-interop-002
Produces, per case:
  <tag>-receipt.json  signed proof_to_policy_decision_receipt
  <tag>-action.json   the presented action bound to the authorization
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from olp_gate.adapters import TrustStore
from olp_gate.crypto import public_key_hex, sha256_hex
from olp_gate.demo import _agent_receipt, _source_hash
from olp_gate.evidence import issue_outcome_receipt
from olp_gate.gateway import evaluate_request
from olp_gate.policy import PolicySpec
from olp_gate.session import SessionLedger
from olp_gate.verified_commit import settings_hash

COVERED_TOOL = "github.ref.advance"
COVERED_TARGET = "terryncew/openline-provider-sandbox:refs/heads/interop-002-effect"
EFFECT_BRANCH = "interop-002-effect"
RUN_ID = "run-interop-002"
NAMESPACE = "interop-002"


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def shared_context(root: Path) -> dict:
    artifact = root / "shared-artifact.json"
    if not artifact.exists():
        artifact.write_text('{"approved":true,"status":"complete"}\n', encoding="utf-8")
    artifact_hash = sha256_hex(artifact.read_bytes())
    run_id = RUN_ID
    settings = {"effect": "branch advance", "ref": f"refs/heads/{EFFECT_BRANCH}"}
    capsule_hash = sha256_hex(f"capsule:{NAMESPACE}".encode())
    policy = PolicySpec.from_mapping(
        {
            "policy_id": f"{NAMESPACE}.receiver-policy",
            "version": "1",
            "require_declared_coverage": True,
            "require_outcome_witness": True,
            "required_evidence_ids": ["result"],
            "evidence_assertions": [
                {"evidence_id": "result", "path": "approved", "op": "equals", "value": True}
            ],
            "metadata": {
                "verified_commit": {
                    "required": True,
                    "tool": COVERED_TOOL,
                    "target": COVERED_TARGET,
                    "settings_hash": settings_hash(settings),
                    "run_id": run_id,
                    "capsule_hash": capsule_hash,
                    "evidence_hashes": [artifact_hash],
                    "max_ttl_seconds": 300,
                }
            },
        }
    )
    return {
        "artifact": artifact,
        "artifact_hash": artifact_hash,
        "run_id": run_id,
        "settings": settings,
        "capsule_hash": capsule_hash,
        "policy": policy,
    }


def issue(case: str, decision_kind: str, root: Path, gate_key: Ed25519PrivateKey,
          source_key: Ed25519PrivateKey, witness_key: Ed25519PrivateKey,
          source_method: str, store: TrustStore, shared: dict) -> tuple[dict, dict]:
    now = datetime.now(timezone.utc)
    action_id = f"{NAMESPACE}-{case}"
    run_id = shared["run_id"]
    artifact_hash = shared["artifact_hash"]
    settings = shared["settings"]
    policy = shared["policy"]

    source = _agent_receipt(
        key=source_key,
        method=source_method,
        chain_id=run_id,
        session_id=f"session-{case}",
        action_id=action_id,
        action_type="tool_call",
        response_hash=artifact_hash,
        timestamp=_iso(now),
    )
    source_hash = _source_hash(source)
    session = SessionLedger(root / f"{case}-{decision_kind}-sessions.json")
    binding = session.issue_challenge(
        run_id=run_id,
        session_id=f"session-{case}",
        expected_source_hash=source_hash,
    )
    harmful = decision_kind == "DENY"
    outcome = issue_outcome_receipt(
        source_receipt_hash=source_hash,
        outcome_status="pass",
        harmful=harmful,
        evidence_hash=artifact_hash,
        witness_id=f"{NAMESPACE}-receiver",
        rollback_supported=False,
        key=witness_key,
    )
    action = {
        "tool": COVERED_TOOL,
        "target": COVERED_TARGET,
        "settings": settings,
        "run_id": run_id,
        "capsule_hash": shared["capsule_hash"],
        "evidence_hashes": [artifact_hash],
    }
    code = sha256_hex(f"one-use-{NAMESPACE}-{case}-{now.isoformat()}".encode())[:64]
    expiry = now + timedelta(seconds=240)
    request = {
        "schema": "openline.proof_to_policy.request.v0.2",
        "request_id": f"request-{NAMESPACE}-{case}",
        "action_type": "tool_call",
        "claim": "The exact receiver-approved branch advance may execute once.",
        "source_receipts": [source],
        "binding": binding,
        "evidence": [
            {
                "id": "result",
                "artifact_path": shared["artifact"].name,
                "content_hash": artifact_hash,
                "source_commitment_path": "credentialSubject.outcome.response_hash",
            }
        ],
        "outcome_receipt": outcome,
        "commit_request": {
            **action,
            "policy_hash": policy.policy_hash,
            "expires_at": _iso(expiry),
            "one_use_code": code,
        },
    }
    receipt = evaluate_request(
        request,
        policy=policy,
        trust_store=store,
        signing_key=gate_key,
        issuer_id=f"{NAMESPACE}-test-gate",
        decision_path=root / f"{case}-{decision_kind}-decisions.jsonl",
        session_ledger=session,
        base_dir=root,
        now=now,
    )
    presented = dict(action)
    presented["policy_hash"] = policy.policy_hash
    return receipt, presented


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True)
    parser.add_argument("--decision-kind", required=True, choices=["COMMIT", "DENY"])
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--gate-key-file", required=True)
    parser.add_argument("--out-tag", default=None)
    args = parser.parse_args()

    root = Path(args.out_dir)
    root.mkdir(parents=True, exist_ok=True)

    key_path = Path(args.gate_key_file)
    if key_path.exists():
        gate_key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(key_path.read_text().strip()))
    else:
        gate_key = Ed25519PrivateKey.generate()
        key_path.write_text(gate_key.private_bytes_raw().hex())
    source_key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex("61" * 32))
    witness_key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex("62" * 32))
    source_method = f"did:example:{NAMESPACE}-source#key-1"
    store = TrustStore.from_mapping(
        {
            "keys": {
                source_method: {
                    "public_key": public_key_hex(source_key),
                    "roles": ["source"],
                    "independence": "operator",
                    "controller": f"{NAMESPACE}-source",
                },
                public_key_hex(witness_key): {
                    "public_key": public_key_hex(witness_key),
                    "roles": ["outcome"],
                    "independence": "receiver",
                    "controller": f"{NAMESPACE}-receiver",
                },
            }
        }
    )

    receipt, presented = issue(args.case, args.decision_kind, root, gate_key,
                               source_key, witness_key, source_method, store,
                               shared_context(root))
    (root / f"{args.out_tag or args.case}-receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    (root / f"{args.out_tag or args.case}-action.json").write_text(
        json.dumps(presented, indent=2, sort_keys=True) + "\n")

    auth = receipt.get("commit_authorization")
    print(json.dumps({
        "case": args.out_tag or args.case,
        "verdict": receipt.get("verdict"),
        "decision": receipt.get("decision"),
        "action_id": (receipt.get("action") or {}).get("id"),
        "has_commit_authorization": isinstance(auth, dict),
        "payload_hash": receipt.get("payload_hash"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
