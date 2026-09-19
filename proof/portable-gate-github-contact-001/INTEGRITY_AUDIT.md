# INTEGRITY AUDIT — PORTABLE-GATE-GITHUB-CONTACT-001

Date: 2026-09-19. Auditor: Muse (evidence-only; no new science, no reruns,
no repairs, no implementation changes).
Source of truth: ~/workspace/portable-gate-github-contact-001/ (frozen
artifacts) + portable contract at terryncew/openline-kill-switch@a303796
+ read-only live GitHub reconciliation of already-created artifacts.

Pre-audit standing: PASS_PORTABLE_GATE_GITHUB_CONTACT_001 (returned
2026-09-19, same day).

## Seal / hash verification (pre-audit)

- PREREGISTRATION.md: 1874c811eec41b55b51ba65e5a8935aa8dfba0a146b72f25ad396e1ff4f9533a — matches PRECONTACT_SEAL.md.
- BOUNDARY_ANALYSIS.md: 08cff2e2e734fd255b6f98b5df3a8fe521805ae365b6351858e4cfe27d4d1a8b — matches seal.
- evidence/evidence.jsonl: 68af081caded8cf396c0f2b130d50325830118908880e1a97ab760d50208baf2 — matches RUN_RECORD.md.
- evidence/appraisal.txt: 866c7d2882190fc5e6857108c941d1866d759176171bc9bbe576afeca9bd9fe8 — matches RUN_RECORD.md.
- Live GitHub: PR #17 closed/merged 38b8f5540d7ee45cdd3b3101a3ee2675a9d9cc68;
  PR #18 open/unmerged; PR #19 open/unmerged; PR #20 open/unmerged;
  PR #21 closed/merged ab6aa3e4cedc05567bc928be78c822ea94c83d4c.
  Sandbox main = 11df9f9f3abde1f949c0e5905eec623161c29c4e (untouched).
  experiment/portable-gate-github-contact-001 tip = ab6aa3e4, 4 ahead / 0
  behind main — NOT merged into main.
- STOP-bearing refs unmutated since the run: exp/pgc001-stopped-a3 head =
  90fa61ff44e4f3ef84180a6bd8c215127f48ce71 (stopped sentinel);
  exp/pgc001-inflight head =
  2a6e7cb2f6c3de1c72aea13e9dcbaa74803a15fe (in-flight sentinel).
  (exp/pgc001-stopped head = ae44eb1d — the documented branch reset for
  the abandoned #19 fixture attempt, not the aborted #18 sentinel.)

## AUDIT 1 — EVIDENCE FORKS

Independent re-verification (not trusting appraise.py): 25 records, all
per-record SHA-256 hashes recompute, zero dangling prev links, every
record's prev-chain reaches GENESIS. Exactly 3 fork points (two records
sharing one predecessor hash):

1. prev=5f04ab17 (STOP_EFFECTIVE, PR #18): DECISION seq 9 (fresh-process
   refusal) + GITHUB_OBSERVATION seq 9 (main-process observation).
2. prev=7ff86917 (STOP_EFFECTIVE, PR #20): DECISION seq 14 (fresh-process
   refusal) + GITHUB_OBSERVATION seq 14 (main-process observation).
3. prev=4d2010fa (ADMIT, PR #21): DISPATCH seq 18 (worker thread) +
   STOP_ISSUED seq 18 (main thread). Each branch then continues linearly
   (DISPATCH->PROVIDER_RESPONSE; STOP_ISSUED->STOP_EFFECTIVE->
   GITHUB_OBSERVATION->ARM_RESULT).

Cause: EvidenceLog cached head/seq at construction; each concurrent
writer (fresh subprocess; worker thread) incremented its own cached
counter. Both per-writer branches are internally linear; all forked
records are preserved in the file — nothing omitted.

Findings on the audit questions:

- Frozen requirement: prereg §8 says "hash-chained JSONL records"; the
  portable EVIDENCE.md (a303796) requires "Chain the records so tampering
  is detectable (each record binds the previous)." Neither requires a
  single linear chain. Predecessor binding is satisfied per record.
- Branch deletion: a fork branch CAN be removed without invalidating the
  surviving branch's hashes (each hash binds only its own prev, never its
  children). The complete bundle is NOT sealed by any pre-contact digest
  (the seal covers PREREGISTRATION.md + BOUNDARY_ANALYSIS.md only); the
  file digest 68af081c… was recorded post-contact in RUN_RECORD.md. So
  silent branch deletion is detectable only by comparing against that
  experimenter-recorded digest — a limitation of the evidence design,
  stated here, not a violation. No deletion occurred: all 25 records
  present and valid.
- Re-derivation: the appraiser re-derived every scientific fact
  (CONTROL merge SHA, STOPPED refusal+unmerged+409 probe, IN-FLIGHT
  classification, "no dispatch causally after a STOP for the same PR"
  from prev-links). The ordering basis for the terminal is GitHub's
  commit/ref state + API responses (prereg §5), not local seq numbers —
  the fork does not touch it.
- Acceptance impact: none. No explicit preregistered criterion requires
  chain linearity.

Classification: NONMATERIAL_EVIDENCE_DEVIATION.

## AUDIT 2 — OWNER-ONLY STOP

Portable contract (GATE_CONTRACT.md, a303796), invariant 1:
"Owner-controlled STOP. The worker and ordinary receivers cannot create,
clear, decrease, or restore STOP authority. Only the owner role mutates
it."

Inspection of actual credential capability and mutation paths
(gate_c.py, run_arm.py, live repo state) — not role names:

- Exactly ONE provider credential exists in the tested arrangement: the
  machine's ambient gh/git credential. It pushed the fixture branches,
  pushed every sentinel, issued every merge request, and created every
  PR. Same git identity throughout (Terrynce White
  <noreply@example.invalid>).
- The STOP-bearing refs are ordinary unprotected branches. The fixture
  path force-pushed them successfully (`git push -f origin <head>` in
  run_arm.py fixture()), proving this credential can force-update the
  STOP-bearing ref.
- The worker roles — the in-flight dispatch thread (its own
  Gate("inflight") instance) and the fresh-process stopped attempt
  (attempt_once.py) — ran with the same ambient credential.
- Gate.stop() is a method on the shared Gate class: any holder of a Gate
  instance (including the worker thread's) can call it. There is no
  capability check; "by": "owner" is a label in the evidence record.
  Owner-only STOP is enforced by driver role convention (only run_arm.py's
  owner path calls stop()), not by capability separation.
- The worker knows the pre-STOP head SHA: it is stored in the admitted
  token (state-*.json) and in the ADMIT evidence records, and the old
  commit objects exist in the local clone. A force-push restoring the
  pre-STOP head is therefore mechanically available to the worker
  credential — and would revive the old admission token, because
  merge(sha=S_old) would then succeed against head==S_old.
- It did not happen: live GitHub confirms both sentinel heads still in
  place; no extra pushes appear in evidence. But the work order is
  explicit that non-occurrence is insufficient.

Classification: OWNER_ONLY_STOP_NOT_ESTABLISHED. Not VIOLATED (no
mutation occurred), but the arrangement cannot rule it out by
capability — enforcement is code convention only. Under the work order's
stated rule ("If the worker credential could restore or mutate the
authoritative STOP state, PASS cannot survive merely because the worker
did not try"), the unqualified PASS does not survive this finding.

## AUDIT 3 — REAL PROVIDER ORDERING

Claimed mechanism re-evaluated against preserved evidence only:

- Documented API semantics: the merge endpoint's `sha` is "SHA that pull
  request head must match to allow merge"; mismatch → 409 "Head branch
  was modified."
- Bogus-sha probe (PR #5, pre-contact inspection): 409, no state change;
  PR #5 re-queried open/unmerged. CAS refuses on mismatch.
- CONTROL: merge(sha=S_C) → 200 merged:true 38b8f55; independent
  GET /pulls/17 confirms merged + merge_commit_sha match. 200 = real
  merge (response + independent state, per prereg §3).
- STOPPED: dead-token merge(sha=S_S) → 409 "Head branch was modified";
  PR #20 independently open/unmerged. Post-STOP refusal at the provider.
- IN-FLIGHT: merge(sha=S_I) → 200 merged:true ab6aa3e4; sentinel
  2a6e7cb2 landed after; independent re-query confirms PR #21 merged with
  that merge SHA. Preregistered rule maps 200 → merge-first →
  PRE_STOP_COMMIT; 409 → sentinel-first → refusal. Observations fit
  exactly one branch.

On the hard question — any preserved execution consistent with
"STOP_EFFECTIVE occurred, yet GitHub accepted an irreversible merge that
completed afterward": none, within the experiment's stated resolution.
That would require GitHub to commit merge(sha=S) with head≠S, which
contradicts the documented semantics and all three empirical CAS
observations (bogus probe, stopped probe, control admission). The
residual window is GitHub-internal check-vs-commit atomicity, which the
boundary analysis explicitly placed below the experiment's resolution
(stated bottom-turtle assumption, same class of trust as the local
stores' atomicity in implementations A/B). The audit does not claim
stronger provider atomicity than the evidence establishes.

Documentation inaccuracy (RUN_RECORD.md only; evidence JSONL is
precise): the run record says "sentinel 9ff74425... landed after GitHub
committed the merge ab6aa3e4" for the in-flight arm. 9ff74425… is
GitHub's computed test-merge SHA for PR #20's head (it appears as
merge_commit_sha on PR #20's GITHUB_OBSERVATION with merged:false), not
a sentinel. The in-flight sentinel per the STOP_EFFECTIVE record is
2a6e7cb2f6c3de1c72aea13e9dcbaa74803a15fe — confirmed live as the head
of exp/pgc001-inflight. Historical artifact left unaltered; noted here.

## AUDIT 4 — FRESH TARGET / NO-RERUN DISCIPLINE

Chronology from evidence + run record:

- PR #18: ADMIT(6) → STOP_ISSUED(7) → STOP_EFFECTIVE(8, sentinel
  3ed0c8dc) → DECISION REFUSE(9) + GITHUB_OBSERVATION(9, open/unmerged).
  Full scientific contact completed CORRECTLY: local refusal, GitHub
  unmerged, provider probe returned the expected 409. The driver then
  crashed asserting the probe (compared GitHub's string "409" to int
  409). Apparatus-only defect — after every scientific event, touching
  nothing in the scientific variable. Chain frozen as-aborted, no
  ARM_RESULT, abort documented in RUN_RECORD.md before moving on.
- PR #19: second fixture attempt. The aborted #18's head branch was
  reset to a new commit (live head ae44eb1d confirms); PR creation POST
  reported 422 but the PR was actually created; adopt-if-just-created
  logic adopted it. A DECISION record (seq 10, REFUSE,
  STOP_REQUESTED_LOCAL) was written for it, but it was never ADMITted,
  never STOPped, never ARM_RESULTed — never armed into the scientific
  run. Abandoned when fixtures moved to unique -aN branch names.
- PR #20: genuinely fresh branch exp/pgc001-stopped-a3; full stopped
  procedure under the unchanged frozen criteria with the driver bug
  fixed first: ADMIT(11) → STOP_ISSUED(12) → STOP_EFFECTIVE(13, sentinel
  90fa61ff) → DECISION(14)+GITHUB_OBSERVATION(14) → PROVIDER_PROBE(15,
  409) → ARM_RESULT(16, STOPPED_REFUSED_UNMERGED).

Against prereg §10 ("Do not rerun a failed or ambiguous target to make
it green. Freeze first. Each arm runs once against its own fresh
disposable PR"): the stopped procedure executed against two PRs, so the
letter of "runs once" is literally breached — but #18 was not failed or
ambiguous scientifically (every observed behavior matched the
preregistered expectation; there was nothing to flip green), freeze-first
was honored (#18's chain preserved as-aborted with the abort documented
before the fresh run), no verdict is claimed from #18, #19 was never
armed, and #20 is a genuinely fresh target under unmoved criteria.

Classification: NO_RERUN_DISCIPLINE_DEVIATION_NONMATERIAL. Acceptance
impact: none — the stopped verdict rests solely on PR #20.

## TERMINAL REAPPRAISAL

- The provider-boundary ordering mechanism behaved as preregistered:
  control merged, stopped refused at both the local gate and the
  provider (409), in-flight honestly classified PRE_STOP_COMMIT, every
  effect claim independently reconciled against live GitHub state.
- But the portable contract's invariant 1 (owner-controlled STOP: the
  worker cannot restore STOP authority) is a required fact for the
  experiment's question — "without weakening the contract at the
  provider boundary" — and the tested arrangement does not establish it
  (Audit 2: single shared credential, force-pushable STOP-bearing refs,
  stop() exposed on the shared class; convention-only enforcement).
- Per the work order's explicit rule, the unqualified PASS cannot
  survive on "the worker didn't try." FAIL is not earned (no post-STOP
  merge committed under the preregistered ordering). INCOMPLETE is not
  earned (the ordering question was answered; no apparatus defect blocks
  it).

Final standing: INDETERMINATE_PORTABLE_GATE_GITHUB_CONTACT_001 —
the evidence cannot establish the required owner-only-STOP fact under
the tested authority arrangement.

Strongest sentence now earned: "In the tested GitHub merge path, the
merge-`sha` compare-and-swap ordering mechanism behaved as preregistered
— one control merge committed, one stopped attempt refused at both the
local gate and the provider, one in-flight race honestly classified
PRE_STOP_COMMIT, all reconciled against independent GitHub state — but
the tested arrangement did not establish owner-only STOP by capability
(the worker role shared the owner's credential and could have restored
the pre-STOP head), so the experiment does not establish that the
portable contract survived contact unweakened."

Strongest tempting sentences NOT earned: "An independently written
receiver governed a real GitHub merge under the portable contract"
(full PASS); "OpenLine works with GitHub"; "the kill switch works on
arbitrary external providers"; "the protocol is universally portable";
"external adoption proved"; "remote effects are solved."

What would reopen it: a rerun of the same preregistered design with
genuinely separate owner/worker provider credentials (worker credential
provably incapable of pushing, force-pushing, or deleting the
STOP-bearing ref — e.g. branch protection or a read-scoped token),
re-preregistered before contact.
