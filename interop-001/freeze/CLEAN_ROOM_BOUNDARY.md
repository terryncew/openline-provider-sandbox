# CLEAN-ROOM BOUNDARY — INDEPENDENT-INTEROP-001 (frozen pre-contact)

Frozen: 2026-09-19. No source-list expansion after contact.

## Implementation A (OpenLine side)

- openline-receipt-gate @ d618ce835424c8f9b7c0fa77133d69db379c7697
  (current merged main; the decision-gate issuance path is used to produce
  the A-origin artifacts)
- May read/use: the full A implementation including its tests, plus the
  profile's referenced documents.

## Implementation B (clean-room side)

Location: ~/workspace/interop-001/b_cleanroom/
Runtime: ~/workspace/.venvs/interop-b (python3.12 + `cryptography` only)

### B MAY read

- freeze/INTEROP_PROFILE.md (this experiment's frozen profile)
- The source documents listed in INTEROP_PROFILE.md §2, and only those:
  olp-wire-canon SPEC.md, schemas/envelope.schema.json,
  schemas/trace-receipt.schema.json, vectors/valid/*, vectors/invalid/*,
  verify-node.mjs (as a black-box CLI only, never read as source),
  receipt-gate docs/RECEIPT_SCHEMA.md, docs/VERIFIED_COMMIT.md,
  kill-switch portable/GATE_CONTRACT.md, portable/IMPLEMENTER_CHECKLIST.md,
  portable/EVIDENCE.md, wallet README.md, wallet SECURITY.md
- Public JSON Schema / JSON Schema spec knowledge, RFC 8032 (Ed25519)
  as implemented by the generic `cryptography` library, Python stdlib docs

### B MUST NOT read or import

- openline-receipt-gate Python implementation (olp_gate/*) or its tests
- openline-kill-switch implementation sources (portable/impl-b/* etc.)
- openline-wallet implementation sources
- BYPASS implementation internals (experiment/bypass-001/*)
- olp-wire-canon reference.py, scripts/*, tests/*
- Any private notes containing algorithmic implementation details
- The A-side driver (a_side/*)

### Material separation (enforced)

- No OpenLine runtime dependency: B's venv contains only `cryptography`
  (generic crypto) + pip/setuptools/wheel. Verified by dependency audit.
- No import of OpenLine packages; no copied OpenLine files.
- Separate state machinery (B's own JSONL journal + registries).
- Separate authority-check implementation (written from the profile).
- Separate receipt parsing/verification (written from SPEC.md).
- Separate effect journal.
- Appraisal via existing independent verifiers + reconciliation script
  that does not import B internals.

### Audit procedure (Q5)

1. `grep -rn "olp_gate\|openline\|kill.switch\|wallet\|reference" b_cleanroom/`
   must show no OpenLine references except in comments naming the profile.
2. B's venv site-packages listed; no OpenLine distributions.
3. `python -c "import b_receiver"` under strace-free import check shows
   only stdlib + cryptography modules loaded.

## Source-isolation verdict

Recorded after the audit. If isolation cannot be established honestly:
INCOMPLETE_INDEPENDENT_INTEROP_001_SOURCE_ISOLATION.
