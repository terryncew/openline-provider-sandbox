# OpenLine provider-effect sandbox

This repository is disposable. It exists only to exercise the real GitHub PR merge boundary in OpenLine Wallet. Do not put production code, credentials, customer data, deployments, or other workflows here.

The experiment uses the already-merged Wallet adapter at `c35e7f427a26cddfc4e7d300a74b84aacc0ea64e`. It does not change Wallet's policy engine or historical receipts.

## Run

Create a repository named `terryncew/openline-provider-sandbox` and import this package into its default `main` branch. The repository must contain `SANDBOX.json` exactly as supplied. Enable GitHub Actions and allow the workflow's requested Contents and Pull requests write permissions. The workflow uses only its automatically issued, repository-scoped `GITHUB_TOKEN`; no personal access token is required.

Open Actions → **PROVIDER-EFFECT-LIVE-001** → Run workflow. Enter `RUN DISPOSABLE MERGE` in the confirmation field. No push or pull-request event triggers this workflow.

The workflow creates two fresh `olp-test-` branches from the current default-branch commit, commits one harmless text file to the head branch, and opens a PR against the disposable base. It never writes to `main`. It uses the existing Wallet live runner to revoke before dispatch, then makes one real GitHub merge request under a fresh grant and holds the successful acknowledgement while revocation and closure are exercised. It does not retry an ambiguous merge.

The run uploads public evidence even if it fails. Private signing keys and the SQLite journal remain under the runner's private temporary directory and are never uploaded. A lost hosted runner does not provide durable recovery; unresolved outcomes stay unresolved. The workflow does not delete the test branches or PR, because they are useful evidence of what happened.

The frozen test conditions are in `PREREGISTRATION.json`. The launcher records its SHA-256 in the run summary.

## What success means

A successful live result establishes one actual GitHub merge, zero merge requests in the revoked pre-dispatch arm, and closure waiting for the receiver-owned in-flight acknowledgement to finish. The final PR state and merge commit must agree with the recorded effect. This is a held-acknowledgement observation after the provider response. It does not prove that GitHub's internal queue can be cancelled, that a running request can be stopped after server acceptance, or that downstream Actions have closed.

An API rejection, transport timeout, unexpected PR state, or failed evidence check is an inconclusive result. Do not rerun the same target to make it green. Preserve the evidence and inspect the real GitHub state before deciding whether a fresh, separately preregistered experiment is warranted.

The full claim boundaries and original controlled experiment remain in the [Wallet repository](https://github.com/terryncew/openline-wallet/blob/c35e7f427a26cddfc4e7d300a74b84aacc0ea64e/PROVIDER_EFFECT_001.md). This sandbox is not a product deployment or production recovery system.
