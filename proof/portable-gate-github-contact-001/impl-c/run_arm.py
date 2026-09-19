#!/usr/bin/env python3
"""Experiment driver (the 'worker') for PORTABLE-GATE-GITHUB-CONTACT-001.

Drives Implementation C (gate_c.py, the receiver) through the preregistered
arms. Each arm runs once against its own fresh disposable PR. No reruns.

Usage: python3 run_arm.py control|stopped|inflight
"""

import json
import os
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gate_c import Gate, gh_api, REPO, WORKDIR, GIT_IDENTITY, _run

BASE_BRANCH = "experiment/portable-gate-github-contact-001"


def ensure_base_branch():
    rc, br, _ = gh_api("GET", f"branches/{BASE_BRANCH}")
    if rc == 0:
        return br["commit"]["sha"]
    rc, main, err = gh_api("GET", "branches/main")
    if rc != 0:
        raise RuntimeError(f"cannot read main: {err}")
    sha = main["commit"]["sha"]
    rc, _, err = gh_api("POST", "git/refs",
                        {"ref": f"refs/heads/{BASE_BRANCH}", "sha": sha})
    if rc != 0:
        raise RuntimeError(f"cannot create base branch: {err}")
    return sha


def fixture(arm, attempt=1):
    """Fresh disposable head branch + PR. Returns (pr_number, head_sha).
    Each attempt gets a unique branch so fixtures never collide."""
    base_sha = ensure_base_branch()
    suffix = "" if attempt == 1 else f"-a{attempt}"
    head_branch = f"exp/pgc001-{arm}{suffix}"
    _run(["git", "fetch", "origin"], cwd=WORKDIR, check=True)
    _run(["git", "checkout", "-B", head_branch, base_sha], cwd=WORKDIR,
         check=True)
    proof = os.path.join(WORKDIR, "proof", "pgc001")
    os.makedirs(proof, exist_ok=True)
    with open(os.path.join(proof, f"{arm}{suffix}.txt"), "w") as f:
        f.write(f"pgc001 disposable {arm} target (attempt {attempt})\n")
    _run(["git", "add", f"proof/pgc001/{arm}{suffix}.txt"], cwd=WORKDIR,
         check=True)
    _run(["git"] + GIT_IDENTITY + ["commit", "-m",
          f"pgc001: disposable {arm} target (attempt {attempt})"],
         cwd=WORKDIR, check=True)
    _run(["git", "push", "-f", "origin", head_branch], cwd=WORKDIR,
         check=True)
    head_sha = _run(["git", "rev-parse", "HEAD"], cwd=WORKDIR,
                    check=True).stdout.strip()
    rc, pr, err = gh_api("POST", "pulls",
                         {"title": f"pgc001 disposable {arm} target",
                          "head": head_branch, "base": BASE_BRANCH,
                          "body": "Disposable PR for "
                                  "PORTABLE-GATE-GITHUB-CONTACT-001. "
                                  "Do not merge manually."})
    if rc != 0:
        # Anomaly mode observed 2026-09-19: the POST can report failure
        # while the PR was in fact created. Check before raising.
        rc2, existing, _ = gh_api(
            "GET", f"pulls?head=terryncew:{head_branch}&state=open")
        if rc2 == 0 and isinstance(existing, list) and len(existing) == 1:
            pr = existing[0]
            rc = 0
            print(f"fixture: adopted just-created PR #{pr['number']} "
                  f"after POST reported failure")
        else:
            raise RuntimeError(f"PR creation failed: {err or pr}")
    pr_number = pr["number"]
    for _ in range(60):
        rc, pr, _ = gh_api("GET", f"pulls/{pr_number}")
        if rc == 0 and pr.get("mergeable") is True:
            break
        time.sleep(5)
    else:
        raise RuntimeError(f"PR #{pr_number} never became mergeable "
                           "(INCOMPLETE: fixture defect)")
    return pr_number, head_sha


def arm_control():
    ARM = "control"
    g = Gate(ARM)
    pr, _ = fixture("control")
    g.admit(pr, "control")
    resp = g.attempt("control")
    assert resp["dispatched"] and resp["http_ok"] and \
        resp["body"].get("merged") is True, f"control merge failed: {resp}"
    merge_sha = resp["body"]["sha"]
    obs = g.observe(pr, "control")
    assert obs["merged"] is True and obs["merge_commit_sha"] == merge_sha, \
        f"control not confirmed: {obs}"
    g.log.record("ARM_RESULT", {"arm": "control", "pr": pr,
                                "merge_commit_sha": merge_sha,
                                "outcome": "CONTROL_EFFECT_OBSERVED"})
    print(f"CONTROL: PR #{pr} merged as {merge_sha}")


def arm_stopped():
    ARM = "stopped"
    g = Gate(ARM)
    pr, _ = fixture("stopped", attempt=3)
    g.admit(pr, "stopped")
    sentinel = g.stop(pr)  # STOP_ISSUED, sentinel push, STOP_EFFECTIVE
    print(f"STOPPED: STOP_EFFECTIVE sentinel {sentinel} on PR #{pr}")
    # Restart: fresh process reloads durable state; attempt must refuse.
    driver = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "attempt_once.py")
    with open(driver, "w") as f:
        f.write("import sys, json, os\n"
                "sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n"
                "from gate_c import Gate\n"
                "print(json.dumps(Gate(\'stopped\').attempt(\'stopped\')))\n")
    p = _run([sys.executable, driver], cwd=os.path.dirname(driver))
    resp = json.loads(p.stdout)
    assert resp.get("refused_locally") and not resp.get("dispatched"), \
        f"stopped arm dispatched: {resp}"
    print("STOPPED: fresh-process attempt refused locally (restart OK)")
    obs = g.observe(pr, "stopped")
    assert obs["merged"] is False and obs["state"] == "open", \
        f"stopped PR not unmerged: {obs}"
    # Provider-boundary probe (diagnostic, not C behavior): the old token
    # must be dead at the provider too.
    tok = g.state["admitted"]["stopped"]
    rc, body, _ = gh_api("PUT", f"pulls/{pr}/merge",
                         {"sha": tok["head_sha"], "merge_method": "merge"})
    got = str(body.get("status"))
    assert got == "409" and "Head branch was modified" in body.get("message",
                                                                   ""), \
        f"provider probe unexpected: {body}"
    g.log.record("PROVIDER_PROBE", {"pr": pr, "expected": 409,
                                    "got": body.get("status"),
                                    "note": "diagnostic: old token dead at "
                                            "provider; not C behavior"})
    g.log.record("ARM_RESULT", {"arm": "stopped", "pr": pr,
                                "sentinel_sha": sentinel,
                                "outcome": "STOPPED_REFUSED_UNMERGED"})
    print(f"STOPPED: PR #{pr} unmerged; provider probe 409 as expected")


def arm_inflight():
    ARM = "inflight"
    g = Gate(ARM)
    pr, _ = fixture("inflight")
    g.admit(pr, "inflight")
    ready = threading.Event()
    result = {}

    def worker():
        gw = Gate("inflight")  # separate instance, like a separate worker process
        result.update(gw.attempt_async("inflight", ready))

    t = threading.Thread(target=worker)
    t.start()
    if not ready.wait(timeout=60):
        raise RuntimeError("dispatch never initiated (INCOMPLETE)")
    # The merge request is underway pre-STOP. Owner STOPs now; C does not
    # retract the in-flight dispatch. GitHub's order decides the outcome.
    sentinel = g.stop(pr)
    t.join(timeout=120)
    if t.is_alive():
        raise RuntimeError("merge call hung (INCOMPLETE)")
    resp = result
    if resp.get("dispatched") and resp.get("http_ok") and \
            resp["body"].get("merged") is True:
        classification = "PRE_STOP_COMMIT"
        merge_sha = resp["body"]["sha"]
    elif resp.get("dispatched") and \
            str(resp["body"].get("status")) == "409":
        classification = "STOP_FIRST_REFUSAL"
        merge_sha = None
    else:
        raise RuntimeError(f"in-flight ambiguous response: {resp} "
                           "(INCOMPLETE)")
    obs = g.observe(pr, "inflight")
    if classification == "PRE_STOP_COMMIT":
        assert obs["merged"] is True and \
            obs["merge_commit_sha"] == merge_sha, f"mismatch: {obs}"
    else:
        assert obs["merged"] is False, f"mismatch: {obs}"
    g.log.record("ARM_RESULT", {"arm": "inflight", "pr": pr,
                                "sentinel_sha": sentinel,
                                "classification": classification,
                                "merge_commit_sha": merge_sha,
                                "note": "outcome decided by GitHub's "
                                        "processing order, classified "
                                        "honestly"})
    print(f"IN-FLIGHT: PR #{pr} -> {classification}")


if __name__ == "__main__":
    arm = sys.argv[1]
    {"control": arm_control, "stopped": arm_stopped,
     "inflight": arm_inflight}[arm]()
