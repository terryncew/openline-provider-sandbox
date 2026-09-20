# FREEZE — BYPASS-001B POSITIVE-CONTROL REPAIR

Date: 2026-09-19 (UTC 2026-09-20).

## Terminal

PASS_BYPASS_001B_POSITIVE_CONTROL_DEMONSTRATED

## What was repaired (bypass-001b, additive; 001 history preserved)

R1 — gate_driver.py gh_api: endpoint segments are now joined into ONE path
string; flags passed with values preserved (explicit endpoint + method +
fields signature). Any non-zero provider call raises ProviderCallFailed —
a failed provider call can never return success. This implements what
deviation A3 claimed and reconciles the frozen code with the narrative.

R2 — receiver executor: raises ProviderCallFailed on any failed or
unconfirmed provider mutation (approve, merge, post-merge state check).
effect_committed is true ONLY when the provider confirms (merge response
merged:true with a merge SHA) AND the independently observed protected ref
equals that provider-returned merge SHA. The 001 failure mode — executor
returning "completed" while the provider call failed — is now impossible:
execute_once journals status='failed' and re-raises.

Commit: 103a2c3 (repair + PREREGISTRATION_001B.md), on branch bypass-001b
from 247094c. Gate, frozen verifier, coverage manifest, criteria: untouched.

Apparatus adaptation A6 (disclosed in PREREGISTRATION_001B.md): additive
`q1bprep` worker phase on main (df23cae) — the frozen q1prep marker already
existed on the protected branch after 001's merge, so q1bprep writes a
distinct 001B marker. Frozen q1prep untouched.

## Fresh Q1 (q1b), end-to-end through the repaired receiver path

- Owner standing: restored to ACTIVE through the authoritative owner path
  (fresh q1b case state; owner-signed admission, sequence 1; recorded as
  apparatus setup).
- Gate: worker mandate for PR #29 admitted; final authority check under
  lock → AUTHORIZED (standing ACTIVE, terminal false).
- execute_once: receiver executor ran the approve and merge provider calls
  itself — no manual merge, no alternate path.
- Provider evidence (independent):
  - PR #29: authored by github-actions[bot] (worker identity),
    base bypass-001-protected, head bypass-001/q1b-change, merged:true.
  - Review 5258800583: APPROVED by terryncew (receiver/owner credential).
  - Merge commit 407e26e0c46a76b7bc2368935c4de668ed0840c8, parents
    fa9afad4188276262bf0b6e61f2775f04fa54c75 (prior protected ref) and
    cd8dcc3e0372b844e990d5813f861ba3b65f1e1b (worker head).
  - Protected ref: fa9afad4188276262bf0b6e61f2775f04fa54c75
    → 407e26e0c46a76b7bc2368935c4de668ed0840c8 — advanced exactly once,
    and ref_after == the provider-returned merge SHA from the executor's
    own merge call inside execute_once.
- Journal evidence: attempt q1b-mediated, result AUTHORIZED,
  execution_status completed, tool_result_hash recorded; final standing
  check ACTIVE/allowed.
- Evidence: bypass-001/evidence/q1b-mediated.json (effect_committed:true,
  attribution "ref_after == provider merge SHA", failure:null),
  bypass-001/evidence/actions/bypass-001-evidence-q1bprep.json.

## Acceptance (from preregistration)

All six conditions held. No manual merge. No alternate path.

## Composition

001's frozen hostile evidence (21 covered routes, zero observed worker
bypasses, zero UNKNOWN) is unchanged and unchallenged. This repaired Q1
demonstrates the positive control 001 lacked: execute_once itself committed
the protected effect through the receiver executor, and journal + provider
evidence agree. Together they close BYPASS's earned claim —
"For this protected resource, the tested agent routes could not go around
the gate." — subject to Terrynce's ratification.

## Branch

bypass-001b — committed, pushed, NOT MERGED (no review).
Receipt Gate main: d618ce835424c8f9b7c0fa77133d69db379c7697 (unchanged).
$0 spend. No model calls.
