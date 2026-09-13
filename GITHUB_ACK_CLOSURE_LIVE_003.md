# GITHUB-ACK-CLOSURE-LIVE-003

Status: **PREREGISTERED — no result yet**

## Why this exists

`GITHUB-ACK-CLOSURE-LIVE-002` issued exactly one real disposable GitHub merge and GitHub completed it, but the frozen receiver verdict remained `GITHUB_ACKNOWLEDGED_EFFECT_CLOSURE_UNRESOLVED`.

The failure was narrower than the merge itself. The recovered receiver still required GitHub's PR read model to expose the acknowledged merge SHA through `merge_commit_sha` before it would attribute the effect. GitHub had already acknowledged the concrete SHA, and the exact commit later existed with the expected parents, but the receiver's late path remained coupled to that lagging PR field.

Wallet `4d26040c0f8e835184ebb710356c9601842610fe` removes that dependency. Once a successful `merged=true` response with a concrete SHA is durably recorded, recovery re-checks the PR identity and reviewed head, then reads that **exact acknowledged commit directly**. The exact commit must bind the disposable base as parent 1 and the reviewed head as parent 2. A non-null contradictory PR SHA still fails closed. No merge retry is permitted.

This experiment is the final bounded real-provider test of that repair.

## Frozen source

Wallet commit:

`4d26040c0f8e835184ebb710356c9601842610fe`

Provider sandbox base at preregistration:

`9a64a5762a808b97b7a1356e36763fd48249babd`

Target repository:

`terryncew/openline-provider-sandbox`

Only disposable `olp-test-<run>-base` and `olp-test-<run>-head` refs may be mutated. The default branch is never the merge target.

## Frozen sequence

1. Validate the dedicated provider sandbox and marker.
2. Create disposable base/head refs and one harmless pull request.
3. Create a fresh Wallet, subject credential, and exact mandate for only that disposable PR merge.
4. Prepare the exact merge through `GitHubMergeReceiver`.
5. Let the receiver issue **one** GitHub merge request.
6. After GitHub returns `merged=true` with a concrete SHA and the receiver durably records it, deliberately interrupt immediate settlement with `GITHUB_MERGE_NOT_RECONCILED`.
7. Require the journal to be `UNCERTAIN`, with the acknowledged SHA preserved and exactly one merge request.
8. Shut down the receiver and construct a fresh receiver over the same journal and signing identity.
9. Run `settle_acknowledged_merges`. It may perform provider reads only.
10. Re-check PR target identity and reviewed head. Do **not** require PR `merge_commit_sha` to be populated.
11. Read the exact acknowledged commit directly and require parent 1 = frozen disposable base and parent 2 = reviewed head.
12. Require a valid signed `MERGE_CONFIRMED` effect receipt.
13. Preserve the frontier receipt in Wallet, revoke the mandate, and require a valid signed `EFFECT_CLOSED` certificate with zero active frontiers and the confirmed effect hash.
14. Perform a fresh independent provider read of the exact acknowledged commit and require the same parent binding. A null PR `merge_commit_sha` is allowed; a contradictory non-null value is not.
15. Freeze the result. No mutation replay.

## Verdicts

### `GITHUB_ACK_DIRECT_COMMIT_CLOSURE_ENFORCED`

PASS requires one GitHub merge request, a concrete successful acknowledgement, receiver restart, direct read-only confirmation of that exact acknowledged commit, valid signed effect + closure evidence, zero active frontiers, no unattributed merge observation, independent provider agreement on the exact commit and parents, and no private key in public evidence.

### `GITHUB_ACK_DIRECT_COMMIT_CLOSURE_FAILED`

FAIL is a known invariant violation: more than one merge mutation, wrong target/head/repository, wrong acknowledged commit, wrong parent binding, contradictory non-null PR merge SHA, signed evidence mismatch, closure that omits the confirmed effect, or any mutation after restart.

### `GITHUB_ACK_DIRECT_COMMIT_CLOSURE_UNRESOLVED`

If the acknowledged commit itself cannot be read and bound within the bounded read-only recovery window, the result stays unresolved. The mutation is never retried.

Bootstrap/auth/import failures before the receiver boundary are harness failures, not scientific verdicts.

## Claim boundary if PASS

> In one disposable real GitHub merge, GitHub acknowledged one concrete merge SHA before receiver settlement was interrupted. After receiver restart, OpenLine recovered that exact effect by reading the acknowledged commit directly, verified the reviewed head in its parents, issued signed effect and closure evidence, and never retried the mutation.

This does not prove control over GitHub merge queues, other writers, downstream Actions, production repositories, provider credential theft, or independent cryptographic attestation by GitHub.
