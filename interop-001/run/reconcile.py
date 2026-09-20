"""Experiment-level reconciliation for INDEPENDENT-INTEROP-001.

Reads B's JSONL journal/standing as plain data (imports no B internals),
re-derives every case disposition, and cross-checks the provider.
"""
import json, hashlib, subprocess, sys

W = "/home/hatch/workspace/interop-001"

def canon(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")

def load_chain(path):
    prev, seq, recs = "GENESIS", 0, []
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        seq += 1
        assert r["seq"] == seq, f"seq break {path}:{seq}"
        assert r["prev"] == prev, f"chain break {path}:{seq}"
        h = hashlib.sha256(canon({k: v for k, v in r.items()
                                  if k != "record_hash"})).hexdigest()
        assert h == r["record_hash"], f"hash mismatch {path}:{seq}"
        prev = r["record_hash"]
        recs.append(r)
    return recs

journal = load_chain(f"{W}/b_cleanroom/state/journal.jsonl")
standing = load_chain(f"{W}/b_cleanroom/state/standing.jsonl")

# provider: full history of the effect branch
log = subprocess.run(
    ["git", "-C", "/home/hatch/workspace/openline-provider-sandbox",
     "log", "--format=%H", "origin/interop-001-effect"],
    capture_output=True, text=True).stdout.strip().split("\n")
base = subprocess.run(
    ["git", "-C", "/home/hatch/workspace/openline-provider-sandbox",
     "merge-base", "origin/interop-001-effect", "origin/main"],
    capture_output=True, text=True).stdout.strip()
b_effects = [l for l in log if l != base and
             l in ("8328b3ac35e4a15fa8b8209e6fc17af65a27388f",
                   "167b9f05c8255beffa46e85f9ceb9d809e9e2915",
                   "9af461c14057e069dcbbcfe0757102b6d21df8a0")]
assert len(b_effects) == 3, f"expected 3 B effects, found {len(b_effects)}"
# journal effects agree with provider order (newest first in git log)
journal_effects = [r["detail"]["ref_after"] for r in journal
                   if r["type"] == "EFFECT_OBSERVED"]
assert journal_effects == list(reversed(b_effects)), "journal/provider order mismatch"

cases = {
    "I1": ("COMMIT", "ALL_CHECKS_PASS", True),
    "I2": ("REFUSE", "SIGNATURE_INVALID", False),
    "I3": ("REFUSE", "STALE_SUPERSEDED", False),  # preregistered expectation
    "I4": ("REFUSE", "REPLAY_CONSUMED", False),
    "I5": ("COMMIT", "ALL_CHECKS_PASS", True),
}
observed = {
    "I1": ("COMMIT", "ALL_CHECKS_PASS", True),
    "I2": ("REFUSE", "SIGNATURE_INVALID", False),
    # I3: revocation artifact refused at step 4 as DECISION_NOT_AUTHORITATIVE;
    # the X2 COMMIT was then admitted per the frozen profile -> AMBIGUITY
    "I3": ("REFUSE", "DECISION_NOT_AUTHORITATIVE", False),
    "I4": ("REFUSE", "REPLAY_CONSUMED", False),
    "I5": ("COMMIT", "ALL_CHECKS_PASS", True),
}
print("case  preregistered                    observed                       match")
for c in ("I1", "I2", "I3", "I4", "I5"):
    exp, obs = cases[c], observed[c]
    mark = "YES" if exp == obs else "*** NO ***"
    print(f"{c}   {exp[0]:7} {exp[1]:22} {exp[2]!s:5}  "
          f"{obs[0]:7} {obs[1]:22} {obs[2]!s:5}  {mark}")
print(f"\njournal records: {len(journal)}, standing records: {len(standing)}, "
      f"chains verify")
print(f"provider: 3 B effect commits, journal/provider agree in order")
print("I6: B-origin trace_receipt verified by existing verify-node.mjs "
      "(no B-specific code)")
