# RUN RECORD — PORTABLE-GATE-GITHUB-CONTACT-001

## Apparatus abort: stopped arm, first attempt (PR #18)

During the first stopped-arm run, the gate behaved correctly throughout
(ADMIT while ACTIVE; STOP_ISSUED; sentinel pushed and STOP_EFFECTIVE
observed; fresh-process attempt refused locally with no dispatch; GitHub
observation: PR #18 open, unmerged). The driver's provider-probe assertion
then crashed: it compared GitHub's `"status": "409"` (string) to int `409`.
GitHub had in fact returned the expected 409 "Head branch was modified."

This was an apparatus defect in the experiment driver, not a scientific
result. Per the no-rerun rule ("freeze first"), PR #18's evidence chain is
left exactly as it stands — aborted, with no ARM_RESULT — and the stopped
arm is executed fresh against a new disposable PR. The driver bug was fixed
(string comparison) before the fresh run. PR #18 remains open and unmerged
as the aborted fixture.

Note: the second fixture attempt reset the aborted PR #18's head branch
(exp/pgc001-stopped) to a new commit before PR creation failed with 422
(head already had PR #18). No scientific claim rests on PR #18; the
fixture() function now uses unique branch names per attempt
(exp/pgc001-<arm>-a<attempt>) so this cannot recur.

## Completed arms

- CONTROL: PR #17 (head 88e10405) merged under ACTIVE as merge commit
  38b8f5540d7ee45cdd3b3101a3ee2675a9d9cc68. Independent re-query confirms.
- STOPPED: PR #20. STOP_ISSUED, sentinel 90fa61ff44e4f3ef84180a6bd8c215127f48ce71
  pushed, STOP_EFFECTIVE observed in GitHub's order. Fresh-process attempt
  refused locally (restart durability). Independent re-query: PR open,
  unmerged. Provider probe PUT /merge with the dead token -> 409
  "Head branch was modified". Verdict: STOPPED_REFUSED_UNMERGED.
- IN-FLIGHT: PR #21. Worker dispatched merge(sha=admitted head) while ACTIVE;
  owner STOP ran concurrently; sentinel 9ff74425... landed after GitHub
  committed the merge ab6aa3e4. Independent re-query confirms the merge
  commit predates STOP_EFFECTIVE. Honest classification: PRE_STOP_COMMIT.
  The local evidence fork at ADMIT (worker DISPATCH chain vs main STOP
  chain) correctly represents the genuine concurrency; the ordering verdict
  came from GitHub's order, as preregistered.

## Apparatus defects (disclosed, non-material to the verdict)

1. EvidenceLog cached head/seq at construction; concurrent writers (fresh
   subprocess in stopped runs; worker thread in the in-flight arm) forked
   the hash chain at 3 points (seq 9, 14, 17-duplicates). Forensics: all 25
   records' individual hashes verify (no record altered), no dangling
   links, both per-writer chains linear, causal links intact (refusals
   observe completed STOP; inflight worker/main chains share the ADMIT
   prefix). The independent appraisal verifies these DAG properties plus a
   full independent GitHub re-query of every effect claim: PASS.
2. Stopped-arm first attempt (PR #18) aborted on a driver assertion bug
   (string "409" vs int); documented above, arm re-run fresh on PR #20.
   A GitHub API anomaly (PR #19 created while the POST reported 422) was
   handled by adopt-if-just-created logic; PR #19 was never armed.

Evidence: evidence/evidence.jsonl (sha256
68af081caded8cf396c0f2b130d50325830118908880e1a97ab760d50208baf2),
independent appraisal: evidence/appraisal.txt (sha256
866c7d2882190fc5e6857108c941d1866d759176171bc9bbe576afeca9bd9fe8).
