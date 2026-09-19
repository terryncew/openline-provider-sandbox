# TERMINAL — PORTABLE-GATE-GITHUB-CONTACT-001 (audited)

Post-run integrity audit completed 2026-09-19
(INTEGRITY_AUDIT.md). This file freezes the corrected terminal.

## Final standing

INDETERMINATE_PORTABLE_GATE_GITHUB_CONTACT_001

Supersedes the pre-audit return of PASS_PORTABLE_GATE_GITHUB_CONTACT_001
(2026-09-19). The provider-boundary ordering facts from the run stand;
the owner-only-STOP fact required by the portable contract's invariant 1
is not established under the tested authority arrangement (single shared
provider credential; worker role could have force-restored the pre-STOP
head). Per the audit work order, PASS cannot survive on "the worker did
not try."

## What the run established (preserved)

- CONTROL: PR #17 merged as 38b8f5540d7ee45cdd3b3101a3ee2675a9d9cc68
  under ACTIVE; independently confirmed.
- STOPPED: PR #20 — STOP_ISSUED, sentinel
  90fa61ff44e4f3ef84180a6bd8c215127f48ce71 landed (STOP_EFFECTIVE),
  fresh-process attempt refused locally, PR independently open/unmerged,
  dead-token provider probe → 409 "Head branch was modified".
- IN-FLIGHT: PR #21 — merge(sha=S) committed as
  ab6aa3e4cedc05567bc928be78c822ea94c83d4c before the sentinel
  2a6e7cb2f6c3de1c72aea13e9dcbaa74803a15fe landed → honestly classified
  PRE_STOP_COMMIT.
- Aborted/unused fixtures: PR #18 open/unmerged (apparatus abort,
  driver assertion bug, no verdict claimed); PR #19 open/unmerged
  (adopted after a 422-reporting POST, never armed).

## Strongest sentence earned

"In the tested GitHub merge path, the merge-`sha` compare-and-swap
ordering mechanism behaved as preregistered — one control merge
committed, one stopped attempt refused at both the local gate and the
provider, one in-flight race honestly classified PRE_STOP_COMMIT, all
reconciled against independent GitHub state — but the tested arrangement
did not establish owner-only STOP by capability (the worker role shared
the owner's credential and could have restored the pre-STOP head), so
the experiment does not establish that the portable contract survived
contact unweakened."

## Not earned

"An independently written receiver governed a real GitHub merge under
the portable contract." / "OpenLine works with GitHub." / "the kill
switch works on arbitrary external providers." / "the protocol is
universally portable." / "external adoption proved." / "remote effects
are solved."

## Limits

- GitHub-internal check-vs-commit atomicity is below this experiment's
  resolution (stated bottom-turtle assumption).
- Evidence chain is a documented DAG (3 fork points), not a single
  linear chain; all 25 records verify, no dangling links.
- Evidence bundle digest (68af081c…) recorded post-contact, not
  pre-sealed; branch deletion would not invalidate surviving hashes.
- What would reopen it: same preregistered design with genuinely
  separate owner/worker provider credentials (worker provably incapable
  of mutating the STOP-bearing ref), re-preregistered before contact.

## Baselines (unchanged)

- openline-kill-switch main a303796; v0.1.0 → ebf2522 (unmoved).
- provider-sandbox main 11df9f9f3abde1f949c0e5905eec623161c29c4e
  (untouched). experiment/portable-gate-github-contact-001 NOT merged.

## Spend

$0. No model calls.
