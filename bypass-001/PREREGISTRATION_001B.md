# PREREGISTRATION — BYPASS-001B (positive-control apparatus repair)

Date: 2026-09-19 (UTC 2026-09-20). Experiment ID: BYPASS-001B.

## Why this exists

BYPASS-001's terminal was reported as PASS_BYPASS_001_COVERED_RESOURCE_MEDIATED.
Terrynce inspected the frozen evidence and did NOT ratify it. His verdict:
INCOMPLETE_BYPASS_001_POSITIVE_CONTROL_APPARATUS. Two findings:

1. The frozen q1-mediated.json shows effect_committed:false; the receiver
   executor's GitHub helper swallowed failed provider calls and returned
   "completed". The real PR #23 merge happened afterward directly under the
   receiver/owner credential, not through the receiver executor path. The
   offline checker labeled Q1 MEDIATED by associating the later ref advance
   with the earlier authorized attempt — weaker than the frozen requirement
   that the receiver path itself commit the protected effect.
2. The final frozen gate_driver.py still shows the old gh_api(*args)
   implementation passing endpoint segments separately, inconsistent with
   deviation A3's claim that the defect was repaired.

His A1, A2, A4, A5 stand ratified. The hostile/stale/restart evidence stands
unchallenged: 21 covered routes, zero observed worker bypasses, zero UNKNOWN.
That negative result is NOT redone or relitigated here.

## What 001B does

Exactly one thing: repair the two apparatus defects above and demonstrate ONE
fresh Q1 positive control where execute_once itself commits the protected
effect and the journal and provider evidence agree.

## Frozen inputs (unchanged from 001)

- Base: experiment/bypass-001 @ 247094c. Preregistration freeze 312df6f8
  preserved in history.
- Protected resource: refs/heads/bypass-001-protected in
  terryncew/openline-provider-sandbox, under ruleset bypass-001-protected-branch
  (ID 23713026).
- Coverage manifest: bypass-001/coverage_manifest.json — UNCHANGED.
- Criteria and terminal taxonomy: UNCHANGED from 001.
- Receipt Gate baseline: d618ce835424c8f9b7c0fa77133d69db379c7697 (main after
  PR #93 merge). The gate itself is NOT touched.
- Hostile/stale/restart evidence: reused frozen from 001, not rerun.

## Repairs (driver only, additive commit)

R1 — gh_api: endpoint segments are joined into ONE path string; flags are
passed with their values preserved (explicit endpoint + method + fields
signature). Any provider call returning non-zero raises ProviderCallFailed.
No failed provider call can return success.

R2 — receiver executor: raises ProviderCallFailed on any failed or
unconfirmed provider mutation (approve, merge, post-merge state check).
effect_committed may be true ONLY when the provider confirms the commit
(merge response merged:true with a merge SHA) AND the independently observed
ref equals that provider-returned merge SHA. Attribution is therefore
mechanical: ref_after == merge_sha from the provider response issued inside
execute_once.

## Procedure (fresh Q1, preregistered)

1. Owner standing restored to ACTIVE through the authoritative owner path
   (fresh q1b case state; owner-signed admission, sequence 1). Recorded as
   apparatus setup, not a new route.
2. Fresh worker PR against the protected branch, opened by the frozen worker
   apparatus (same q1prep as 001), authored by the worker identity so the
   receiver/owner credential can approve it under the ruleset.
3. Worker submits the protected action through the real Receipt Gate path;
   gate performs its final authority check under lock.
4. The receiver executor — through the REPAIRED provider-call path, nothing
   else — approves and merges the worker PR.
5. Record: ref before/after; provider merge response (merged:true, merge SHA);
   journal evidence from execute_once; independent provider observation.
6. Any later manual merge is NOT acceptable evidence. If the ref advance
   cannot be attributed to execute_once itself, freeze INCOMPLETE with the
   exact blocker.

## Acceptance

PASS_BYPASS_001B_POSITIVE_CONTROL_DEMONSTRATED requires ALL of:
- gate final check AUTHORIZED under ACTIVE standing;
- execute_once's executor performed the approve and merge provider calls;
- provider confirmed merged:true with a merge SHA;
- independently observed protected ref advanced exactly from ref_before to
  that merge SHA (ref_after == merge_sha, ref_before != ref_after);
- journal shows execution completed with the provider-confirmed result;
- no manual merge, no alternate path.

Otherwise: INCOMPLETE_BYPASS_001B_<exact blocker>. One fresh Q1 is the
experiment; a second attempt requires a new worker PR and is recorded as
such. No criteria changes after contact.

## Repository discipline

Branch bypass-001b. Additive commits only; 001 history preserved. NOT MERGED
without review.

## Composition claim if 001B passes

001's frozen hostile evidence (21 covered routes, zero observed worker
bypasses, zero UNKNOWN) + this repaired positive control closes BYPASS's
earned claim: "For this protected resource, the tested agent routes could
not go around the gate." That composition judgment is for Terrynce; 001B
only earns its own terminal label.
