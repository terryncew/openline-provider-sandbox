# FREEZE — INDEPENDENT-INTEROP-002

Terminal: **PASS_INDEPENDENT_INTEROP_002_CONTRACT_TRAVELED**

Date: 2026-09-19/20. $0 spend, no model calls.

## What was tested

Whether a materially independent implementation (B), built from the
repaired frozen interop profile without OpenLine implementation code,
reaches the same preregistered consequence dispositions as OpenLine (A) —
including terminal revocation — when both consume the repaired contract.

## 001 standing (unchanged)

- 001 terminal: INCOMPLETE_INDEPENDENT_INTEROP_001_PROFILE_AMBIGUITY,
  frozen on branch study/independent-interop-001 @
  98f1b118d37d8a352eb4b7ec437e82322ea81a70 (pushed, not merged).
- The exact ambiguity that earned the repair: A produced a genuine signed
  terminal-revocation receipt `(verdict=REJECTED, decision=DENY)` for action
  interop-001-X2 (payload_hash
  bafdb8ddbd42ce68e9af0566b9be567c7d0c01bd3f7d4ee95e10e7fbfc00baa2);
  the frozen 001 profile required `verdict==VERIFIED` for every authority
  artifact, so B refused it as DECISION_NOT_AUTHORITATIVE; the public
  documents listed verdict and decision values but pinned no
  (verdict, decision) pairing for a terminal DENY. A clean-room implementer
  could not derive the pairing from the docs alone.
- Confirmation: no 001 artifact was modified, re-read as a template for
  the pairing rule, or re-labeled. The 001 branch SHA above is unchanged.

## Contract repair (frozen before 002 contact)

- Repo: terryncew/openline-receipt-gate
- File: docs/RECEIPT_SCHEMA.md (the smallest document owning the ambiguous
  meaning: its "Verdict and enforcement are separate" section listed the
  values with no pairing pinned)
- Pre-repair sha256:
  2b7195a83fd1fa70de168f0f520a426208c28d29e6b90a39a0af9856dfc1d4fb
- Exact semantic clarification (32 insertions, 0 deletions, one file):
  new section "Terminal-revocation pairing (pinned)". A
  terminal-revocation receipt is mechanically identified by ALL of
  `decision == DENY`, `verdict == REJECTED`, `commit_authorization == null`.
  The valid pairing is exactly `(verdict=REJECTED, decision=DENY)`; a
  receiver MUST treat it as the terminal standing for the receipt's
  `action` (`action.type` + `action.id`). Contradictory pairings MUST NOT
  be treated as terminal revocation: `(VERIFIED, DENY)`, `(REJECTED,
  COMMIT)`, `(UNDECIDABLE, DENY)`. No other verdict/decision meaning
  changes; `(VERIFIED, COMMIT)` remains the grant pairing.
- Post-repair sha256:
  824f9f6e051690a75a1ff8c826cc554cd7469a20e8248236676d3b86a2ee8a45
- Repair branch: study/interop-contract-repair-002 @
  e676383f967c02f70d8a26284379d2a79e537b7c (based at d618ce8; pushed,
  NOT merged, no PR)
- Vectors added (interop-002/vectors/, frozen pre-contact, admitted by the
  002 preregistration as conformance material):
  - V1-valid-revocation: genuine A-issued (REJECTED, DENY),
    payload 5b8cbfbb06cd99ed7bb368c69bb0e7846871feef512846c82ac50f34ed8155bd
  - V2-invalid-pairing: SYNTHETIC negative vector (V1 body re-signed by
    the apparatus with verdict=VERIFIED; valid signature; the real gate
    never emits this pairing),
    payload 87f98e8b84ee34112d31ad5ef6a746f2376fb6e1929ad8cc98777a7545db1221
  - V3-neighbor-commit: genuine A-issued (VERIFIED, COMMIT),
    payload 7932a29cdee3647a06a1afb173e63eef0ddf9dfebbf0fe4d12ddad64564ccb13
- Why each change is necessary: the pairing pin is the exact gap 001
  exposed — without it two implementations cannot derive one disposition
  for a terminal DENY. The vectors are the minimum discriminating set:
  valid repaired pairing, contradictory pairing, neighboring grant.
- Why no other semantic surface changed: the edit touches only the
  verdict/decision section; authority, receipt architecture,
  canonicalization, signatures, replay, successor, effect, provider,
  kill-switch, Wallet, gate runtime, Bureau, and distributed STOP are
  byte-identical. The repair did not require more than the pairing plus
  directly necessary explanatory text — NO_GO was not triggered.

## 002 baselines

- A: openline-receipt-gate @ d618ce835424c8f9b7c0fa77133d69db379c7697
  (same A baseline as 001; pristine worktree used for all A-side minting)
- Repaired contract: docs/RECEIPT_SCHEMA.md @
  e676383f967c02f70d8a26284379d2a79e537b7c
- kill-switch @ a303796745164e3c186d7a45cc090004afdc8e7f,
  wallet @ 687bf0d8fe2158969fcecb5c2522d8d8908856dd,
  olp-wire-canon @ 3607996396e4a647213a4a67bc62d4ae07f998f
- Study branch: study/independent-interop-002 (terryncew/openline-provider-sandbox)
- Pre-contact commit: 67369b341a72dc4a19b80d0845ed5b81593d69f7
  (repaired profile + boundary + vectors + A driver + B; Q1–Q5 PASS)
- Source allowlist: freeze/INTEROP_PROFILE_002.md §2 documents +
  interop-002/vectors/ (admitted conformance material)
- Source denylist: olp_gate/* and its tests, kill-switch impl sources,
  wallet impl sources, bypass-001 internals, olp-wire-canon reference.py /
  scripts / tests, private notes, a_side/*, 001's B receiver logic and run
  artifacts as a template for the pairing rule. Disclosed apparatus reuse:
  001's b_cleanroom/provider.py was read to replicate the fail-loud
  provider discipline specified in profile §8 (orthogonal plumbing, not
  the semantic rule under test).

## Clean room

- Implementation B: interop-002/b_cleanroom/ — written fresh from the
  repaired 002 profile. Own modules: canon.py (SPEC §3), envelope.py,
  receiver.py (§7 fixed check order with the repaired step-4 pairing
  rule), store.py (hash-chained JSONL journal, standing ledger, one-use
  registry), provider.py (fail-loud gh ref advance), check_vectors.py,
  run_case.py.
- Dependency audit (Q5): venv site-packages contain only
  cryptography/cffi/pycparser; grep finds no olp_gate/openline/wallet/
  reference imports (one string literal names the covered-effect repo per
  the profile); loaded modules are stdlib + cryptography + b_cleanroom.
  PASS.
- Proof of no OpenLine implementation code: B's canon and envelope were
  written from SPEC.md §§2–4 and the repaired RECEIPT_SCHEMA.md; B's
  pairing rule comes verbatim from the repaired contract's pinned section;
  Q4 shows byte-identical canonical commitments with the vectors.

## Qualification (pre-contact)

- Q1: V1-valid-revocation parses and validates → REVOCATION_ADMITTABLE.
  PASS.
- Q2: V2-invalid-pairing (valid signature, contradictory pairing) →
  REFUSE / DECISION_NOT_AUTHORITATIVE. The pairing check refuses it, not
  the signature check. PASS.
- Q3: V3-neighbor-commit → GRANT_PATH; grant semantics unchanged. PASS.
- Q4: B recomputes payload_hash byte-identically on 3/3 repair vectors and
  5/5 signed olp-wire-canon valid vectors; Ed25519 verifies. PASS.
- Q5: source isolation audit clean (above). PASS.

## Results (all preregistered cases agree)

| case | preregistered | observed | effect |
|------|---------------|----------|--------|
| I1 | COMMIT ALL_CHECKS_PASS, 1 effect | COMMIT ALL_CHECKS_PASS | 10fd5f7d (df23cae → 10fd5f7d) |
| I2 | REFUSE SIGNATURE_INVALID, none | REFUSE SIGNATURE_INVALID | none |
| I3 | ADMITTED_REVOCATION then REFUSE STALE_SUPERSEDED, none | ADMIT ADMITTED_REVOCATION, then REFUSE STALE_SUPERSEDED | none |
| I4 | REFUSE REPLAY_CONSUMED, none | REFUSE REPLAY_CONSUMED | none |
| I5 | COMMIT ALL_CHECKS_PASS, 1 effect | COMMIT ALL_CHECKS_PASS | 67c6e5ab (10fd5f7d → 67c6e5ab) |
| I6 | B receipts VALID by existing verifier | 3/3 trace_receipts verified by verify-node.mjs, zero B-specific code | — |

- Exact terminal-revocation disposition on A: genuine signed v0.4 receipt
  (verdict=REJECTED, decision=DENY), commit_authorization null, action
  interop-002-Y2, payload_hash
  d21faa395536fa196f1d511742e207696c4bb1324a2a3dcf4e3aa549118bef31 —
  the gate's terminal revocation of Y2's authority.
- Exact terminal-revocation disposition on B: ADMIT / ADMITTED_REVOCATION;
  Y2's standing head is the terminal DENY (no current executable
  authority); no effect; B-origin trace_receipt
  22ef039d23519e72863fbeeca98eb41657734186d1380c42681f02814c51edfd
  commits to the revocation-admission record. One shared disposition:
  Y2's authority is terminally revoked.
- A→B exchange: 4 A-origin receipts consumed by B (Y1/Y2/Y2-DENY/Y3);
  B reached the preregistered disposition for each. Independent
  appraisal: authenticity, standing, decisions, and effects re-derived by
  run/reconcile.py (imports no B internals) — all PASS.
- B→appraiser exchange: B's trace_receipts for the I1 effect, the I3
  revocation admission, and the I5 effect all verify under the existing
  verify-node.mjs with no B-specific code; each trace_root binds the
  corresponding journal evidence entry (re-derived independently).
- Journal: 10 records, hash chain intact; decision sequence
  COMMIT/REFUSE/ADMIT/REFUSE/REFUSE/COMMIT with the preregistered reasons,
  in order.

## Effect evidence

- Protected effect observations: interop-002-effect df23cae → 10fd5f7d
  (I1, action tool_call|interop-002-Y1) → 67c6e5ab (I5, action
  tool_call|interop-002-Y3). Provider confirms each ref advance exactly
  once; ref_after equals the provider-returned commit SHA; independent
  re-observation matches; each commit message names its action identity
  and receipt payload_hash.
- Refused/no-effect observations: I2, I3-stale, I4 — provider branch
  history shows exactly the two journal-recorded B commits and nothing
  else between them; no-effect established provider-side. I3-deny carries
  an EFFECT_ABSENCE_OBSERVED journal record (revocation admits no effect).
- Independent reconciliation: run/reconcile.py — all checks PASS (see
  above).

## Disclosed evidence-coverage gap (not a criterion change)

B's journal records STANDING entries only for revocation admissions, not
for COMMIT admissions (the standing ledger file carries both; the
reconciliation cross-checks the ledger against journal DECISION records).
This is a B evidence-layout limitation, disclosed here. It did not affect
any disposition, and B was NOT changed post-contact. The first version of
run/reconcile.py additionally assumed absence-journal records for every
refusal and journal STANDING records for COMMIT admissions; those
assumptions were corrected in the appraisal script (recorded in its
comments) — the criteria, profile, vectors, and B are unchanged since
the pre-contact freeze.

## Terminal

**PASS_INDEPENDENT_INTEROP_002_CONTRACT_TRAVELED**

## Claim

Strongest sentence earned: "A materially independent implementation,
built from the repaired frozen interop profile without OpenLine
implementation code, exchanged the tested authority and evidence artifacts
with OpenLine and reached the same preregistered consequence dispositions."
Short form: "The repaired contract traveled without the implementation."

Strongest tempting sentence NOT earned: any of industry interoperability,
third-party validation, external adoption, arbitrary implementation
portability, arbitrary receipt compatibility, production readiness,
standard compliance, an OpenLine Standard, or universal authority
semantics.

## Freeze

- Branch: study/independent-interop-002
  (terryncew/openline-provider-sandbox)
- Commit: <terminal freeze commit>
- PR: none. NOT MERGED (no merge conditions carried by the work order).
- Effect branch: terryncew/openline-provider-sandbox
  refs/heads/interop-002-effect (2 B commits; disposable)

NEXT: HOLMESGPT-RECEIVER-CONTACT-001 is earned.
