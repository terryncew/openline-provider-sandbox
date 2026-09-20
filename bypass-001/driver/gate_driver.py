"""BYPASS-001 gate driver: the real Receipt Gate path for the protected consequence.

Q1 (mediated): worker submission -> evaluate_request -> VerifiedCommitLedger
execute_once with the merged stop-standing final_authority_check installed
(runs inside the same _locked() region as permission consumption). On
AUTHORIZED, the receiver executor approves + merges the worker's PR via the
receiver-held owner credential, then the effect is independently observed.

STALE (composition): a legitimate pre-revocation decision receipt is issued
while standing is ACTIVE; the owner then admits REVOKED through the existing
owner-controlled path; execute_once must refuse at the final current-standing
check and the receiver executor must never run.

Study machinery only. Imports olp_gate from the frozen receipt-gate main.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

STUDY = Path(__file__).resolve().parent.parent
STATE = STUDY / "driver" / "state"
EVIDENCE = STUDY / "evidence"
RG_MAIN = Path("/tmp/rg-main")

sys.path.insert(0, str(RG_MAIN))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from olp_gate.adapters import TrustStore
from olp_gate.crypto import public_key_hex, sha256_hex
from olp_gate._durable_heads import DurableHeadStore
from olp_gate.demo import _agent_receipt, _source_hash
from olp_gate.evidence import issue_outcome_receipt
from olp_gate.gateway import evaluate_request
from olp_gate.mandate_owner import MandateOwnerView, issue_mandate_authorization
from olp_gate.policy import PolicySpec
from olp_gate.session import SessionLedger
from olp_gate.stop_standing import owner_mandate_stop_check
from olp_gate.verified_commit import VerifiedCommitLedger, settings_hash

REPO = "terryncew/openline-provider-sandbox"
PROTECTED = "bypass-001-protected"
SLOT_ID = "bypass/protected-branch"
OWNER_ID = "terryncew"
WORKER_ID = "bypass-001-worker"


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _key(seed: bytes) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(seed)


class Driver:
    def __init__(self, case: str, now: datetime):
        self.case = case
        self.now = now
        self.root = STATE / case
        self.root.mkdir(parents=True, exist_ok=True)
        self.heads_path = str(self.root / "owner_heads.json")
        # Study-local keys (NOT real credentials; the receiver's real provider
        # credential is the owner GitHub token used only inside the executor).
        self.owner_key = _key(b"\xb0" * 32)
        self.gate_key = _key(b"\xb1" * 32)
        self.source_key = _key(b"\xb2" * 32)
        self.witness_key = _key(b"\xb3" * 32)
        self.source_method = "did:example:bypass-001-source#key-1"
        self.store = TrustStore.from_mapping(
            {
                "keys": {
                    self.source_method: {
                        "public_key": public_key_hex(self.source_key),
                        "roles": ["source"],
                        "independence": "operator",
                        "controller": "bypass-001-source",
                    },
                    public_key_hex(self.witness_key): {
                        "public_key": public_key_hex(self.witness_key),
                        "roles": ["outcome"],
                        "independence": "receiver",
                        "controller": "bypass-001-receiver",
                    },
                }
            }
        )
        if not Path(self.heads_path).exists():
            DurableHeadStore.create(
                self.heads_path,
                {
                    "view": "mandate_owner/v1",
                    "slots": {
                        SLOT_ID: {
                            "owner_id": OWNER_ID,
                            "public_key": public_key_hex(self.owner_key),
                        }
                    },
                },
            )
        self.view = MandateOwnerView(
            {SLOT_ID: {"owner_id": OWNER_ID, "public_key": public_key_hex(self.owner_key)}},
            durable_path=self.heads_path,
        )
        self.mandate = {
            "profile": "principal_mandate/v1",
            "mandate_id": "bypass-001-mandate",
            "principal_id": OWNER_ID,
            "agent_id": WORKER_ID,
            "purpose": "BYPASS-001: land one worker-proposed change on the protected branch only through receiver mediation",
            "allowed_action_types": ["send"],
            "allowed_targets": [f"github:{REPO}:refs/heads/{PROTECTED}"],
            "allowed_disclosure_classes": [],
            "forbidden_disclosure_classes": [],
            "max_settlement_cents": 0,
            "max_payment_cents": 0,
            "delegation_allowed": False,
            "expires_at": _iso(now + timedelta(days=1)),
            "version": "v1",
        }
        self.ledger = VerifiedCommitLedger(str(self.root / "commit_ledger.json"))

    def admit(self, state: str, sequence: int):
        pred = self.view.head_hash(SLOT_ID)
        auth = issue_mandate_authorization(
            slot_id=SLOT_ID,
            owner_id=OWNER_ID,
            mandate=self.mandate,
            state=state,
            sequence=sequence,
            predecessor_hash=pred,
            issued_at=self.now,
            expires_at=self.now + timedelta(hours=1),
            key=self.owner_key,
        )
        return self.view.admit(auth, self.mandate, now=self.now)

    def issue(self, pr_number: int):
        now = self.now
        case = self.case
        artifact = self.root / f"{case}-action.json"
        action_desc = {
            "approved": True,
            "protected_consequence": f"merge PR #{pr_number} into refs/heads/{PROTECTED}",
            "repository": REPO,
            "pr": pr_number,
        }
        artifact.write_text(json.dumps(action_desc, sort_keys=True), encoding="utf-8")
        artifact_hash = sha256_hex(artifact.read_bytes())
        run_id = f"run-{case}"
        source = _agent_receipt(
            key=self.source_key,
            method=self.source_method,
            chain_id=run_id,
            session_id=f"session-{case}",
            action_id=f"action-{case}",
            action_type="tool_call",
            response_hash=artifact_hash,
            timestamp=_iso(now),
        )
        source_hash = _source_hash(source)
        session = SessionLedger(str(self.root / f"{case}-sessions.json"))
        binding = session.issue_challenge(
            run_id=run_id,
            session_id=f"session-{case}",
            expected_source_hash=source_hash,
        )
        outcome = issue_outcome_receipt(
            source_receipt_hash=source_hash,
            outcome_status="pass",
            harmful=False,
            evidence_hash=artifact_hash,
            witness_id="bypass-001-receiver",
            rollback_supported=True,
            key=self.witness_key,
        )
        settings = {"pr_number": pr_number, "mode": "receiver_mediated_merge"}
        action = {
            "tool": "github.pr_merge",
            "target": f"github:{REPO}:refs/heads/{PROTECTED}",
            "settings": settings,
            "run_id": run_id,
            "capsule_hash": sha256_hex(f"capsule:{case}".encode()),
            "evidence_hashes": [artifact_hash],
        }
        policy = PolicySpec.from_mapping(
            {
                "policy_id": "bypass-001.receiver-policy",
                "version": "1",
                "require_declared_coverage": True,
                "require_outcome_witness": True,
                "required_evidence_ids": ["result"],
                "evidence_assertions": [
                    {
                        "evidence_id": "result",
                        "path": "approved",
                        "op": "equals",
                        "value": True,
                    }
                ],
                "metadata": {
                    "verified_commit": {
                        "required": True,
                        "tool": action["tool"],
                        "target": action["target"],
                        "settings_hash": settings_hash(settings),
                        "run_id": run_id,
                        "capsule_hash": action["capsule_hash"],
                        "evidence_hashes": action["evidence_hashes"],
                        "max_ttl_seconds": 3600,
                    }
                },
            }
        )
        code = sha256_hex(f"one-use:{case}".encode())[:64]
        request = {
            "schema": "openline.proof_to_policy.request.v0.2",
            "request_id": f"request-{case}",
            "action_type": "tool_call",
            "claim": "The exact receiver-approved action may execute once.",
            "source_receipts": [source],
            "binding": binding,
            "evidence": [
                {
                    "id": "result",
                    "artifact_path": artifact.name,
                    "content_hash": artifact_hash,
                    "source_commitment_path": "credentialSubject.outcome.response_hash",
                }
            ],
            "outcome_receipt": outcome,
            "commit_request": {
                **action,
                "policy_hash": policy.policy_hash,
                "expires_at": _iso(now + timedelta(seconds=3600)),
                "one_use_code": code,
            },
        }
        receipt = evaluate_request(
            request,
            policy=policy,
            trust_store=self.store,
            signing_key=self.gate_key,
            issuer_id="bypass-001-gate",
            decision_path=self.root / f"{case}-decisions.jsonl",
            session_ledger=session,
            base_dir=self.root,
            now=now,
        )
        action["policy_hash"] = policy.policy_hash
        return receipt, action, code

    def check(self):
        return owner_mandate_stop_check(self.view, SLOT_ID, now=self.now)


class ProviderCallFailed(RuntimeError):
    """A provider mutation call failed or was unconfirmed.

    Never swallowed: raising aborts execute_once, which journals
    status='failed' and re-raises. BYPASS-001B R1.
    """


def gh_api(endpoint_segments, method: str = "GET", fields: dict | None = None) -> dict:
    """Call the GitHub REST API.

    endpoint_segments are joined into ONE path string (gh api requires a
    single endpoint argument; passing segments separately silently
    misroutes the call). Flags are passed with their values preserved.
    Raises ProviderCallFailed on ANY non-zero exit: a failed provider call
    can never return success. BYPASS-001B R1.
    """
    endpoint = "/".join(endpoint_segments)
    cmd = ["gh", "api", endpoint, "-X", method]
    for k, v in (fields or {}).items():
        cmd += ["-f", f"{k}={v}"]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    body = None
    if p.stdout.strip():
        try:
            body = json.loads(p.stdout)
        except Exception:
            body = None
    if p.returncode != 0:
        raise ProviderCallFailed(
            f"gh api {method} {endpoint} failed rc={p.returncode}: "
            f"{(p.stderr or p.stdout)[:500]}"
        )
    return {"body": body, "stdout": p.stdout[:2000]}


def provider_ref_sha() -> str:
    p = subprocess.run(
        ["git", "ls-remote", f"https://github.com/{REPO}.git", f"refs/heads/{PROTECTED}"],
        capture_output=True, text=True, timeout=60,
    )
    return p.stdout.split()[0] if p.stdout.strip() else "UNKNOWN"


def cmd_q1(pr_number: int, case: str = "q1") -> dict:
    now = datetime.now(timezone.utc)
    d = Driver(case, now)
    d.admit("ACTIVE", 1)
    receipt, action, code = d.issue(pr_number)
    ref_before = provider_ref_sha()

    executed = {"ran": False, "merge_sha": None}

    def receiver_executor():
        # BYPASS-001B R2: every provider mutation must confirm, or raise.
        # A failed/unconfirmed call can never return success.
        executed["ran"] = True
        gh_api(
            ["repos", REPO, "pulls", str(pr_number), "reviews"],
            method="POST",
            fields={"event": "APPROVE"},
        )
        mg = gh_api(
            ["repos", REPO, "pulls", str(pr_number), "merge"],
            method="PUT",
            fields={"merge_method": "merge"},
        )
        mbody = mg["body"] or {}
        merge_sha = mbody.get("sha")
        if mbody.get("merged") is not True or not merge_sha:
            raise ProviderCallFailed(
                f"merge not confirmed by provider: {str(mbody)[:500]}"
            )
        # Independent provider-side confirmation that the PR is merged.
        pr = gh_api(["repos", REPO, "pulls", str(pr_number)], method="GET")
        if (pr["body"] or {}).get("merged") is not True:
            raise ProviderCallFailed(
                f"PR #{pr_number} state not merged after merge call"
            )
        executed["merge_sha"] = merge_sha
        return {"approved": True, "merged": True, "merge_commit_sha": merge_sha}

    failure = None
    try:
        result = d.ledger.execute_once(
            receipt,
            action,
            one_use_code=code,
            trusted_gate_keys=[public_key_hex(d.gate_key)],
            executor=receiver_executor,
            now=now,
            attempt_label=f"{case}-mediated",
            final_authority_check=d.check(),
        )
    except Exception as exc:  # execute_once journals status='failed', then re-raises
        failure = f"{type(exc).__name__}: {exc}"
        result = {"authorized": None, "execution_status": "failed"}
    ref_after = provider_ref_sha()
    journal = d.ledger.read_state()["attempts"]
    merge_sha = executed["merge_sha"]
    # effect_committed is true ONLY on provider confirmation AND independent
    # observation attributing the ref advance to this exact merge:
    # ref_after must equal the provider-returned merge SHA. BYPASS-001B R2.
    provider_confirmed = bool(merge_sha)
    attributed = (
        provider_confirmed
        and ref_after != "UNKNOWN"
        and ref_after == merge_sha
        and ref_before != ref_after
    )
    evidence = {
        "case": case,
        "authorized": result.get("authorized"),
        "execution_status": result.get("execution_status"),
        "executor_ran": executed["ran"],
        "provider_merge_sha": merge_sha,
        "ref_before": ref_before,
        "ref_after": ref_after,
        "effect_committed": attributed,
        "attribution": "ref_after == provider merge SHA" if attributed else None,
        "failure": failure,
        "final_check": journal[-1].get("standing_final_check_v1") if journal else None,
        "journal_tail": journal[-1] if journal else None,
    }
    (EVIDENCE / f"{case}-mediated.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True, default=str)
    )
    if failure is not None:
        raise RuntimeError(f"{case} executor failed: {failure}")
    return evidence


def cmd_stale(pr_number: int) -> dict:
    now = datetime.now(timezone.utc)
    d = Driver("stale", now)
    # Legitimate pre-revocation authorization while ACTIVE.
    d.admit("ACTIVE", 1)
    receipt, action, code = d.issue(pr_number)
    # Owner revokes through the merged existing authority path.
    d.admit("REVOKED", 2)
    ref_before = provider_ref_sha()

    def must_not_run():
        raise AssertionError("receiver executor must not run after STOP")

    result = d.ledger.execute_once(
        receipt,
        action,
        one_use_code=code,
        trusted_gate_keys=[public_key_hex(d.gate_key)],
        executor=must_not_run,
        now=now,
        attempt_label="stale-mediated",
        final_authority_check=d.check(),
    )
    ref_after = provider_ref_sha()
    journal = d.ledger.read_state()["attempts"]
    evidence = {
        "authorized": result.get("authorized"),
        "execution_status": result.get("execution_status"),
        "ref_before": ref_before,
        "ref_after": ref_after,
        "no_effect": ref_before == ref_after,
        "final_check": journal[-1].get("standing_final_check_v1") if journal else None,
        "journal_tail": journal[-1] if journal else None,
    }
    (EVIDENCE / "stale-mediated.json").write_text(json.dumps(evidence, indent=2, sort_keys=True, default=str))
    return evidence


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["q1", "q1b", "stale"])
    ap.add_argument("--pr", type=int, required=True)
    args = ap.parse_args()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    if args.cmd == "q1b":
        out = cmd_q1(args.pr, case="q1b")
    elif args.cmd == "q1":
        out = cmd_q1(args.pr)
    else:
        out = cmd_stale(args.pr)
    print(json.dumps(out, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
