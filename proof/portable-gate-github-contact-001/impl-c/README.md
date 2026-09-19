# Implementation C — barrier compliance

Built 2026-09-19 from the portable semantic surface alone:
terryncew/openline-kill-switch@a303796 —
portable/README.md, portable/GATE_CONTRACT.md, portable/IMPLEMENTER_CHECKLIST.md,
portable/CONFORMANCE.md, portable/EVIDENCE.md.

The implementer did NOT open, import, copy, or consult for guidance:
- openline-kill-switch/src/
- openline-kill-switch/portable/impl-b/
- OpenLine Wallet authority/gate implementation
- the reference kill-switch study code
- the SQLite implementation's control internals

Reused (generic, no authority/gate semantics):
- `gh` CLI REST call pattern for GitHub transport (also visible in the
  sandbox's prior scripts; re-derived here, not copied).
- Empty-commit + push + branch-head poll as ordinary git mechanics.

Everything else — the (PR, head-SHA) authority token, STOP-as-head-
advancement, the provider-CAS-as-final-check design, the evidence vocabulary
mapping — was derived from the portable contract's twelve invariants and
GitHub's documented `sha` parameter semantics.
