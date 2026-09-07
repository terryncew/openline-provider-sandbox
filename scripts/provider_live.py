"""Provision one disposable GitHub PR and invoke the frozen Wallet live runner.

This is an experiment launcher, not an authorization service. It cannot target
any repository other than the dedicated, marked sandbox. No mutation is retried.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

SOURCE_COMMIT = "c35e7f427a26cddfc4e7d300a74b84aacc0ea64e"
SANDBOX = "terryncew/openline-provider-sandbox"
MARKER = "openline.wallet.disposable_provider_sandbox.v1"
CONFIRM = "RUN DISPOSABLE MERGE"
SHA = re.compile(r"[0-9a-f]{40}\Z")
RUN_ID = re.compile(r"[1-9][0-9]{0,19}\Z")
MAX_RESPONSE = 2 * 1024 * 1024


class ExperimentError(Exception):
    def __init__(self, code, *, details=None):
        self.code = code
        self.details = details or {}
        super().__init__(code)



def require(ok, code):
    if not ok:
        raise ExperimentError(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True).encode("ascii") + b"\n")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GitHubAPI:
    """Dedicated sandbox API, with no redirects, retries, or arbitrary URLs."""
    def __init__(self, token, repository=SANDBOX):
        require(repository == SANDBOX, "SANDBOX_REPOSITORY_REQUIRED")
        require(isinstance(token, str) and token and "\n" not in token and "\r" not in token,
                "GITHUB_TOKEN_REQUIRED")
        self.repository = repository
        self.token = token
        self.opener = build_opener(NoRedirect)
        self.mutations = []
        self.observations = []

    def request(self, method, suffix, body=None):
        require(method in {"GET", "POST", "PUT"}, "METHOD_INVALID")
        require((suffix == "" and method == "GET") or
                (suffix.startswith("/") and ".." not in suffix and not suffix.startswith("//")
                 and "?" not in suffix and "#" not in suffix), "PATH_INVALID")
        allowed = {
            ("GET", ""), ("GET", "/contents/SANDBOX.json"),
            ("POST", "/git/refs"), ("POST", "/pulls"),
        }
        permitted = (method, suffix) in allowed or (
            method == "GET" and (re.fullmatch(r"/git/ref/heads/[A-Za-z0-9-]+", suffix)
                                 or re.fullmatch(r"/pulls/[0-9]+", suffix)
                                 or re.fullmatch(r"/git/commits/[0-9a-f]{40}", suffix))
        ) or (method == "PUT" and re.fullmatch(r"/contents/olp-test-[0-9]+\.txt", suffix))
        require(bool(permitted), "ENDPOINT_NOT_ALLOWED")
        require((method == "GET") == (body is None), "BODY_INVALID")
        data = canonical(body) if body is not None else None
        path = "/repos/" + self.repository + suffix
        req = Request("https://api.github.com" + path, data=data, method=method,
            headers={"Authorization": "Bearer " + self.token,
                     "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2026-03-10",
                     "Content-Type": "application/json",
                     "User-Agent": "openline-provider-effect-live-001"})
        started = time.monotonic_ns()
        observation = {"method": method, "path": path,
                       "request_sha256": digest(data) if data is not None else None}
        if method != "GET":
            self.mutations.append(observation)  # Before dispatch, including uncertain attempts.
        try:
            with self.opener.open(req, timeout=20) as response:
                raw = response.read(MAX_RESPONSE + 1)
                require(len(raw) <= MAX_RESPONSE, "RESPONSE_TOO_LARGE")
                value = json.loads(raw)
                require(isinstance(value, dict), "RESPONSE_INVALID")
                observation.update(status=response.status, response_sha256=digest(raw),
                    duration_ns=time.monotonic_ns()-started,
                    request_id=response.headers.get("X-GitHub-Request-Id"))
                self.observations.append(dict(observation))
                return value
        except HTTPError as exc:
            try:
                raw_error = exc.read(8193)
                if len(raw_error) <= 8192:
                    error_body = json.loads(raw_error)
                    message = error_body.get("message") if isinstance(error_body, dict) else None
                    if isinstance(message, str):
                        observation["error_message"] = message.replace(self.token, "[REDACTED]")[:512]
            except (ValueError, OSError, UnicodeError):
                pass
            observation.update(status=exc.code, duration_ns=time.monotonic_ns()-started,
                request_id=exc.headers.get("X-GitHub-Request-Id"))
            self.observations.append(dict(observation))
            raise ExperimentError("GITHUB_HTTP_" + str(exc.code), status=exc.code,
                request_id=exc.headers.get("X-GitHub-Request-Id")) from None
        except (URLError, TimeoutError, OSError):
            observation.update(status="UNKNOWN", duration_ns=time.monotonic_ns()-started)
            self.observations.append(dict(observation))
            raise ExperimentError("GITHUB_TRANSPORT_UNCERTAIN") from None

    def repo(self):
        return self.request("GET", "")

    def marker(self):
        value = self.request("GET", "/contents/SANDBOX.json")
        import base64
        require(value.get("encoding") == "base64" and value.get("type") == "file", "MARKER_INVALID")
        return json.loads(base64.b64decode(value["content"], validate=False))

    def ref(self, name):
        return self.request("GET", "/git/ref/heads/" + name)

    def create_ref(self, name, sha):
        require(SHA.fullmatch(sha) is not None and re.fullmatch(r"olp-test-[0-9]+-(base|head)", name),
                "TEST_REF_INVALID")
        return self.request("POST", "/git/refs", {"ref": "refs/heads/"+name, "sha": sha})

    def put_test_file(self, branch, run_id, content):
        import base64
        require(branch == "olp-test-"+run_id+"-head", "TEST_BRANCH_INVALID")
        encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
        return self.request("PUT", "/contents/olp-test-"+run_id+".txt",
            {"message": "test: harmless provider-effect marker", "content": encoded, "branch": branch})

    def create_pr(self, head, base, run_id):
        require(head == "olp-test-"+run_id+"-head" and base == "olp-test-"+run_id+"-base",
                "TEST_PR_INVALID")
        return self.request("POST", "/pulls", {"title": "Disposable provider-effect test " + run_id,
            "head": head, "base": base, "body": "Harmless test marker. This PR exists only for PROVIDER-EFFECT-LIVE-001.",
            "draft": False, "maintainer_can_modify": False})

    def commit(self, sha):
        require(SHA.fullmatch(sha) is not None, "COMMIT_SHA_INVALID")
        return self.request("GET", "/git/commits/"+sha)

    def pr(self, number):
        require(type(number) is int and number > 0, "PR_NUMBER_INVALID")
        return self.request("GET", "/pulls/"+str(number))


def validate_sandbox(api):
    repo = api.repo()
    marker = api.marker()
    require(repo.get("full_name", "").lower() == SANDBOX and repo.get("owner", {}).get("login") == "terryncew"
            and type(repo.get("id")) is int and not repo.get("fork") and not repo.get("archived")
            and repo.get("default_branch") == "main", "SANDBOX_IDENTITY_INVALID")
    require(marker == {"schema": MARKER, "repository": SANDBOX,
                       "purpose": "Disposable GitHub merge experiments; no production data"}, "MARKER_INVALID")
    return repo


def bootstrap(api, run_id):
    require(RUN_ID.fullmatch(run_id) is not None, "RUN_ID_INVALID")
    repo = validate_sandbox(api)
    base_sha = api.ref("main")["object"]["sha"]
    require(SHA.fullmatch(base_sha) is not None, "BASE_SHA_INVALID")
    base, head = "olp-test-"+run_id+"-base", "olp-test-"+run_id+"-head"
    api.create_ref(base, base_sha)
    api.create_ref(head, base_sha)
    commit = api.put_test_file(head, run_id, "OpenLine disposable merge test " + run_id + "\n")
    require(SHA.fullmatch(commit["commit"]["sha"]) is not None, "TEST_COMMIT_INVALID")
    pr = api.create_pr(head, base, run_id)
    require(type(pr.get("number")) is int and pr["base"]["ref"] == base
            and pr["head"]["sha"] == commit["commit"]["sha"], "TEST_PR_RESPONSE_INVALID")
    return {"repository": SANDBOX, "repository_id": repo["id"], "number": pr["number"],
            "base_ref": base, "base_sha": base_sha, "head_ref": head,
            "head_sha": commit["commit"]["sha"], "source_commit": SOURCE_COMMIT,
            "run_id": run_id, "bootstrap_observations": list(api.observations)}


def wait_for_target(client, plan):
    from openline_wallet.github_effect_live import discover_target
    from openline_wallet.errors import WalletError
    deadline = time.monotonic() + 60
    while True:
        try:
            target, safety = discover_target(client, plan["repository"], plan["number"])
            require(target.repository_id == plan["repository_id"] and target.head_sha == plan["head_sha"]
                    and target.base_ref == plan["base_ref"] and target.base_sha == plan["base_sha"],
                    "TARGET_CHANGED")
            return target, safety
        except WalletError as exc:
            if exc.code != "GITHUB_PR_NOT_READY" or time.monotonic() >= deadline:
                raise
            time.sleep(2)


def verify_observation(evidence, plan, api=None):
    from openline_wallet.crypto import record_hash, verify_record
    from openline_wallet.wallet import verify_bundle
    from openline_wallet.clock import parse_time
    result = evidence["result"]
    require(verify_record(result)[0], "RESULT_SIGNATURE_INVALID")
    require(result["experiment_id"] == "PROVIDER-EFFECT-001", "EXPERIMENT_ID_MISMATCH")
    require(result["base_commit"] == "ec385ce2c0cdc253d5e634d1963f254203205e30",
            "EVIDENCE_SOURCE_BOUNDARY_INVALID")
    require(result["verdict"] == "LIVE_GITHUB_MERGE_OBSERVED" and
            result["transport"] == "github", "LIVE_RESULT_INCOMPLETE")
    directory = evidence["directory"]
    names = {p.name for p in directory.glob("*.json") if p.name != "result.json"}
    require(set(result["evidence_sha256"]) == names, "EVIDENCE_FILE_SET_MISMATCH")
    for name, expected in result["evidence_sha256"].items():
        require(name in names and digest((directory / name).read_bytes()) == expected,
                "EVIDENCE_HASH_MISMATCH")
    a, b, effect = evidence["after_a"], evidence["after_b"], evidence["effect_b"]["effect_receipt"]
    require(a["merged"] is False and b["merged"] is True and
            b["head_sha"] == plan["head_sha"] and b["repository_id"] == plan["repository_id"] and
            b["merge_commit_sha"] == effect["merge_commit_sha"] and
            evidence["merge_requests"] == 1 and evidence["merge_requests_after_a"] == 0 and
            evidence["closure_blocked_during_ack"] is True, "LIVE_OBSERVATION_MISMATCH")
    closure = evidence["closure_b"]
    key = effect["gate_public_key"]
    for record in (effect, evidence["effect_b"]["receipt"], evidence["admission_b"], closure):
        require(verify_record(record, expected_public_key=key)[0], "SIGNED_EVIDENCE_INVALID")
    key_a = evidence["admission_a"]["gate_public_key"]
    for record in (evidence["closure_a"], evidence["stopped_a"]["receipt"], evidence["admission_a"]):
        require(verify_record(record, expected_public_key=key_a)[0], "SIGNED_EVIDENCE_INVALID")
    require(evidence["closure_a"]["gate_public_key"] == key_a and
            evidence["closure_a"]["principal_id"] == evidence["admission_a"]["principal_id"],
            "CLOSURE_A_BINDING_INVALID")
    bundle = evidence["revoked_b"]
    verified_bundle, timeline = verify_bundle(bundle, now=parse_time(bundle["issued_at"]), require_fresh=False)
    require(timeline.mandates[effect["mandate_id"]]["status"] == "REVOKED" and
            verified_bundle["principal"]["principal_id"] == effect["principal_id"] and
            closure["mandate_id"] == effect["mandate_id"] and
            closure["status"] == "EFFECT_CLOSED" and closure["active_frontiers"] == 0 and
            record_hash(effect) in closure["confirmed_effect_hashes"], "CLOSURE_EVIDENCE_INVALID")
    require(effect["target"]["repository_id"] == plan["repository_id"] and
            effect["target"]["head_sha"] == plan["head_sha"] and
            effect["merge_commit"]["parents"][1] == plan["head_sha"], "EFFECT_TARGET_INVALID")
    require(evidence["stopped_a"]["decision"] == "STOPPED" and
            evidence["stopped_a"]["effect_applied"] is False and
            evidence["closure_a"]["status"] == "EFFECT_CLOSED" and
            evidence["closure_a"]["active_frontiers"] == 0, "PRE_DISPATCH_CONTROL_INVALID")
    require(evidence["effect_b"]["decision"] == "ALLOWED" and
            evidence["effect_b"]["effect_applied"] is True and
            evidence["errors"] == [] and evidence["wallet_receipt_count"] >= 2,
            "EFFECT_RESULT_INVALID")
    timing = evidence["timing"]
    require(all(type(timing.get(k)) is int for k in
            ("ack_observed_ns", "revocation_requested_ns", "closure_requested_ns",
             "ack_released_ns", "closure_returned_ns")) and
            timing["ack_observed_ns"] <= timing["revocation_requested_ns"] <=
            timing["closure_requested_ns"] <= timing["ack_released_ns"] <=
            timing["closure_returned_ns"], "CLOSURE_TIMING_INVALID")
    require(closure["principal_id"] == effect["principal_id"] and
            closure["gate_id"] == effect["gate_id"] and
            closure["gate_public_key"] == key and
            closure["target"] == effect["target"] and
            closure["head_sequence"] == verified_bundle["head"]["sequence"] and
            closure["head_hash"] == verified_bundle["head"]["event_hash"],
            "CLOSURE_BINDING_INVALID")
    observation = {"verdict": "LIVE_GITHUB_MERGE_OBSERVED",
        "scope": "ONE_DISPOSABLE_PR_HELD_ACKNOWLEDGEMENT",
        "merge_commit_sha": b["merge_commit_sha"], "repository_id": plan["repository_id"],
        "head_sha": plan["head_sha"], "base_drift": effect["merge_commit"]["base_drift"]}
    if api is not None:
        # Independent fresh provider reads; these can corroborate a result but
        # cannot identify a writer or establish anything about downstream work.
        current = api.pr(plan["number"])
        commit = api.commit(b["merge_commit_sha"])
        require(current["merged"] is True and current["merge_commit_sha"] == b["merge_commit_sha"] and
                current["head"]["sha"] == plan["head_sha"] and
                current["base"]["repo"]["id"] == plan["repository_id"] and
                current["base"]["ref"] == plan["base_ref"], "PROVIDER_FINAL_STATE_MISMATCH")
        parents = [row["sha"] for row in commit["parents"]]
        require(commit["sha"] == b["merge_commit_sha"] and len(parents) == 2 and
                parents == effect["merge_commit"]["parents"], "PROVIDER_COMMIT_MISMATCH")
        observation["provider_observation"] = {"pr_number": plan["number"],
            "merge_commit_sha": commit["sha"], "parents": parents,
            "base_drift": parents[0] != plan["base_sha"],
            "request_observations": api.observations[-2:]}
    return observation


def execute(api, plan, private, public):
    from openline_wallet.github_effect import GitHubClient, _snapshot
    from openline_wallet.github_effect_live import run_experiment, recover
    client = GitHubClient(api.token)
    target, safety = wait_for_target(client, plan)
    write_json(public / "target.json", {"target": target.to_record(), "safety": safety, "effect_authority": "NONE"})
    # The only code path permitted to issue the merge PUT is the existing receiver.
    try:
        data = run_experiment(client, target, private, public / "provider", transport="github")
        if data["verdict"] != "LIVE_GITHUB_MERGE_OBSERVED":
            raise ExperimentError("LIVE_PROVIDER_INCONCLUSIVE")
        directory = public / "provider"
        evidence = {p.stem: json.loads(p.read_text()) for p in directory.glob("*.json")}
        evidence["directory"] = directory
        return verify_observation(evidence, plan, api)
    except Exception:
        # Never retry the mutation. Recovery is read/reconcile-only.
        try:
            recovery = recover(client, private, public / "recovery")
            write_json(public / "recovery-summary.json", recovery)
        except Exception as exc:
            write_json(public / "recovery-error.json", {"code": getattr(exc, "code", type(exc).__name__)})
        raise


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args(argv)
    require(args.confirm == CONFIRM, "EXPLICIT_CONFIRMATION_REQUIRED")
    public, private = args.output.resolve(), args.state.resolve()
    require(public != private and public not in private.parents and private not in public.parents, "PATH_OVERLAP")
    require(not public.exists() and not private.exists(), "OUTPUT_ALREADY_EXISTS")
    public.mkdir(parents=True, mode=0o700)
    private.mkdir(parents=True, mode=0o700)
    api = GitHubAPI(os.environ.get("OPENLINE_GITHUB_TOKEN", ""))
    prereg = Path(__file__).resolve().parents[1] / "PREREGISTRATION.json"
    require(prereg.is_file(), "PREREGISTRATION_MISSING")
    prereg_sha256 = digest(prereg.read_bytes())
    report = {"experiment_id": "PROVIDER-EFFECT-LIVE-001", "preregistration_sha256": prereg_sha256, "status": "INCONCLUSIVE",
              "source_commit": SOURCE_COMMIT, "transport": "github", "claim_boundary":
              "One disposable PR; held acknowledgement after provider response. No internal queue, Actions, other writers, or production closure claim."}
    try:
        plan = bootstrap(api, args.run_id)
        write_json(public / "plan.json", plan)
        report.update(execute(api, plan, private, public))
        report["status"] = "COMPLETE"
    except Exception as exc:
        report["error_code"] = getattr(exc, "code", str(exc) if isinstance(exc, ExperimentError) else type(exc).__name__)
    finally:
        report["bootstrap_mutations"] = len(api.mutations)
        write_json(public / "bootstrap-http.json", api.observations)
        write_json(public / "summary.json", report)
        hashes = {str(p.relative_to(public)): digest(p.read_bytes()) for p in sorted(public.rglob("*"))
                  if p.is_file() and p.name != "SHA256SUMS.txt"}
        (public / "SHA256SUMS.txt").write_text("".join(f"{v}  {k}\n" for k,v in hashes.items()))
        print(json.dumps({"status": report["status"], "verdict": report.get("verdict", "INCONCLUSIVE"),
                          "error_code": report.get("error_code")}, sort_keys=True))
    return 0 if report["status"] == "COMPLETE" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ExperimentError as exc:
        print("STOPPED — " + str(exc), file=sys.stderr)
        raise SystemExit(2)
