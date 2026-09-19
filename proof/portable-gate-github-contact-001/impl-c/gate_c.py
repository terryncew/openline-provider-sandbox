#!/usr/bin/env python3
"""Implementation C — portable consequence-gate receiver for one GitHub merge.

Built from the portable semantic surface alone
(terryncew/openline-kill-switch@a303796: portable/README.md, GATE_CONTRACT.md,
IMPLEMENTER_CHECKLIST.md, CONFORMANCE.md, EVIDENCE.md).

Did NOT import, copy, call, or inspect for guidance: openline-kill-switch/src/,
openline-kill-switch/portable/impl-b/, OpenLine Wallet authority/gate code, the
reference kill-switch study code, or the SQLite implementation's internals.

Architecture (from the gate contract, not from any implementation):
- Owner-controlled STOP: only the owner role issues STOP (stop()).
- Authority token: (PR number, head SHA) bound at admission while ACTIVE.
- Revocation: owner STOP advances the PR head via a sentinel commit, which
  invalidates outstanding tokens at the provider.
- Final authority check: GitHub's `sha` compare-and-swap inside the merge
  operation — the check happens at commit time, server-side, atomically with
  the commit. A local dispatch-time check is a fail-safe fast path only.
- STOP_REQUESTED (local durable record) vs STOP_EFFECTIVE (sentinel landed in
  GitHub's order) are distinct, per the contract's vocabulary.
- Evidence: hash-chained JSONL; a separate appraiser re-derives verdicts.

Transport: `gh` CLI REST calls (generic provider transport, no authority
semantics). Stdlib only. No network except to api.github.com via gh.
"""

import hashlib
import json
import os
import subprocess
import sys
import time

REPO = "terryncew/openline-provider-sandbox"
HERE = os.path.dirname(os.path.abspath(__file__))
def state_path_for(arm):
    return os.path.join(HERE, f"state-{arm}.json")
EVIDENCE_PATH = os.path.join(HERE, "..", "evidence", "evidence.jsonl")
WORKDIR = os.path.join(HERE, "..", "sandbox")  # local clone for git pushes
GIT_IDENTITY = ["-c", "user.name=Terrynce White",
                "-c", "user.email=noreply@example.invalid"]


def _run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def gh_api(method, path, fields=None):
    cmd = ["gh", "api", f"repos/{REPO}/{path}", "-X", method]
    for k, v in (fields or {}).items():
        cmd += ["-f", f"{k}={v}"]
    p = _run(cmd)
    try:
        body = json.loads(p.stdout) if p.stdout.strip() else {}
    except json.JSONDecodeError:
        body = {"_raw": p.stdout}
    return p.returncode, body, p.stderr.strip()


class EvidenceLog:
    def __init__(self, path=EVIDENCE_PATH):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.head = "GENESIS"
        self.seq = 0
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    self.head = rec["hash"]
                    self.seq = rec["seq"]

    def record(self, rtype, payload):
        self.seq += 1
        body = {"seq": self.seq, "prev": self.head, "type": rtype,
                "payload": payload}
        canon = json.dumps(body, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256((self.head + canon).encode()).hexdigest()
        body["hash"] = digest
        with open(self.path, "a") as f:
            f.write(json.dumps(body, sort_keys=True) + "\n")
        self.head = digest
        return body


def load_state(arm):
    path = state_path_for(arm)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"stop_requested": False, "stop_effective": None,
            "admitted": {}, "owner": "owner"}


def save_state(arm, s):
    with open(state_path_for(arm), "w") as f:
        json.dump(s, f, indent=2, sort_keys=True)


class Gate:
    """The receiver. Owns: admission binding, revocation signal, local
    dispatch gate, durable STOP state, evidence. Does not own GitHub's
    atomic compare-and-commit; it binds authority to it."""

    def __init__(self, arm="default"):
        self.arm = arm
        self.log = EvidenceLog()
        self.state = load_state(arm)

    def _save(self):
        save_state(self.arm, self.state)

    def pr_head(self, pr_number):
        rc, pr, err = gh_api("GET", f"pulls/{pr_number}")
        if rc != 0:
            raise RuntimeError(f"pr_head failed: {err or pr}")
        return pr["head"]["sha"], pr["head"]["ref"], pr.get("mergeable")

    def admit(self, pr_number, token_id):
        """Admit preliminary work: explicitly non-authoritative."""
        if self.state["stop_requested"]:
            self.log.record("DECISION", {"token": token_id, "pr": pr_number,
                                         "decision": "REFUSE",
                                         "reason": "STOP_REQUESTED_LOCAL"})
            self._save()
            return None
        head_sha, head_ref, mergeable = self.pr_head(pr_number)
        self.state["admitted"][token_id] = {
            "pr": pr_number, "head_sha": head_sha, "head_ref": head_ref,
            "status": "ADMITTED"}
        self._save()
        self.log.record("ADMIT", {"token": token_id, "pr": pr_number,
                                  "head_sha": head_sha, "head_ref": head_ref,
                                  "mergeable": mergeable,
                                  "note": "preliminary; non-authoritative"})
        return head_sha

    def stop(self, pr_number):
        """Owner-only STOP. Returns sentinel SHA once STOP_EFFECTIVE."""
        if self.state["stop_requested"]:
            raise RuntimeError("STOP already requested")
        self.state["stop_requested"] = True
        self._save()
        self.log.record("STOP_ISSUED", {"pr": pr_number, "by": "owner"})
        # Revocation signal: advance the PR head so outstanding tokens die.
        _, head_ref, _ = self.pr_head(pr_number)
        _run(["git", "fetch", "origin", head_ref], cwd=WORKDIR,
             check=False)
        _run(["git", "checkout", "-B", head_ref, f"origin/{head_ref}"],
             cwd=WORKDIR, check=True)
        _run(["git"] + GIT_IDENTITY + ["commit", "--allow-empty", "-m",
              "pgc001: owner STOP sentinel (authority revocation signal)"],
             cwd=WORKDIR, check=True)
        sentinel = _run(["git", "rev-parse", "HEAD"], cwd=WORKDIR,
                        check=True).stdout.strip()
        push = _run(["git", "push", "origin", head_ref], cwd=WORKDIR)
        if push.returncode != 0:
            self.log.record("STOP_EFFECTIVE_FAILED",
                            {"stderr": push.stderr.strip()})
            raise RuntimeError(f"sentinel push failed: {push.stderr.strip()}")
        # Confirm the sentinel landed in GitHub's order.
        for _ in range(30):
            rc, br, _ = gh_api("GET", f"branches/{head_ref}")
            if rc == 0 and br["commit"]["sha"] == sentinel:
                break
            time.sleep(2)
        else:
            self.log.record("STOP_EFFECTIVE_FAILED",
                            {"reason": "sentinel not observed"})
            raise RuntimeError("sentinel push not observed on GitHub")
        self.state["stop_effective"] = {"pr": pr_number,
                                        "sentinel_sha": sentinel,
                                        "head_ref": head_ref}
        self._save()
        self.log.record("STOP_EFFECTIVE",
                        {"pr": pr_number, "sentinel_sha": sentinel,
                         "head_ref": head_ref,
                         "note": "ordering point: sentinel position in "
                                 "GitHub order"})
        return sentinel

    def attempt(self, token_id):
        """Final protected commit attempt through the gate."""
        tok = self.state["admitted"].get(token_id)
        if tok is None:
            raise RuntimeError(f"unknown token {token_id}")
        pr_number, head_sha = tok["pr"], tok["head_sha"]
        if self.state["stop_requested"]:
            self.log.record("DECISION", {"token": token_id, "pr": pr_number,
                                         "decision": "REFUSE",
                                         "reason": "STOP_REQUESTED_LOCAL",
                                         "note": "fail-safe fast path; no "
                                                 "dispatch left the gate"})
            return {"dispatched": False, "refused_locally": True}
        self.log.record("DISPATCH", {"token": token_id, "pr": pr_number,
                                     "sha": head_sha,
                                     "note": "provider CAS is the final "
                                             "authority check"})
        rc, body, err = gh_api("PUT", f"pulls/{pr_number}/merge",
                               {"sha": head_sha, "merge_method": "merge"})
        self.log.record("PROVIDER_RESPONSE",
                        {"token": token_id, "pr": pr_number,
                         "http_ok": rc == 0, "body": body,
                         "stderr": err})
        return {"dispatched": True, "http_ok": rc == 0, "body": body}

    def attempt_async(self, token_id, ready):
        """Variant for the in-flight case: local check, record DISPATCH,
        signal that the request is underway, then perform the HTTP call.
        The caller issues STOP after `ready` fires; GitHub's processing
        order decides the outcome."""
        tok = self.state["admitted"].get(token_id)
        if tok is None:
            raise RuntimeError(f"unknown token {token_id}")
        pr_number, head_sha = tok["pr"], tok["head_sha"]
        if self.state["stop_requested"]:
            self.log.record("DECISION", {"token": token_id, "pr": pr_number,
                                         "decision": "REFUSE",
                                         "reason": "STOP_REQUESTED_LOCAL"})
            ready.set()
            return {"dispatched": False, "refused_locally": True}
        self.log.record("DISPATCH", {"token": token_id, "pr": pr_number,
                                     "sha": head_sha,
                                     "note": "request underway pre-STOP; "
                                             "provider CAS decides"})
        ready.set()
        rc, body, err = gh_api("PUT", f"pulls/{pr_number}/merge",
                               {"sha": head_sha, "merge_method": "merge"})
        self.log.record("PROVIDER_RESPONSE",
                        {"token": token_id, "pr": pr_number,
                         "http_ok": rc == 0, "body": body,
                         "stderr": err})
        return {"dispatched": True, "http_ok": rc == 0, "body": body}

    def observe(self, pr_number, label):
        """Independent effect observation (GitHub is the effect source)."""
        rc, pr, err = gh_api("GET", f"pulls/{pr_number}")
        if rc != 0:
            raise RuntimeError(f"observe failed: {err or pr}")
        head_sha, _, _ = self.pr_head(pr_number)
        obs = {"label": label, "pr": pr_number, "state": pr["state"],
               "merged": pr["merged"],
               "merge_commit_sha": pr.get("merge_commit_sha"),
               "head_sha": head_sha}
        self.log.record("GITHUB_OBSERVATION", obs)
        return obs
