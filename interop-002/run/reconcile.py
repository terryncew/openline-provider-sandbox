"""Independent reconciliation for INDEPENDENT-INTEROP-002.

Re-derives authenticity, standing, decisions, and effect evidence from the
frozen artifacts + B's journal WITHOUT importing any B internals.
Canonicalization is re-implemented here from the SPEC (ASCII sort,
no-whitespace, ensure_ascii string encoding) so agreement is independent.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ROOT = Path(__file__).resolve().parents[1]
A_ART = ROOT / "a_side" / "artifacts"
RUN = ROOT / "run"
STATE = ROOT / "b_cleanroom" / "state"

PINNED_ISSUER = "9647b78a4f5423024f83de0c12fbe9ec5275e8d23a2fda83014d43cdf89fd176"
B_PUBKEY = "3039ba5c07f087918c8a687ebe78598f1b007212d72113916a92566a3f96bf6e"
EFFECT_REPO = "terryncew/openline-provider-sandbox"
EFFECT_BRANCH = "interop-002-effect"

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(("PASS " if cond else "FAIL ") + name + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(name)


def canon(value) -> bytes:
    if value is None:
        return b"null"
    if value is True:
        return b"true"
    if value is False:
        return b"false"
    if isinstance(value, int):
        return str(value).encode()
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    if isinstance(value, list):
        return b"[" + b",".join(canon(v) for v in value) + b"]"
    if isinstance(value, dict):
        items = sorted(value.items(), key=lambda kv: kv[0])
        return b"{" + b",".join(
            json.dumps(k, ensure_ascii=True).encode("ascii") + b":" + canon(v)
            for k, v in items
        ) + b"}"
    raise ValueError(type(value))


def load_receipt(path: Path) -> dict:
    return json.loads(path.read_text())


def verify_a_receipt(path: Path) -> dict:
    r = load_receipt(path)
    body = {k: v for k, v in r.items() if k not in ("payload_hash", "signature")}
    cb = canon(body)
    h_ok = r["payload_hash"] == hashlib.sha256(cb).hexdigest()
    sig = r["signature"]
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(PINNED_ISSUER)).verify(
            bytes.fromhex(sig["value"]), cb
        )
        s_ok = sig["public_key"] == PINNED_ISSUER
    except Exception:
        s_ok = False
    return {"hash_ok": h_ok, "sig_ok": s_ok, "verdict": r["verdict"],
            "decision": r["decision"], "action_id": r["action"]["id"],
            "payload_hash": r["payload_hash"]}


def main() -> int:
    # 1. A-origin authenticity, re-derived.
    y1 = verify_a_receipt(A_ART / "Y1-receipt.json")
    y2 = verify_a_receipt(A_ART / "Y2-receipt.json")
    y2d = verify_a_receipt(A_ART / "Y2-DENY-receipt.json")
    y3 = verify_a_receipt(A_ART / "Y3-receipt.json")
    for name, v in (("Y1", y1), ("Y2", y2), ("Y2-DENY", y2d), ("Y3", y3)):
        check(f"A {name} genuine (hash+sig)", v["hash_ok"] and v["sig_ok"])
    check("A Y2-DENY pairing is (REJECTED, DENY)",
          (y2d["verdict"], y2d["decision"]) == ("REJECTED", "DENY"))
    check("A Y2-DENY commit_authorization null",
          load_receipt(A_ART / "Y2-DENY-receipt.json")["commit_authorization"] is None)

    # 2. Journal chain integrity, re-derived.
    prev = "GENESIS"
    seq = 0
    entries = []
    for line in (STATE / "journal.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        e = json.loads(line)
        seq += 1
        body = {k: v for k, v in e.items() if k != "record_hash"}
        h = hashlib.sha256(canon(body)).hexdigest()
        if e.get("seq") != seq or e.get("prev_hash") != prev or h != e["record_hash"]:
            check(f"journal chain seq {seq}", False, "break or hash mismatch")
            break
        prev = e["record_hash"]
        entries.append(e)
    else:
        check(f"journal hash chain intact ({seq} records)", True)

    # 3. Standing re-derived from the standing ledger file, cross-checked
    #    against journal DECISION records. (Correction, recorded: B journals
    #    STANDING records only for revocation admissions; COMMIT admissions
    #    live in the ledger file. The ledger is B-produced evidence; the
    #    cross-check against DECISION records makes the re-derivation
    #    independent. B itself was NOT changed post-contact.)
    ledger = json.loads((STATE / "standing.json").read_text())
    y2_heads = ledger.get("tool_call|interop-002-Y2", [])
    check("Y2 standing head is terminal DENY",
          len(y2_heads) == 1 and y2_heads[0].get("decision") == "DENY"
          and y2_heads[0].get("terminal") is True
          and y2_heads[0].get("payload_hash") == y2d["payload_hash"])
    y1_heads = ledger.get("tool_call|interop-002-Y1", [])
    y3_heads = ledger.get("tool_call|interop-002-Y3", [])
    check("Y1/Y3 standing heads are COMMIT (not terminal)",
          len(y1_heads) == 1 and y1_heads[0].get("decision") == "COMMIT"
          and y1_heads[0].get("terminal") is False
          and y1_heads[0].get("payload_hash") == y1["payload_hash"]
          and len(y3_heads) == 1 and y3_heads[0].get("decision") == "COMMIT"
          and y3_heads[0].get("terminal") is False
          and y3_heads[0].get("payload_hash") == y3["payload_hash"])
    admit_decisions = [(e["action_identity"], e["reason"]) for e in entries
                       if e["type"] == "DECISION" and e["outcome"] in ("COMMIT", "ADMIT")]
    check("every ledger admission has a matching journal DECISION",
          ("tool_call|interop-002-Y1", "ALL_CHECKS_PASS") in admit_decisions
          and ("tool_call|interop-002-Y2", "ADMITTED_REVOCATION") in admit_decisions
          and ("tool_call|interop-002-Y3", "ALL_CHECKS_PASS") in admit_decisions)

    # 4. Decisions re-derived from DECISION records vs result files.
    decisions = [(e["outcome"], e["reason"]) for e in entries if e["type"] == "DECISION"]
    expected_seq = [
        ("COMMIT", "ALL_CHECKS_PASS"),        # I1
        ("REFUSE", "SIGNATURE_INVALID"),      # I2
        ("ADMIT", "ADMITTED_REVOCATION"),     # I3 deny
        ("REFUSE", "STALE_SUPERSEDED"),       # I3 stale
        ("REFUSE", "REPLAY_CONSUMED"),        # I4
        ("COMMIT", "ALL_CHECKS_PASS"),        # I5
    ]
    check("decision sequence matches preregistration",
          decisions == expected_seq, f"{decisions}")

    # 5. Effect evidence: journal EFFECT_OBSERVED vs provider.
    #    Refusals (I2, I3-stale, I4) carry no EFFECT_ABSENCE_OBSERVED journal
    #    record in B's layout; no-effect for those steps is established
    #    provider-side: the branch must show exactly the two B-authored
    #    effect commits, in order, both accounted for by EFFECT_OBSERVED.
    #    (Correction, recorded: the first version of this script wrongly
    #    expected 4 absence records. B itself was NOT changed post-contact.)
    effects = [e for e in entries if e["type"] == "EFFECT_OBSERVED"]
    check("exactly 2 EFFECT_OBSERVED records", len(effects) == 2)
    absence = [e for e in entries if e["type"] == "EFFECT_ABSENCE_OBSERVED"]
    check("1 EFFECT_ABSENCE_OBSERVED record (I3-deny admits no effect)",
          len(absence) == 1
          and absence[0]["action_identity"] == "tool_call|interop-002-Y2")
    out = subprocess.run(
        ["gh", "api", f"repos/{EFFECT_REPO}/git/ref/heads/{EFFECT_BRANCH}",
         "--jq", ".object.sha"],
        capture_output=True, text=True, timeout=60,
    )
    provider_head = out.stdout.strip()
    check("provider ref head == journal's last EFFECT_OBSERVED ref_after",
          provider_head == effects[-1]["ref_after"] and len(provider_head) == 40,
          provider_head)
    commits = [e["commit"] for e in effects]
    check("effect commits distinct, each exactly one ref advance",
          len(set(commits)) == 2 and effects[0]["ref_after"] == effects[1]["ref_before"])
    hist = subprocess.run(
        ["gh", "api", f"repos/{EFFECT_REPO}/commits?sha={EFFECT_BRANCH}&per_page=5",
         "--jq", ".[].sha"],
        capture_output=True, text=True, timeout=60,
    )
    branch_shas = hist.stdout.strip().splitlines()
    b_shas = [c for c in commits]
    check("provider branch history shows exactly the 2 journal-recorded B commits on top",
          branch_shas[:2] == [effects[1]["commit"], effects[0]["commit"]]
          and all(s in branch_shas for s in b_shas),
          f"head={branch_shas[:3]}")

    # 6. B-origin trace receipts: trace_root binds the journal evidence entry;
    #    signature verifies under B's pubkey (independent of B's code).
    for trace_file, ev_type in (
        ("I1-result-trace-receipt.json", "EFFECT_OBSERVED"),
        ("I3-deny-result-trace-receipt.json", "STANDING"),
        ("I5-result-trace-receipt.json", "EFFECT_OBSERVED"),
    ):
        t = json.loads((RUN / trace_file).read_text())
        body = {k: v for k, v in t.items() if k not in ("payload_hash", "signature")}
        cb = canon(body)
        h_ok = t["payload_hash"] == hashlib.sha256(cb).hexdigest()
        try:
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(B_PUBKEY)).verify(
                bytes.fromhex(t["signature"]["value"]), cb)
            s_ok = t["signature"]["public_key"] == B_PUBKEY
        except Exception:
            s_ok = False
        # find the journal entry this trace commits to
        ev = next(
            (e for e in entries
             if e["type"] == ev_type and hashlib.sha256(
                 canon({k: v for k, v in e.items() if k != "record_hash"})).hexdigest()
             == t["trace_root"]),
            None,
        )
        check(f"{trace_file}: sig+hash valid, trace_root binds a journal {ev_type}",
              h_ok and s_ok and ev is not None)

    if failures:
        print(f"\nRECONCILIATION FAILED: {failures}")
        return 1
    print("\nRECONCILIATION: all checks PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
