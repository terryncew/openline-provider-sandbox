"""Run real read-only checks for one exact disposable GitHub head.

This is a sandbox orchestration helper, not a Wallet authority mechanism.
The only write is dispatching the fixed check workflow. A failed or uncertain
request is never retried. No merge is issued from this module.
"""
from __future__ import annotations

import re
import time
from typing import Any

CHECK_WORKFLOW = "provider-effect-head-check.yml"
CHECK_NAME = "provider-head-check-"
CHECK_TIMEOUT = 240
SHA = re.compile(r"[0-9a-f]{40}\Z")
RUN_ID = re.compile(r"[1-9][0-9]{0,19}\Z")
REPOSITORY = "terryncew/openline-provider-sandbox"
SOURCE_COMMIT = "c35e7f427a26cddfc4e7d300a74b84aacc0ea64e"


class HeadCheckError(Exception):
    def __init__(self, code: str, details: dict[str, Any] | None = None):
        self.code = code
        self.details = details or {}
        super().__init__(code)


def require(ok: bool, code: str, details: dict[str, Any] | None = None) -> None:
    if not ok:
        raise HeadCheckError(code, details)


def _identity(plan: dict[str, Any]) -> tuple[str, str, str]:
    run_id, head = plan["run_id"], plan["head_sha"]
    require(isinstance(run_id, str) and RUN_ID.fullmatch(run_id), "HEAD_CHECK_RUN_ID_INVALID")
    require(isinstance(head, str) and SHA.fullmatch(head), "HEAD_CHECK_SHA_INVALID")
    branch = "olp-test-" + run_id + "-head"
    require(plan["repository"] == REPOSITORY and plan["repository_id"] == 1360489534
            and plan["head_ref"] == branch and plan["source_commit"] == SOURCE_COMMIT,
            "HEAD_CHECK_TARGET_INVALID")
    return run_id, head, branch


def write_json(path: Any, value: Any) -> None:
    from pathlib import Path
    import json
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True).encode("ascii") + b"\n")


def run_head_check(api: Any, plan: dict[str, Any], output: Any,
                   *, clock=time.monotonic, sleep=time.sleep, timeout=CHECK_TIMEOUT) -> dict[str, Any]:
    """Require an actual successful GitHub Actions run and published check.

    The caller supplies a fixed-endpoint API and a public evidence directory.
    No retry of the dispatch is allowed, even if its acknowledgement is lost.
    """
    from pathlib import Path
    import json

    run_id, head, branch = _identity(plan)
    output = Path(output)
    # Confirm the head is still exactly the one created by this invocation.
    before = api.ref(branch)
    require(before.get("object", {}).get("sha") == head,
            "HEAD_CHECK_TARGET_CHANGED")
    response = api.dispatch_head_check(run_id, head)
    workflow_run_id = response.get("workflow_run_id")
    require(type(workflow_run_id) is int and workflow_run_id > 0,
            "HEAD_CHECK_DISPATCH_ID_UNAVAILABLE", {"dispatch_status": response.get("status")})
    record = {"schema": "openline.wallet.provider_head_check.v1", "parent_run_id": run_id,
              "head_sha": head, "head_ref": branch, "workflow_run_id": workflow_run_id,
              "source_commit": SOURCE_COMMIT, "status": "INCONCLUSIVE"}
    write_json(output / "head-check.json", record)
    deadline = clock() + timeout
    while clock() < deadline:
        run = api.head_check_run(workflow_run_id)
        require(run.get("id") == workflow_run_id and run.get("head_sha") == head
                and run.get("head_branch") == branch and run.get("event") == "workflow_dispatch"
                and run.get("path") == ".github/workflows/" + CHECK_WORKFLOW
                and run.get("head_repository", {}).get("id") == plan["repository_id"],
                "HEAD_CHECK_RUN_IDENTITY_INVALID")
        record["workflow_status"] = run.get("status")
        record["workflow_conclusion"] = run.get("conclusion")
        if run.get("status") == "completed":
            require(run.get("conclusion") == "success", "HEAD_CHECK_FAILED", record)
            jobs = api.head_check_jobs(workflow_run_id)
            rows = jobs.get("jobs", [])
            require(jobs.get("total_count") == 1 and len(rows) == 1,
                    "HEAD_CHECK_JOBS_INVALID")
            job = rows[0]
            require(job.get("name") == CHECK_NAME + run_id and job.get("run_id") == workflow_run_id
                    and job.get("status") == "completed" and job.get("conclusion") == "success"
                    and job.get("head_sha", head) == head and type(job.get("id")) is int
                    and job["id"] > 0, "HEAD_CHECK_JOB_INVALID")
            expected_steps = {"Verify disposable source identity", "Verify pinned Wallet source",
                              "Test pinned Wallet downstream suite", "Test sandbox downstream suite",
                              "Compile launcher"}
            steps = {row.get("name"): row.get("conclusion") for row in job.get("steps", [])}
            require(all(steps.get(name) == "success" for name in expected_steps),
                    "HEAD_CHECK_STEPS_INVALID")
            checks = api.head_checks(head)
            rows = checks.get("check_runs", [])
            require(type(checks.get("total_count")) is int and checks["total_count"] == len(rows),
                    "HEAD_CHECK_LIST_INCOMPLETE")
            matches = [row for row in rows if row.get("name") == CHECK_NAME + run_id]
            if len(matches) == 1:
                check = matches[0]
                require(check.get("head_sha") == head and check.get("status") == "completed"
                        and check.get("conclusion") == "success"
                        and check.get("app", {}).get("slug") == "github-actions"
                        and type(check.get("id")) is int, "HEAD_CHECK_PUBLISHED_INVALID")
                after = api.ref(branch)
                require(after.get("object", {}).get("sha") == head, "HEAD_CHECK_TARGET_CHANGED")
                record.update(status="COMPLETE", conclusion="success", check_run_id=check["id"],
                              job_id=job["id"], run_url=run.get("html_url"))
                write_json(output / "head-check.json", record)
                return record
            require(len(matches) <= 1, "HEAD_CHECK_DUPLICATE")
        else:
            require(run.get("status") in {"queued", "in_progress", "waiting", "requested", "pending"},
                    "HEAD_CHECK_STATUS_INVALID")
        sleep(2)
    write_json(output / "head-check.json", record)
    raise HeadCheckError("HEAD_CHECK_TIMEOUT", record)
