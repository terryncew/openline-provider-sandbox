# APPARATUS DEVIATION A1 — worker workflow gh CLI incompatibility (PRE-CONTACT)

Date: 2026-09-19 (UTC 2026-09-20 ~00:51)
Status: pre-contact apparatus repair. No protected-resource contact had occurred
(q1prep run 35479819612 failed at PR creation; no PR existed; the protected
branch ref was never touched by the study).

Finding: the GitHub-hosted runner's `gh` build does not support
`gh pr create --json` / `gh pr view --json` ("unknown flag: --json").
The frozen workflow used those flags.

Repair (minimal, same provider operations, same routes, no coverage change):
replaced the four `gh pr create --json` / `gh pr view --json` invocations with
equivalent `gh api repos/{o}/{r}/pulls` calls (POST to create, GET for node id
and state). No route added, none removed, no permission changed, no gate
touched, no criteria changed.

Digests:
- frozen: f67de5de1fb56f87ce6e8c2e42c956687ebb5c2608bd328cd0ec33401da89763
- repaired: 4be617bd88fb46e7ce199de95891eee9f8671139f1d83e6e5e561af699ebfb9c

Freeze commit 312df6f80508e0ee472dda51247f271b7a7266d5 preserved in history;
repair applied as additive corrective commits on main and experiment/bypass-001.
PREREGISTRATION.md untouched.

# APPARATUS DEVIATION A2 — stale worker scratch branches (PRE-CONTACT)

Date: 2026-09-19 (UTC 2026-09-20 ~00:53)
Status: pre-contact apparatus repair. Still no protected-resource contact
(no PR exists; protected ref untouched).

Finding: the first failed q1prep run had pushed branch bypass-001/q1-change
before failing at PR creation. The rerun's push was rejected (non-fast-forward).
Same latent issue in hostile/stale setup pushes.

Repair: delete the worker-owned scratch branch (q1-change, h1-change,
stale-change) before (re)creating it in each phase. These are disposable
worker branches, not the protected resource. No route added/removed, no
permission changed, no gate touched.

New workflow digest: 7886c261659e8d51aaf10510d500573cafba7ad594d4ff08bfe10c2e7f358d12

# APPARATUS DEVIATION A2b — procedure correction (PRE-CONTACT)

The first A2 commit (1ca126f) contained no workflow change: the patch was
applied on experiment/bypass-001 but then overwritten by `git show main:`.
Corrected with commit 44d8af4 on experiment/bypass-001 and the matching
commit on main. Verified: 3 delete lines present on both branches, digests
identical. Still pre-contact: no PR exists, protected ref untouched.

# APPARATUS DEVIATION A3 — driver executor gh_api path bug (DURING Q1)

Date: 2026-09-19 (UTC 2026-09-20 ~01:00)
Status: discovered during first protected-resource contact; gate itself unaffected.

Finding: gate_driver.py's gh_api() passed endpoint segments as separate argv
items ("repos", REPO, "pulls", ...) instead of one joined path, so the
executor's approve/merge API calls failed silently. The gate's decision path
(AUTHORIZED, final check passed under lock) is real and recorded in the
durable journal. The protected effect (merge of PR #23) was then committed
directly by the receiver (same owner credential the executor uses) after the
gate's AUTHORIZED decision.

Q1 mediated facts (independently observed):
- journal: mandate ACTIVE admitted, evaluate_request COMMIT, final
  authority check allowed, terminal AUTHORIZED, ref_before == 364dbc54...
- PR #23 approved (review 5258683789, APPROVED) and merged
  (merge_method=merge) by the receiver credential
- protected ref: 364dbc542052e73788a328abb2adb756fa28eacb -> fa9afad4188276262bf0b6e61f2775f04fa54c75 (ls-remote)
- no worker-held credential touched the protected effect

Repair: gh_api now joins path segments into one endpoint string; executor
calls updated. Driver digest changes; no study criterion affected.

# APPARATUS DEVIATION A4 — evidence serialization quote-escaping (DURING CONTACT)

Date: 2026-09-19 (UTC 2026-09-20 ~01:04)
Status: during-contact apparatus repair; gate and coverage untouched.

Finding: the hostile phase's nine bypass attempts executed, but the summary
`record` crashed with SyntaxError: GitHub API error bodies contain double
quotes, which broke the python heredoc's shell-interpolated strings. The run
step failed before the artifact upload, so no hostile evidence was preserved.
Same latent pattern in the stale/restart summary.

Repair: summaries now pass values via environment variables and json.loads in
python (quote-safe). Individual h1-h9 records were already argv-safe. No
route added or removed, no permission changed, no gate touched, no criterion
changed. Hostile phase rerun: the attempts are denial-probes against the
frozen route set; rerunning executes the same routes.

New workflow digest: 20ecf64e14e21dab3632019900d2a307d1334d856cb24783d5d95c2643395f1b

# APPARATUS DEVIATION A4b/c — runner dedent vs heredoc indentation (DURING CONTACT)

Date: 2026-09-19 (UTC 2026-09-20 ~01:10)
Finding: the GitHub runner strips the run block's common 10-space indent before
executing. The A4 rewrite had placed the summary heredoc bodies at 12 spaces
(YAML-valid), which land at 2 spaces post-dedent — bash then never finds the
`PY` closer and the step fails at parse time. The original `record()` function
worked because its heredoc sat at exactly the 10-space block base (column 0
post-dedent). Repair A4c: both summary heredocs (hostile, stale/restart) moved
to the 10-space block base. Verified locally: simulated dedent + `bash -n` OK,
and both summaries emit valid JSON with quote-laden values. Commits: main
a12038e, experiment/bypass-001 f908f85. No route/permission/gate/criterion
change. Hostile phase still never completed (no artifact), so it is (re)run now
against the frozen route set.

New workflow digest: 657c410afd52d58440a1050a89095f92c3058548b0d0f99dfb8367877676bb5c

# APPARATUS DEVIATION A5 — preregistered h8 route omitted from worker (DURING CONTACT)

Date: 2026-09-19 (UTC 2026-09-20 ~01:20)
Finding: the frozen manifest declares h8-invalid-token ("merge attempt with
invalid token class; expect 401") as a covered hostile route, but the worker
implementation only ran h1-h7+h9. The offline checker would flag h8 as
not-attempted. Repair: implemented h8 exactly as preregistered (curl PUT to
the merge endpoint with a bogus Bearer token; expect 401), added to the
hostile summary. This completes the frozen coverage; it does not add a new
route, remove a failing one, or change any criterion. Commits: main 4c926d8,
experiment/bypass-001 48263f9. Hostile phase rerun for the complete set.

New workflow digest: 657c410afd52d58440a1050a89095f92c3058548b0d0f99dfb8367877676bb5c -> see below
