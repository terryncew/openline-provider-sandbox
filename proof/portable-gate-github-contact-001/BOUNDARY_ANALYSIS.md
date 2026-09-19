# BOUNDARY ANALYSIS — PORTABLE-GATE-GITHUB-CONTACT-001

Date: 2026-09-19. Author: Muse (implementer C / experimenter).
Source surface for kill-switch behavior: terryncew/openline-kill-switch@a303796
(portable/README.md, portable/GATE_CONTRACT.md, portable/IMPLEMENTER_CHECKLIST.md,
portable/CONFORMANCE.md, portable/EVIDENCE.md). Verified origin/main = a303796.

## The six questions

### 1. What exact event makes the merge irreversible for this experiment?

GitHub's server-side creation of the merge commit and update of the base-branch
ref during its processing of `PUT /repos/{o}/{r}/pulls/{n}/merge`.
Observable as: HTTP 200 with `merged:true` and a merge commit SHA in the
response body; independently confirmable afterwards via `GET /pulls/{n}`
(`merged:true`, `merge_commit_sha` set) — the commit is then part of the base
branch history. A local ADMIT decision is not this event. HTTP dispatch is not
this event. The 200 response is taken as the irreversible point only together
with the independent state confirmation.

### 2. What is the last point at which the receiver can still refuse it?

Two layers, kept distinct:

(a) Local: the receiver can refuse to dispatch the merge request at all.

(b) Provider: inside GitHub's processing of the merge operation, GitHub
evaluates the `sha` precondition — "SHA that pull request head must match to
allow merge." If the PR head does not equal the supplied SHA at processing
time, GitHub returns 409 ("Head branch was modified. Review and try the merge
again.") and no merge occurs. This was verified two ways on 2026-09-19:
GitHub's API documentation states the 409 semantics, and an empirical probe
(`PUT .../pulls/5/merge` with a bogus `sha`) returned exactly that 409 with
no state change (PR #5 re-queried afterwards: still open, unmerged).

The receiver controls (b) indirectly: it binds each admission to the exact
head SHA observed while authority was current, and revokes by advancing the
head (sentinel commit), which invalidates the binding.

### 3. Does the receiver itself own that point?

Partially, and the split is stated honestly rather than hidden:

- The receiver owns the admission binding (token = PR number + head SHA),
  the revocation signal (owner STOP advances the head via a sentinel commit),
  and the local dispatch gate.
- GitHub owns the atomic compare-and-commit inside the merge operation.

The receiver does NOT own GitHub's commit. What it owns is a
provider-enforced precondition on that commit: the merge cannot be created
unless the head still equals the SHA bound at admission time. Owner STOP
changes the head, so a post-STOP merge of a pre-STOP admission is refused by
the provider, not merely by the receiver's local code.

### 4. Or does it merely authorize / dispatch a request and then surrender control?

Without the `sha` binding, it would be mere dispatch — and the experiment
would be NO_GO. With the binding, the dispatch carries a provider-enforced
precondition that encodes current owner authority: authority token = (PR, head
SHA); revocation = head advancement. The difference between "checked STOP
immediately before sending the HTTP request" (forbidden downgrade) and this
design is mechanical: the standing check that matters happens inside GitHub's
merge operation, at commit time, against state the owner controls — not in the
receiver's process before dispatch.

### 5. Can STOP_EFFECTIVE and the irreversible merge commit be placed into one unambiguous ordering?

Yes. Definitions:

- STOP_REQUESTED: owner issues STOP to Implementation C (durable local record).
- STOP_EFFECTIVE: the sentinel commit's landing on the PR head branch in
  GitHub's order — observable via the API as head SHA == sentinel SHA.
  (Distinct from STOP_REQUESTED, per the contract's vocabulary.)

Both candidate events — GitHub's processing of `merge(sha=S)` and the
sentinel push landing — are GitHub-side events. GitHub serializes them, so
exactly one of two interleavings holds, each with a defined outcome:

- Merge processed first (head still S): merge commits. Ordering: effect
  before STOP_EFFECTIVE → honestly classified PRE_STOP_COMMIT.
- Sentinel lands first (head is S_sentinel ≠ S): 409, no merge.
  Ordering: STOP-first → refuse.

No wall-clock is used for the ordering claim. The API responses (200+merge
SHA vs 409) plus head-SHA observations are the ordering evidence.

### 6. Is there a provider-native primitive that genuinely lets the portable rule hold at the final merge boundary?

Yes: the merge endpoint's `sha` optimistic-concurrency parameter. It is
designed exactly for "do not commit unless the world still looks like it did
when I was authorized." The receiver binds "the world" to "head SHA observed
while owner authority was current" and makes owner STOP observably change the
world (sentinel commit). This is the standard capability-revocation pattern
(version-bound capability + provider compare-and-swap), not timing folklore:
at no point does the argument depend on how fast anything happens, only on
GitHub's processing order, which is unambiguous.

## Bottom-turtle assumptions (stated, not hidden)

- GitHub's merge endpoint validates `sha` and creates the merge commit as one
  server-side unit (docs + empirical 409 behavior support this; a TOCTOU
  inside GitHub's implementation is below this experiment's resolution, the
  same class of trust as the local store's atomicity in implementations A/B).
- During the experiment, only Implementation C pushes to the disposable PR
  head branches (append-only by C; no force-pushes).
- The `gh` CLI credential has push + pull-request write on the sandbox repo
  (verified by the successful 409 probe, which required an authenticated
  merge-attempt call).

## Conclusion

A legitimate implementation route exists. The critical stop condition does
NOT trigger: GitHub provides a usable primitive (`sha` CAS) that binds
current owner STOP standing — encoded as head-SHA stability — to the merge
commit. Proceeding to preregistration. NO_GO is not earned.
