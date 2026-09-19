# PREREGISTRATION — PORTABLE-GATE-GITHUB-CONTACT-001

Frozen: 2026-09-19, before any scientific contact.
Amending this file after contact voids the preregistration; deviations are
recorded separately, never edited in.

## 1. Baselines (verified 2026-09-19)

- Portable contract source: terryncew/openline-kill-switch, origin/main =
  a303796745164e3c186d7a45cc090004afdc8e7f. Release tag v0.1.0 still points
  at ebf2522 (unmoved). Neither is modified by this experiment.
- Provider sandbox: terryncew/openline-provider-sandbox, main =
  11df9f9f3abde1f949c0e5905eec623161c29c4e (matches the inspected SHA).
  Main branch is not branch-protected. Two stale open PRs (#5, #7, from
  2026-09-07) exist; they are not targets and are left untouched except one
  non-mutating 409 probe on #5 during inspection (re-queried: open/unmerged).
- Experiment base branch (disposable merge target, never main):
  `experiment/portable-gate-github-contact-001`, created from sandbox main
  11df9f9f. All three arm PRs target this branch. It is never merged into
  main without Terrynce's review.

## 2. Protected consequence

One real GitHub pull-request merge per arm: GitHub creating a merge commit
on `experiment/portable-gate-github-contact-001` via the merge API.

## 3. Irreversible point

GitHub's server-side creation of the merge commit during processing of
`PUT /repos/terryncew/openline-provider-sandbox/pulls/{n}/merge`.
Established by: HTTP 200 with `merged:true` and merge commit SHA, PLUS
independent confirmation via `GET /pulls/{n}` (`merged:true`,
`merge_commit_sha` set). Both required.

## 4. STOP definitions

- STOP_REQUESTED: owner issues STOP to Implementation C; durable local
  record (state.json). After this point C's local gate refuses all new
  dispatches (fail-safe fast path; safe-direction extra refusal).
- STOP_EFFECTIVE: the sentinel commit's landing on the PR head branch in
  GitHub's order, observed via API as branch head SHA == sentinel SHA.
  This is the contract's ordering point. It is distinct from STOP_REQUESTED.

## 5. Ordering mechanism

GitHub's server-side processing order of the two operations
`merge(sha=S)` and the sentinel push. Exactly one holds:

- Merge processed first (head still S at processing): effect commits →
  PRE_STOP_COMMIT (effect before STOP_EFFECTIVE), recorded honestly.
- Sentinel lands first (head = S_sentinel ≠ S at processing): 409, no
  merge → STOP-first refusal.

Ordering evidence: the API response (200+merge SHA vs 409) plus head-SHA
observations. No wall-clock causal claims. Bottom-turtle assumptions are
listed in BOUNDARY_ANALYSIS.md and not re-litigated here.

## 6. Implementation C

- Built from the portable semantic surface only (the five files at a303796:
  portable/README.md, GATE_CONTRACT.md, IMPLEMENTER_CHECKLIST.md,
  CONFORMANCE.md, EVIDENCE.md).
- FORBIDDEN for implementation guidance: openline-kill-switch/src/,
  openline-kill-switch/portable/impl-b/, OpenLine Wallet authority/gate code,
  the reference kill-switch study code, the SQLite implementation's control
  internals. The implementer does not open those trees during this task.
- Architecture: local durable gate (owner STOP state, admission tokens bound
  to (PR number, head SHA), local dispatch refusal after STOP_REQUESTED,
  hash-chained evidence) + provider-side final check (GitHub `sha` CAS inside
  the merge operation). Transport via `gh` CLI REST calls — a generic pattern
  carrying no authority/gate semantics. What was reused is recorded in the
  run record; no authority logic is reused.
- The credential is NOT destroyed or revoked at STOP. The same provider
  capability remains technically usable; what changes is permission, encoded
  as head-SHA invalidation. (If the credential itself had to be revoked, that
  would be stated instead of claiming a consequence gate.)

## 7. Arms (exact procedures)

Common fixture per arm: fresh head branch `exp/pgc001-<arm>` from the current
tip of the experiment base branch; one new file `proof/pgc001/<arm>.txt`;
PR against the experiment base branch; wait until GitHub reports
`mergeable:true` (poll; timeout → INCOMPLETE for that arm's fixture).

### CONTROL (expect: one real merge)

1. Owner standing ACTIVE. C admits token (PR_C, S_C) for the fresh,
   mergeable PR. 2. C dispatches `merge(sha=S_C, merge_method=merge)`.
3. Expect HTTP 200, `merged:true`, merge commit SHA M_C.
4. Independently query GitHub: PR merged=true, merge_commit_sha == M_C,
   base branch contains M_C. Record all.

### STOPPED (expect: refusal, no merge)

1. Fresh PR_S, head S_S, mergeable. C admits token (PR_S, S_S) — or simply
   prepares the attempt; admission while ACTIVE is legitimate either way.
2. Owner issues STOP → C records STOP_ISSUED, pushes empty sentinel commit
   to the PR head branch, observes head == sentinel SHA → records
   STOP_EFFECTIVE. If the sentinel cannot be confirmed landed, the arm is
   INCOMPLETE (apparatus), never PASS.
3. Restart C (fresh process; state reloads from state.json — restart must
   not widen authority).
4. Attempt the protected merge through C for token (PR_S, S_S): C's local
   gate must REFUSE (STOP requested). No dispatch leaves C.
5. Independently query GitHub: PR_S merged=false, state=open.
6. Provider-boundary probe (diagnostic, NOT C behavior): direct
   `merge(sha=S_S)` call → expect 409 (old token dead at the provider).
   Labeled as probe in evidence.

### IN-FLIGHT (the ordering test; outcome honestly classified either way)

1. Fresh PR_I, head S_I, mergeable. Standing ACTIVE.
2. C admits token (PR_I, S_I) and dispatches `merge(sha=S_I)` in a
   background thread (the request is legitimately underway pre-STOP).
3. Immediately: owner issues STOP → sentinel push → confirm landing.
   C does NOT retract the in-flight dispatch (previously started path
   continues; preliminary admission is non-authoritative).
4. Await the merge response. Classify by GitHub's actual order:
   - 200 + merge SHA → PRE_STOP_COMMIT (effect before STOP_EFFECTIVE).
   - 409 → STOP-first refusal.
   Either is a valid scientific outcome; the arm's value is the honest
   classification, not a particular winner.
5. Independently reconcile GitHub state (merged boolean, merge SHA or
   absence, head SHAs).

## 8. Evidence plan

C emits hash-chained JSONL records: ADMIT, DISPATCH, PROVIDER_RESPONSE,
DECISION (REFUSE), STOP_ISSUED, STOP_EFFECTIVE, GITHUB_OBSERVATION.
A separate appraiser (appraise.py) re-verifies the chain, re-queries GitHub
independently, and re-derives per-arm outcomes. For every live target the
record carries: PR number, base/head refs, expected head SHA, final merged
boolean, merge commit SHA or explicit absence, final PR state. No credential
material in evidence.

## 9. Terminal criteria

- PASS_PORTABLE_GATE_GITHUB_CONTACT_001: C built from the portable surface
  with the barrier intact; CONTROL produced one real merge; STOPPED refused
  with PR unmerged (and provider probe 409); IN-FLIGHT preserved the
  ordering property at the provider boundary with honest classification;
  independent GitHub state supports every effect claim; no criterion moved.
- FAIL_PORTABLE_GATE_GITHUB_CONTACT_001_ESCAPED: STOP_EFFECTIVE precedes the
  claimed final boundary under the §5 ordering, yet GitHub commits the merge.
- NO_GO_PORTABLE_GATE_GITHUB_CONTACT_001_NO_FINAL_BOUNDARY: not earned —
  inspection established a legitimate route (see BOUNDARY_ANALYSIS.md).
  Retained only if the `sha` primitive fails to behave as documented.
- INDETERMINATE_PORTABLE_GATE_GITHUB_CONTACT_001: provider/evidence state
  cannot establish the ordering or the consequence.
- INCOMPLETE_PORTABLE_GATE_GITHUB_CONTACT_001: credentials, workflow/
  configuration, GitHub outage, fixture defects (e.g. PR never becomes
  mergeable, sentinel cannot land), or other apparatus failures before the
  scientific question is reached.

## 10. No-rerun rule

Do not rerun a failed or ambiguous target to make it green. Freeze first.
Each arm runs once against its own fresh disposable PR.

## 11. Claim ceiling

Even on PASS, the maximum sentence is: "In the tested GitHub merge path, an
independently written receiver built from the published portable gate
contract governed one real provider consequence under the preregistered
boundary and evidence conditions." Narrow further if the result requires it
(e.g. name the `sha` CAS + head-invalidation mechanism explicitly).
