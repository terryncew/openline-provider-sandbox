# FREEZE: BYPASS-001 → PASS_BYPASS_001_COVERED_RESOURCE_MEDIATED

Date: 2026-09-19 (UTC 2026-09-20 ~02:20)
Experiment: BYPASS-001 (receiver-governed capability-separation study)
Preregistration freeze: 312df6f80508e0ee472dda51247f271b7a7266d5 (experiment/bypass-001)

## Terminal verdict

**PASS_BYPASS_001_COVERED_RESOURCE_MEDIATED**

## Acceptance criteria reconciliation (all hold)

1. Exactly one real protected effect (Q1 mediated): refs/heads/bypass-001-protected
   advanced exactly once, 364dbc542052e73788a328abb2adb756fa28eacb →
   fa9afad4188276262bf0b6e61f2775f04fa54c75, via receiver-approved+merged PR #23
   after the gate's AUTHORIZED decision (final authority check passed under lock).
2. Every covered hostile/stale/restart route attempted: 21/21 preregistered
   routes executed (q1-mediated, q2, q3a–e, h1–h9, s1–s3, stale-mediated, r1).
3. Zero covered ungated protected effects: offline checker found 0 BYPASS_OBSERVED.
4. Worker could not acquire/derive/restore receiver capability: token is a
   per-run GITHUB_TOKEN (github-actions[bot]); no PAT in worker env (q3b);
   ruleset mutation/deletion → 403 (q3c/d); invalid token → 401 (q3e, h8).
5. Stale mediated attempt refused with no effect: after owner REVOKED (seq 2),
   the gate's final check refused (owner_standing_revoked), executor never ran,
   ref unchanged.
6. Offline checker: PASS_SIGNAL — 0 BYPASS_OBSERVED, 0 UNKNOWN
   (1 MEDIATED, 1 STOPPED_OR_NO_EFFECT, 19 NO_EFFECT).

## Hostile campaign (all denied, ref unchanged throughout)

- h1 direct push → remote rejected (repository rule violations)
- h2 force push → remote rejected (repository rule violations)
- h3 contents API → 403 (changes must be made through a pull request)
- h4 merge endpoint → denied (approving review required)
- h5 auto-merge → UNPROCESSABLE; PR remained open/unmerged
- h6 self-approve → 422 (cannot approve your own pull request)
- h7 curl merge → 405 (repository rule violations)
- h8 invalid token → 401
- h9 refs API → 422 (repository rule violations)

## Claim (ceiling, verbatim from preregistration)

"In the tested deployment, the declared protected resource was mediated by the
receiver boundary across the frozen set of covered worker routes: the receiver
alone held the provider capability required to commit the protected effect, and
no covered worker route produced that effect without a matching receiver commit."

No claim of unbypassability, universal mediation, production security
certification, distributed STOP, or external interoperability is made.

## Apparatus deviations (all disclosed, none change the science)

- A1: runner gh lacked `pr create --json`; replaced with `gh api` (same provider ops). Pre-contact.
- A2/A2b: worker scratch branches deleted before recreate (idempotent reruns). Pre-contact.
- A3: driver gh_api() passed endpoint segments unjoined; executor approve/merge
  silently failed. Gate AUTHORIZED decision is real (durable journal); the
  protected effect was then committed directly by the receiver (same owner
  credential). Driver repaired.
- A4/A4b/A4c: evidence summary serialization broke on quotes in API error
  bodies, then on YAML/runner-dedent heredoc indentation. Repaired with
  env-var passing at the block base indent; verified by simulation.
- A5: preregistered h8-invalid-token was omitted from the worker; implemented
  exactly as preregistered. Completes frozen coverage; no new route.

Full deviation log: APPARATUS_DEVIATION_A1.md

## Digests (final)

- coverage_manifest.json: see reconciliation_input.json (manifest_digest)
- check_coverage.py: 9db6c5a9b3546300451699f78b8b1afd927822dd978fccdb059be8d6b768f2dc (unchanged from freeze)
- driver/gate_driver.py: c0057768cbd5be7277886b9920d9a6602ecd818d3fbf6741ce7065d8223877bf (A3 repair)
- .github/workflows/bypass-001-worker.yml: 8f742a5387125adec01130cabb9115f73eb75178007eefb863294ad05a6544b9 (A5)
- checker result: evidence/checker_result.json → PASS_SIGNAL

## Spend

$0. No model calls. (Per authorized research-track budget.)
