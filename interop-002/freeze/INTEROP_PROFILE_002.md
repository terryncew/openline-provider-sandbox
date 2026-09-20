# INTEROP PROFILE — INDEPENDENT-INTEROP-002 (frozen pre-contact)

Status: FROZEN. No edits after contact. 001 stays frozen as the ambiguity
that earned the repair; this profile is NOT a patch of 001.

The single intentional semantic difference from the 001 profile is the
repaired terminal-revocation (verdict, decision) pairing, taken verbatim
from the repaired contract (RECEIPT_SCHEMA.md @ e676383,
"Terminal-revocation pairing (pinned)").

## 1. Question

Does the materially independent implementation (B), built from this
repaired frozen profile without OpenLine implementation code, reach the
same preregistered consequence dispositions as OpenLine (A) — including
terminal revocation — when both consume the repaired contract?

## 2. Source documents incorporated by reference (exact versions)

- olp-wire-canon SPEC.md @ 3607996396e4a647213a4a67bc62d4ae07f998f
  (canon `olp-wire-0.1-draft`; canonicalization `olp-canonical-json-int-v1`;
  Ed25519 envelope; payload_hash; signature over canonical body bytes)
- olp-wire-canon schemas/envelope.schema.json, schemas/trace-receipt.schema.json
- olp-wire-canon vectors/valid/*, vectors/invalid/*, verify-node.mjs
  (canonicalization self-check only)
- openline-receipt-gate docs/RECEIPT_SCHEMA.md
  @ e676383f967c02f70d8a26284379d2a79e537b7c
  (v0.4 `proof_to_policy_decision_receipt` field set, INCLUDING the repaired
  "Terminal-revocation pairing (pinned)" section; file sha256
  824f9f6e051690a75a1ff8c826cc554cd7469a20e8248236676d3b86a2ee8a45.
  Pre-repair sha256 was
  2b7195a83fd1fa70de168f0f520a426208c28d29e6b90a39a0af9856dfc1d4fb.
  The repair added 32 lines and deleted 0; no other semantic surface changed.)
- openline-receipt-gate docs/VERIFIED_COMMIT.md @ d618ce8
  (commit_authorization bindings; one-use; sequential replay blocked)
- openline-kill-switch portable/GATE_CONTRACT.md,
  portable/IMPLEMENTER_CHECKLIST.md, portable/EVIDENCE.md
  @ a303796745164e3c186d7a45cc090004afdc8e7f
- openline-wallet README.md, SECURITY.md @ 687bf0d8fe2158969fcecb5c2522d8d8908856dd
- This experiment's repair conformance vectors: interop-002/vectors/
  V1-valid-revocation, V2-invalid-pairing (synthetic negative),
  V3-neighbor-commit (see vectors/VECTORS_README.md)

Explicitly excluded: Bureau scoring, x402 airlock, MCP, containment,
multi-receiver propagation, distributed consensus, wallet bundle format,
v0.2/v0.3 legacy receipts, OTel capture, amendment chains beyond continuity.

## 3. Actor roles

- Issuer (A side): the OpenLine decision gate, identified by one Ed25519
  public key pinned in B's config out-of-band (never from the receipt).
- Receiver (B): the clean-room implementation. Owns the final consequence
  check and the protected effect.
- Owner: holder of the issuer key; issues COMMIT grants and terminal DENY
  revocations.
- Presenter: untrusted transport of artifacts to B.
- Appraiser: existing independent verifiers + the experiment reconciliation
  script (imports no B internals) + direct provider observation.

## 4. Authority object

A signed v0.4 `proof_to_policy_decision_receipt` per RECEIPT_SCHEMA.md, with
`decision` in {COMMIT, DENY}.

- COMMIT grant: carries `commit_authorization` per VERIFIED_COMMIT.md.
- DENY revocation: terminal standing for the named action identity;
  `commit_authorization` is null.
- Action identity (profile rule): `action.type + "|" + action.id`
  from the receipt's plaintext `action` object.
- Terminal-revocation pairing (repaired contract, mechanically decidable):
  the valid terminal-revocation pairing is exactly
  `(verdict=REJECTED, decision=DENY)` with `commit_authorization` null.
  Contradictory pairings MUST NOT be treated as terminal revocation:
  `(VERIFIED, DENY)`, `(REJECTED, COMMIT)`, `(UNDECIDABLE, DENY)`.

## 5. Current-standing semantics

From kill-switch GATE_CONTRACT invariants and wallet
"genuine but too old to use":

- B keeps a standing ledger: per action identity, the sequence of admitted
  signed decisions. Admission order is B's monotonic sequence, never
  wall-clock.
- The current head governs. A terminal DENY head — an admitted receipt with
  the pinned pairing `(verdict=REJECTED, decision=DENY)` — means the identity
  has no current executable authority.
- An older COMMIT, however authentic, presented after a terminal DENY head
  was admitted, is refused as STALE_SUPERSEDED.
- Fresh owner action = a new signed decision under the same pinned issuer
  key. A COMMIT for a NEW action identity after a DENY for another identity
  is a successor grant, evaluated on its own merits.

## 6. Proposal binding

The signed `commit_authorization` binds (profile, tool, target,
settings_hash, run_id, capsule_hash, evidence_hashes, policy_hash,
expires_at, one_use_code_hash, action_hash, authorization_hash) per
VERIFIED_COMMIT.md. B binds the presented effect to the plaintext fields
(tool, target, run_id, capsule_hash, evidence_hashes). The `*_hash`
derivations are not specified in the public docs; B treats them as
signature-bound integrity values (opaque). Any mutation of them breaks the
signature, so tamper dispositions are unaffected. This is a stated profile
limitation, not an ambiguity: the profile does not require B to recompute
them.

## 7. B's final consequence check (fixed order)

1. Strict JSON parse (duplicate keys rejected).
2. Envelope: kind == `proof_to_policy_decision_receipt`,
   receipt_version == "0.4",
   canonicalization_id == `olp-canonical-json-int-v1`.
   Recompute canonical body bytes (body minus `payload_hash`, `signature`);
   `payload_hash` must equal SHA-256 of those bytes; Ed25519 signature must
   verify over the canonical body bytes.
   Else REFUSE / SIGNATURE_INVALID.
3. `signature.public_key` == B's pinned issuer key.
   Else REFUSE / ISSUER_NOT_PINNED.
4. Pairing rule (REPAIRED — this is the 001→002 semantic change):
   `decision` in {COMMIT, DENY}, and exactly one of:
   - `(verdict=VERIFIED, decision=COMMIT)` → grant path; continue at step 5.
   - `(verdict=REJECTED, decision=DENY)` → admit as the new terminal
     standing head for the action identity; no effect; record
     ADMITTED_REVOCATION. A DENY is never an effect grant.
   - any other (verdict, decision) combination — including (VERIFIED, DENY),
     (REJECTED, COMMIT), and any UNDECIDABLE verdict —
     → REFUSE / DECISION_NOT_AUTHORITATIVE.
5. For COMMIT: `commit_authorization` present with all bound fields.
   Else REFUSE / AUTHORIZATION_MISSING.
6. `policy.hash` == B's pinned policy hash. Else REFUSE / POLICY_MISMATCH.
7. `expires_at` parseable and in the future at check time.
   Else REFUSE / EXPIRED.
8. Current standing head for the action identity is not a terminal DENY.
   Else REFUSE / STALE_SUPERSEDED.
9. `commit_authorization.one_use_code_hash` not in B's consumed registry.
   (Consumption key = the signed hash value itself; the raw code is never
   needed by B. First presentation consumes; any second presentation of the
   same authorization refuses.) Else REFUSE / REPLAY_CONSUMED.
10. Presented action's tool/target equal the profile's covered effect;
    run_id, capsule_hash, evidence_hashes equal the authorization's
    plaintext fields. Else REFUSE / BINDING_MISMATCH.
11. All pass: consume the one-use hash, admit the standing entry, commit
    the protected effect exactly once through the provider, observe it,
    emit evidence.

## 8. Covered protected effect (the one real disposable consequence)

- `tool`: `github.ref.advance`
- `target`: `terryncew/openline-provider-sandbox:refs/heads/interop-002-effect`
- The effect = advance of that ref by exactly one B-authored commit whose
  message names the action identity and the receipt `payload_hash`.
- Effect identity = (repo, ref, new_commit_sha).
- B's provider path: every provider mutation must succeed and be confirmed
  by the provider; any failure raises and records failure (no silent
  success). Independent observation: provider ref before/after per case +
  the new commit retrievable via the provider API.

## 9. Receipt / evidence

- B keeps a hash-chained evidence journal (each record binds the previous
  record's hash; monotonic seq). Record types (kill-switch EVIDENCE.md
  semantics, B's own layout): DECISION (ADMIT/REFUSE + reason), STANDING
  (admissions, revocations), EFFECT_OBSERVED (provider SHAs),
  EFFECT_ABSENCE_OBSERVED (checked, nothing found), ORDERING (monotonic
  positions).
- Per accepted effect, B emits a signed wire-canon `trace_receipt`
  (SPEC §6.1 + schemas/trace-receipt.schema.json, shape from the valid
  vector) with `trace_root` = SHA-256 of the canonical JSON of B's
  effect-evidence record, signed with B's own Ed25519 key.
- Per admitted terminal revocation, B emits a signed wire-canon
  `trace_receipt` with `trace_root` = SHA-256 of the canonical JSON of B's
  revocation-admission record, as B-origin evidence of the shared
  revocation disposition (consumed by the existing verifier, no B-specific
  code).

## 10. Revocation / successor

- Revocation: terminal DENY per action identity = the pinned pairing
  `(verdict=REJECTED, decision=DENY)` admitted as standing head (see §5).
- Successor: fresh COMMIT with fresh `one_use_code_hash` and fresh
  `action.id` under the same pinned issuer key. B's journal distinguishes
  consumed / superseded / accepted.

## 11. Canonicalization / signature

Exactly olp-wire-canon SPEC.md §2–§4: `olp-canonical-json-int-v1`,
SHA-256 lowercase hex, Ed25519, signature over canonical body bytes.

## 12. Fail-closed

Any check failure → no effect, reason recorded. If B cannot establish
standing (journal unreadable) → no effect, recorded.

## 13. Conformance vectors (pre-contact qualification)

Repair vectors (disposition-only evaluation; no effect committed):

- V1-valid-revocation (genuine (REJECTED, DENY)): steps 1–3 pass;
  step 4 → REVOCATION_ADMITTABLE.
- V2-invalid-pairing (synthetic (VERIFIED, DENY), valid signature):
  steps 1–3 pass; step 4 → REFUSE / DECISION_NOT_AUTHORITATIVE.
- V3-neighbor-commit (genuine (VERIFIED, COMMIT)): steps 1–3 pass;
  step 4 → GRANT_PATH. (Expiry/standing/replay are live-state checks and
  are not asserted for vectors.)

Wire-canon vectors/valid/* + vectors/invalid/* remain admitted for B's
canonicalization self-check (payload_hash reproduction + signature
verification), as in 001.

## 14. Preregistered cases

Action namespace: `interop-002-Y1`, `interop-002-Y2`, `interop-002-Y3`
(fresh; no reuse of 001's X1/X2/X3 identities).

- I1 CURRENT AUTHORITY / COMMIT: A-origin signed COMMIT (fresh one-use) for
  action Y1 accepted by B; B commits exactly one protected effect;
  provider observation confirms; B's evidence + receipt appraised.
  Preregistered: COMMIT ALL_CHECKS_PASS, exactly one effect.
- I2 TAMPER: I1's receipt with a mutated bound field (action.id);
  B refuses; no effect. Preregistered: REFUSE SIGNATURE_INVALID.
- I3 TERMINAL REVOKE THEN STALE: A-origin signed DENY with the pinned
  pairing `(verdict=REJECTED, decision=DENY)` for Y2 admitted by B as the
  terminal standing head (ADMITTED_REVOCATION, no effect); the Y2 COMMIT
  then presented; B refuses STALE_SUPERSEDED at its own final check;
  no effect. Preregistered: ADMITTED_REVOCATION then REFUSE
  STALE_SUPERSEDED; ref unchanged across both steps.
  (001 preregistered the same terminal labels; 001 observed REFUSE
  DECISION_NOT_AUTHORITATIVE at the admit step because the pairing was
  unpinned. The repair is exactly what makes the preregistered labels
  reachable.)
- I4 REPLAY: I1's authorization presented a second time;
  B refuses REPLAY_CONSUMED; no effect.
- I5 SUCCESSOR: A-origin signed COMMIT with fresh one-use and fresh
  action Y3 under the same issuer key; B accepts; exactly one effect;
  journal distinguishes Y1 consumed / Y2 revoked-terminal / Y3 accepted.
  Preregistered: COMMIT ALL_CHECKS_PASS, exactly one effect.
- I6 B-ORIGIN EVIDENCE: B's own signed wire-canon `trace_receipt` for an
  accepted effect AND for the admitted Y2 revocation, consumed by the
  existing `verify-node.mjs` without B-specific code; preregistered
  disposition VALID for both.

## 15. Appraisal (B does not grade itself)

- Authenticity: B's verification per §7, re-derived by the reconciliation
  script from the artifacts + journal.
- Current standing: B's standing ledger, re-derived from admitted
  decisions.
- Decision: B's journal DECISION records.
- Effect: direct provider observation (ref before/after, commit via API).
- Receipt: `verify-node.mjs` for B's trace_receipts (I6); receipt-gate's
  own verifier as a sanity check on A receipts only (not the verdict).
- Silence is not agreement: any case whose effect/evidence cannot be
  independently reconciled → INDETERMINATE.

## 16. Terminal taxonomy

- PASS_INDEPENDENT_INTEROP_002_CONTRACT_TRAVELED
- FAIL_INDEPENDENT_INTEROP_002_SEMANTIC_DIVERGENCE
- INCOMPLETE_INDEPENDENT_INTEROP_002_PROFILE_AMBIGUITY
- INCOMPLETE_INDEPENDENT_INTEROP_002_SOURCE_ISOLATION
- INDETERMINATE_INDEPENDENT_INTEROP_002_EFFECT_OR_EVIDENCE
- INCOMPLETE_INDEPENDENT_INTEROP_002 (apparatus failure before contact)
- NO_GO_INTEROP_002_REPAIR_SCOPE_EXPANDED (repair exceeded the pairing)

## 17. Claim ceiling

"A materially independent implementation, built from the repaired frozen
interop profile without OpenLine implementation code, exchanged the tested
authority and evidence artifacts with OpenLine and reached the same
preregistered consequence dispositions."
Short: "The repaired contract traveled without the implementation."
Never: industry interoperability, third-party validation, external
adoption, arbitrary implementation portability, arbitrary receipt
compatibility, production readiness, standard compliance, OpenLine
Standard, universal authority semantics. B is "materially independent /
clean-room implementation", never "external" or "third-party".

## 18. Out-of-band pinned values (frozen pre-contact, recorded at setup)

- B's pinned issuer key:
  9647b78a4f5423024f83de0c12fbe9ec5275e8d23a2fda83014d43cdf89fd176
  (same experiment test-gate key as 001)
- B's pinned policy hash:
  dd73adab77159b7a3bafbd9c0deb1953d798f071143011464fb3e8bce0e40d01
- B's own receipt-signing key: generated by B at build, pubkey recorded in
  the pre-contact freeze record.
