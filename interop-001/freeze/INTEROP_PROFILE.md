# INTEROP PROFILE — INDEPENDENT-INTEROP-001 (frozen pre-contact)

Status: FROZEN. No edits after contact. Any needed repair freezes 001 and designs 002.

## 1. Question

Can a materially independent implementation (B), built from this profile only,
implement the consequence-authority contract and exchange artifacts with the
OpenLine implementation (A) to reach the same preregistered consequence
dispositions?

## 2. Source documents incorporated by reference (exact versions)

- olp-wire-canon SPEC.md @ 3607996396e4a647213a4a67bc62d4ae07f998f
  (canon `olp-wire-0.1-draft`; canonicalization `olp-canonical-json-int-v1`;
  Ed25519 envelope; payload_hash; signature over canonical body bytes)
- olp-wire-canon schemas/envelope.schema.json, schemas/trace-receipt.schema.json
- olp-wire-canon vectors/valid/*, vectors/invalid/*, verify-node.mjs
- openline-receipt-gate docs/RECEIPT_SCHEMA.md @ d618ce835424c8f9b7c0fa77133d69db379c7697
  (v0.4 `proof_to_policy_decision_receipt` field set)
- openline-receipt-gate docs/VERIFIED_COMMIT.md @ d618ce8
  (commit_authorization bindings; one-use; sequential replay blocked)
- openline-kill-switch portable/GATE_CONTRACT.md,
  portable/IMPLEMENTER_CHECKLIST.md, portable/EVIDENCE.md
  @ a303796745164e3c186d7a45cc090004afdc8e7f
  (authority / final-check / fail-closed / replay / evidence semantics)
- openline-wallet README.md, SECURITY.md @ 687bf0d8fe2158969fcecb5c2522d8d8908856dd
  (signed history; receiver pins identity key; genuine-but-old unusable;
  receiver owns the consequential decision)

Explicitly excluded: Bureau scoring, x402 airlock, MCP, containment,
multi-receiver propagation, distributed consensus, wallet bundle format,
v0.2/v0.3 legacy receipts, OTel capture, amendment chains beyond continuity.

Known inter-document mismatches recorded in
../inventory/SEMANTIC_INVENTORY.md §6. None blocks this profile: the profile
references only the non-conflicting parts above. Where EVIDENCE.md and the
frozen kill-switch CONTRACT.md differ on vocabulary, this profile uses
EVIDENCE.md's semantic record types with B's own field layout (EVIDENCE.md
states the layout is implementation-neutral).

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

## 5. Current-standing semantics

From kill-switch GATE_CONTRACT invariants 1, 2, 6, 10 and wallet
"genuine but too old to use":

- B keeps a standing ledger: per action identity, the sequence of admitted
  signed decisions. Admission order is B's monotonic sequence, never
  wall-clock.
- The current head governs. A terminal DENY head means the identity has no
  current executable authority.
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
4. `verdict` == VERIFIED and `decision` in {COMMIT, DENY}.
   Else REFUSE / DECISION_NOT_AUTHORITATIVE.
   - If `decision` == DENY: admit as the new standing head for the action
     identity; no effect; record ADMITTED_REVOCATION. A DENY is never an
     effect grant.
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
- `target`: `terryncew/openline-provider-sandbox:refs/heads/interop-001-effect`
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

## 10. Revocation / successor

- Revocation: terminal DENY per action identity (see §5).
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

- vectors/valid/* (6): B reproduces each `payload_hash` and verifies each
  Ed25519 signature with the embedded key.
- vectors/invalid/tampered-coherence-input-receipt.json: B rejects
  (signature).
- vectors/invalid/altered-coherence-input-disclosure.json: B rejects
  (disclosure hash mismatch against the receipt's committed hash).
- vectors/invalid/broken-chain-loss-amendment.json: B rejects
  (prev-hash discontinuity).

## 14. Preregistered cases

- I1 CURRENT AUTHORITY / COMMIT: A-origin signed COMMIT (fresh one-use) for
  action X1 accepted by B; B commits exactly one protected effect;
  provider observation confirms; B's evidence + receipt appraised.
- I2 TAMPER: I1's receipt with a mutated bound field (action.id);
  B refuses; no effect.
- I3 STALE AFTER REVOKE: A-origin signed COMMIT for fresh action X2, then
  A-origin signed DENY for X2 admitted by B; the X2 COMMIT presented;
  B refuses STALE_SUPERSEDED at its own final check; no effect.
- I4 REPLAY: I1's authorization presented a second time;
  B refuses REPLAY_CONSUMED; no effect. (Profile requires one-use/replay
  resistance per VERIFIED_COMMIT.md.)
- I5 SUCCESSOR: A-origin signed COMMIT with fresh one-use and fresh
  action X3 under the same issuer key; B accepts; exactly one effect;
  journal distinguishes X1 consumed / X2 superseded / X3 accepted.
- I6 B-ORIGIN EVIDENCE: B's own signed wire-canon `trace_receipt` for an
  accepted effect, consumed by the existing `verify-node.mjs` without
  B-specific code; preregistered disposition VALID.

## 15. Appraisal (B does not grade itself)

- Authenticity: B's verification per §7, re-derived by the reconciliation
  script from the artifacts + journal.
- Current standing: B's standing ledger, re-derived from admitted
  decisions.
- Decision: B's journal DECISION records.
- Effect: direct provider observation (ref before/after, commit via API).
- Receipt: `verify-node.mjs` for B's trace_receipt (I6); receipt-gate's
  own verifier as a sanity check on A receipts only (not the verdict).
- Silence is not agreement: any case whose effect/evidence cannot be
  independently reconciled → INDETERMINATE.

## 16. Terminal taxonomy

- PASS_INDEPENDENT_INTEROP_001_CONTRACT_TRAVELED
- FAIL_INDEPENDENT_INTEROP_001_SEMANTIC_DIVERGENCE
- INCOMPLETE_INDEPENDENT_INTEROP_001_PROFILE_AMBIGUITY
- INCOMPLETE_INDEPENDENT_INTEROP_001_SOURCE_ISOLATION
- INDETERMINATE_INDEPENDENT_INTEROP_001_EFFECT_OR_EVIDENCE

## 17. Claim ceiling

"A materially independent implementation, built from the frozen interop
profile without OpenLine implementation code, exchanged the tested
authority and evidence artifacts with OpenLine and reached the same
preregistered consequence dispositions."
Short: "The contract traveled without the implementation."
Never: industry interoperability, external adoption, third-party
validation, universal portability, standards compliance, an OpenLine
standard, production readiness. B is "independently implemented /
clean-room implementation", never "external" or "third-party".

## 18. Out-of-band pinned values (frozen pre-contact, recorded at setup)

- B's pinned issuer key: <recorded in SETUP.json at issuance>
- B's pinned policy hash: <recorded in SETUP.json at issuance>
- B's own receipt-signing key: generated by B, pubkey recorded in SETUP.json
