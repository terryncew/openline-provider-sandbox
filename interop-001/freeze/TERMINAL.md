# FREEZE — INDEPENDENT-INTEROP-001

Terminal: **INCOMPLETE_INDEPENDENT_INTEROP_001_PROFILE_AMBIGUITY**

Date: 2026-09-19/20. $0 spend, no model calls.

## What was tested

Whether a materially independent implementation (B), built from a frozen
interop profile and public documents only, could exchange authority/evidence
artifacts with the OpenLine implementation (A) and reach the same
preregistered consequence dispositions (I1–I6).

## Terminal reason

The revocation path (I3) exposed a genuine contract gap, not an
implementation defect. The frozen profile's step 4 required `verdict ==
VERIFIED` for every authority artifact. The real OpenLine gate produces a
terminal revocation as `(verdict=REJECTED, decision=DENY)` — a genuinely
signed artifact B refused as DECISION_NOT_AUTHORITATIVE per the frozen
profile. The public documents (RECEIPT_SCHEMA.md, VERIFIED_COMMIT.md) list
verdict ∈ {VERIFIED, REJECTED, UNDECIDABLE} and decision ∈ {COMMIT, ...,
DENY, ...} but pin **no (verdict, decision) pairing** for revocation
artifacts. A clean-room implementer reading only the docs cannot know
whether a DENY arrives as (VERIFIED, DENY) or (REJECTED, DENY). The
contract itself does not determine the answer — hence INCOMPLETE
(profile ambiguity), not FAIL (no implementation failed; B executed the
frozen profile exactly, and A produced a genuine artifact).

Per freeze discipline the profile was NOT patched after contact and 001
was NOT rerun. A 002 would be earned only if the revocation-pairing gap is
closed in the documents first (or a profile explicitly admits
(REJECTED, DENY) as terminal) — that is Terrynce's call.

## What survived (earned, frozen)

- I1 COMMIT: A-origin genuine signed v0.4 receipt (VERIFIED/COMMIT,
  payload cde17ec6…) verified by B from docs alone; B committed exactly
  one real protected effect itself (branch interop-001-effect
  df23caee → 8328b3ac), journal + provider agree.
- I2 TAMPER: bound field mutated → B refused SIGNATURE_INVALID; ref
  unchanged.
- I4 REPLAY: I1's authorization re-presented → B refused REPLAY_CONSUMED;
  ref unchanged.
- I5 SUCCESSOR: fresh A-origin COMMIT (new action id, new one-use) under
  the same issuer key → B accepted; exactly one effect (167b9f05 →
  9af461c1); journal distinguishes X1 consumed / X2 committed / X3
  accepted.
- I6 B-ORIGIN EVIDENCE: B's own signed wire-canon trace_receipt verified
  by the existing independent `verify-node.mjs` with no B-specific code
  (payload d21ca19f…).
- Q1–Q5 all PASS pre-contact (vectors 11/11; provider path; source
  isolation audit clean).
- The grant path traveled. The revocation path is where the contract is
  under-specified.

## Case table (reconciled)

| case | preregistered | observed | effect |
|------|---------------|----------|--------|
| I1 | COMMIT ALL_CHECKS_PASS | COMMIT ALL_CHECKS_PASS | 8328b3ac (1 commit) |
| I2 | REFUSE SIGNATURE_INVALID | REFUSE SIGNATURE_INVALID | none |
| I3 | REFUSE STALE_SUPERSEDED | REFUSE DECISION_NOT_AUTHORITATIVE | none at revoke step; X2 COMMIT later admitted per frozen profile → 167b9f05 |
| I4 | REFUSE REPLAY_CONSUMED | REFUSE REPLAY_CONSUMED | none |
| I5 | COMMIT ALL_CHECKS_PASS | COMMIT ALL_CHECKS_PASS | 9af461c1 (1 commit) |
| I6 | B receipt VALID by existing verifier | verified trace_receipt d21ca19f | — |

## Strongest sentence earned

"A materially independent implementation, built from the frozen interop
profile without OpenLine implementation code, verified genuine
OpenLine-signed authority artifacts from the public documents alone,
reached the same dispositions on the grant path (accept valid COMMIT,
refuse tamper, refuse replay, accept fresh successor), committed the real
protected effects itself with journal and provider evidence in agreement,
and produced a receipt the existing independent verifier accepted —
while the revocation path exposed that the public contract does not pin
the (verdict, decision) pairing for a terminal DENY."

## Strongest tempting sentence NOT earned

"The contract traveled without the implementation." (Full PASS not
earned: the revocation semantics did not travel unambiguously.)

## Material

- Profile: freeze/INTEROP_PROFILE.md (frozen pre-contact, unedited after)
- Clean-room boundary: freeze/CLEAN_ROOM_BOUNDARY.md
- B pre-contact freeze: freeze/B_PRECONTACT_FREEZE.json (B tree 625b7f32636eadc8)
- B implementation: b_cleanroom/ (stdlib + cryptography only; audit in freeze)
- A driver: a_side/issue_authority.py (real olp_gate.evaluate_request path)
- A artifacts: a_side/artifacts/ (X1/X2/X3 COMMIT, X2DENY, SETUP.json)
- B state: b_cleanroom/state/ (journal.jsonl, standing.jsonl, consumed.txt, config.json)
- Case results: run/I{1,2,3,4,5}-result.json, run/I3a-admit-deny.json, run/B-X3-trace-receipt.json
- Reconciliation: run/reconcile.py (no B imports; chains + provider verified)

## Baselines

- openline-receipt-gate @ d618ce835424c8f9b7c0fa77133d69db379c7697 (A)
- openline-kill-switch @ a303796745164e3c186d7a45cc090004afdc8e7f
- openline-wallet @ 687bf0d8fe2158969fcecb5c2522d8d8908856dd
- olp-wire-canon @ 3607996396e4a647213a4a67bc62d4ae07f998f
- BYPASS: closed by composition (001 hostile evidence frozen + 001B PASS)
- Effect branch: terryncew/openline-provider-sandbox refs/heads/interop-001-effect
  (3 B commits; disposable)
