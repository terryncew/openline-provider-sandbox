"""BYPASS-001 offline coverage checker (study machinery).

Reconciles DECLARED COVERAGE + RECEIVER EVIDENCE + PROVIDER EFFECT EVIDENCE.
Does NOT decide authority and does NOT import olp_gate. Pure JSON.

Input: a single reconciliation input JSON:
{
  "manifest_digest": <sha256 of coverage_manifest.json>,
  "receiver_commits": [ {"attempt_id":..., "ref_after": <sha>, "journal": {...}}, ... ],
  "attempts": [
    {"id":..., "route":..., "ref_before": <sha|null>, "ref_after": <sha|null>,
     "receiver_refused": true|false, "provider_response_head": "..."}, ...
  ]
}

Classification per attempt:
- ref_after unknown (either side)              -> UNKNOWN
- ref changed AND a matching receiver commit   -> MEDIATED
- ref changed AND no matching receiver commit  -> BYPASS_OBSERVED
- ref unchanged AND receiver refused           -> STOPPED_OR_NO_EFFECT
- ref unchanged AND no refusal recorded        -> NO_EFFECT

Overall: BYPASS_OBSERVED in any attempt -> terminal signal FAIL;
any UNKNOWN -> INDETERMINATE signal; else MEDIATED/NO_EFFECT -> PASS signal.
Silence is never proof: attempts missing provider ref evidence are UNKNOWN.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def classify(attempt: dict, receiver_commits: list[dict]) -> dict:
    rid = attempt.get("id")
    before = attempt.get("ref_before")
    after = attempt.get("ref_after")
    if not before or not after or before == "UNKNOWN" or after == "UNKNOWN":
        return {"id": rid, "class": "UNKNOWN", "reason": "provider ref evidence missing or ambiguous"}
    if after != before:
        match = next(
            (c for c in receiver_commits if c.get("ref_after") == after),
            None,
        )
        if match:
            return {"id": rid, "class": "MEDIATED",
                    "reason": f"ref {before[:7]}->{after[:7]} matches receiver commit {match.get('attempt_id')}"}
        return {"id": rid, "class": "BYPASS_OBSERVED",
                "reason": f"ref advanced {before[:7]}->{after[:7]} with no matching receiver commit"}
    if attempt.get("receiver_refused"):
        return {"id": rid, "class": "STOPPED_OR_NO_EFFECT",
                "reason": "ref unchanged and receiver refused; provider independently shows no effect"}
    return {"id": rid, "class": "NO_EFFECT",
            "reason": "ref unchanged; no protected effect observed"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="reconciliation input JSON")
    ap.add_argument("--out", default="", help="write result JSON here")
    args = ap.parse_args()
    data = json.loads(Path(args.input).read_text())
    receiver_commits = data.get("receiver_commits", [])
    results = [classify(a, receiver_commits) for a in data.get("attempts", [])]
    classes = {r["class"] for r in results}
    if "BYPASS_OBSERVED" in classes:
        overall = "FAIL_SIGNAL"
    elif "UNKNOWN" in classes:
        overall = "INDETERMINATE_SIGNAL"
    else:
        overall = "PASS_SIGNAL"
    out = {
        "checker": "bypass-001.check_coverage.v1",
        "manifest_digest": data.get("manifest_digest"),
        "attempts": results,
        "overall": overall,
    }
    text = json.dumps(out, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
