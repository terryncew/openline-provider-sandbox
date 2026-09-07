# OpenLine provider-effect sandbox

This repository is disposable. It exists only to exercise the real GitHub PR merge boundary in OpenLine Wallet. Do not put production code, credentials, customer data, deployments, or other workflows here.

The experiment uses the already-merged Wallet adapter at `c35e7f427a26cddfc4e7d300a74b84aacc0ea64e`. It does not change Wallet's policy engine or historical receipts.

## Run

Create a repository named `terryncew/openline-provider-sandbox` and import this package into its default `main` branch. The repository must contain `SANDBOX.json` exactly as supplied. Enable GitHub Actions and allow the workflow's requested Contents and Pull requests write permissions. For this disposable repository, also open Settings → Actions → General → Workflow permissions, enable “Allow GitHub Actions to create and approve pull requests,” and save. GitHub disables this separate setting by default for new personal repositories. A workflow-level pull-requests: write declaration does not override it. The workflow uses only its automatically issued, repository-scoped `GITHUB_TOKEN`; no personal access token is required.

Open Actions → **PROVIDER-EFFECT-LIVE-001** → Run workflow. Enter `RUN DISPOSABLE MERGE` in the confirmation field. No push or pull-request event triggers this workflow.

The workflow creates two fresh `olp-test-` branches from the current default-branch commit, commits one harmless text file to the head branch, and opens a PR against the disposable base. It never writes to `main`. It uses the existing Wallet live runner to revoke before dispatch, then makes one real GitHub merge request under a fresh grant and holds the successful acknowledgement while revocation and closure are exercised. It does not retry an ambiguous merge.

The run uploads public evidence even if it fails. Private signing keys and the SQLite journal remain under the runner's private temporary directory and are never uploaded. A lost hosted runner does not provide durable recovery; unresolved outcomes stay unresolved. The workflow does not delete the test branches or PR, because they are useful evidence of what happened.

The frozen test conditions are in `PREREGISTRATION.json`. The launcher records its SHA-256 in the run summary.

## What success means

A successful live result establishes one actual GitHub merge, zero merge requests in the revoked pre-dispatch arm, and closure waiting for the receiver-owned in-flight acknowledgement to finish. The final PR state and merge commit must agree with the recorded effect. This is a held-acknowledgement observation after the provider response. It does not prove that GitHub's internal queue can be cancelled, that a running request can be stopped after server acceptance, or that downstream Actions have closed.

An API rejection, transport timeout, unexpected PR state, or failed evidence check is an inconclusive result. Do not rerun the same target to make it green. Preserve the evidence and inspect the real GitHub state before deciding whether a fresh, separately preregistered experiment is warranted.

The full claim boundaries and original controlled experiment remain in the [Wallet repository](https://github.com/terryncew/openline-wallet/blob/c35e7f427a26cddfc4e7d300a74b84aacc0ea64e/PROVIDER_EFFECT_001.md). This sandbox is not a product deployment or production recovery system.

## Failed attempts and recovery

Attempt 1 stopped before HTTP with PATH_INVALID. Attempt 2 created two disposable
branches and a harmless file commit, then GitHub rejected POST /pulls with 403.
Both evidence archives remain frozen; the exact run IDs and hashes are in
`proofs/provider-effect-live-001/`. Neither attempt reached the Wallet merge
frontier. Do not rerun those jobs or reuse their targets.

The next run requires the repository setting above. If GitHub still rejects
PR creation, preserve the new artifact and inspect its request ID and status.
Do not broaden the token, turn off repository protections, or retry an uncertain
mutation to obtain a green result.

The downstream verifier now checks the actual nested Wallet v1 principal/head
fields, signed receipt bindings, effect-to-closure linkage, and monotonic
held-acknowledgement timing. A controlled fixture test cannot establish a live
provider result. The real merge and independent GitHub state reconciliation
remain required before freezing a live claim.

## Attempt 3: confirmed repository permission blocker

Run `34153215260` completed all 80 pinned Wallet tests, all 25 sandbox
tests, and compilation before the live step. It created two disposable
branches and one harmless file commit. GitHub then returned HTTP 403:

    GitHub Actions is not permitted to create or approve pull requests.

The launcher incorrectly passed `status` and `request_id` keywords to an
exception constructor that accepts `details`, masking the 403 as a TypeError.
The original artifact is preserved and the exact error is recorded in
`proofs/provider-effect-live-001/attempt-3.json`. No provider merge request
was sent and no Wallet effect-closure result was obtained.

The exception contract and sanitized diagnostics are now covered by
regressions for HTTP 403, HTTP 500, secret-bearing error messages, complete
CLI failure evidence, and unexpected exceptions. These repairs do not alter
the Wallet implementation or the preregistered experiment.

**The next run is blocked on repository configuration.** In this sandbox's
Settings → Actions → General → Workflow permissions, enable
“Allow GitHub Actions to create and approve pull requests” and save.
The workflow already requests the necessary Contents and Pull requests write
permissions; those declarations cannot override this separate restriction.
Do not expand credentials, disable branch protections, or substitute a manual
merge for the controlled experiment. After confirming the setting, run a fresh
workflow with a new disposable target. If permission is still denied, retain
the new failure evidence rather than repeating the mutation.

## Attempt 5: the missing head-check boundary

Run `34154199328` passed all upstream and sandbox tests and created disposable
PR #5 successfully. The frozen Wallet discovery then waited for readiness and
returned `WalletError`. Its source rejects `mergeable_state=unstable`. Independent
GitHub reads confirmed that PR #5 is open, unmerged and conflict-free, but its
exact head has zero check runs and no commit statuses. The head was created with
`GITHUB_TOKEN`; the ordinary CI branch filters exclude `olp-test-*`, so the
required evaluation had not been produced. The original receipt remains
INCONCLUSIVE and its precise Wallet error code was not recorded.

The repair is a dedicated read-only workflow dispatched on the exact newly
created head. It runs the pinned Wallet suite, the sandbox suite, the source
pin, and compilation. The parent requires the real GitHub workflow, job, and
published check to succeed before repeating the unchanged Wallet discovery.
A failed, skipped, ambiguous, or missing check cannot authorize the merge.
The child has Contents read permission only; the parent adds Actions write
solely to dispatch that fixed workflow. No personal access token is needed.

The original `mergeable_state` rejection is not relaxed. If the provider still
reports unstable after genuine checks pass, preserve the new diagnostics and
stop. Do not invent a successful status, disable protections, use a manual
merge, or retry the old PR. The next run creates a fresh disposable target.
The only claim available remains the one actually established by the external
merge and signed closure evidence; this patch itself earns no live result.
