"""Real-check orchestration controls; no network or synthetic check is published."""
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import provider_head_check as check

SPEC = importlib.util.spec_from_file_location("head_check_launcher", ROOT / "scripts/provider_live.py")
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)
A = "a" * 40
B = "b" * 40
RID = "123"
RUN = 456


def plan():
    return {"repository": check.REPOSITORY, "repository_id": 1360489534,
            "run_id": RID, "head_ref": "olp-test-123-head", "head_sha": A,
            "source_commit": check.SOURCE_COMMIT, "number": 7,
            "base_ref": "olp-test-123-base", "base_sha": B}


class FakeAPI:
    def __init__(self):
        self.dispatches = 0
        self.merges = 0
        self.status = "completed"
        self.conclusion = "success"
        self.job_conclusion = "success"
        self.check_conclusion = "success"
        self.head = A
        self.mismatched = False
        self.duplicate = False
        self.run_id = RUN
    def ref(self, name):
        return {"object": {"sha": self.head}}
    def dispatch_head_check(self, run_id, sha):
        self.dispatches += 1
        return {"workflow_run_id": self.run_id}
    def head_check_run(self, run_id):
        return {"id": run_id, "head_sha": B if self.mismatched else A,
                "head_branch": "olp-test-123-head", "event": "workflow_dispatch",
                "path": ".github/workflows/provider-effect-head-check.yml",
                "head_repository": {"id": 1360489534}, "status": self.status,
                "conclusion": self.conclusion, "html_url": "https://github.com/terryncew/openline-provider-sandbox/actions/runs/456"}
    def head_check_jobs(self, run_id):
        names = ["Verify disposable source identity", "Verify pinned Wallet source",
                 "Test pinned Wallet downstream suite", "Test sandbox downstream suite", "Compile launcher"]
        return {"total_count": 1, "jobs": [{"id": 789, "run_id": run_id,
                "name": "provider-head-check-123", "status": "completed",
                "conclusion": self.job_conclusion,
                "steps": [{"name": n, "conclusion": "success"} for n in names]}]}
    def head_checks(self, sha):
        item = {"id": 999, "name": "provider-head-check-123", "head_sha": A,
                "status": "completed", "conclusion": self.check_conclusion,
                "app": {"slug": "github-actions"}}
        rows = [item, dict(item, id=1000)] if self.duplicate else [item]
        return {"total_count": len(rows), "check_runs": rows}


class HeadCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name)
        self.api = FakeAPI()
    def run_check(self, **kwargs):
        options = {"sleep": lambda _: None, "timeout": 1}
        options.update(kwargs)
        return check.run_head_check(self.api, plan(), self.output, **options)
    def test_real_completed_run_job_and_published_check_required(self):
        result = self.run_check()
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["check_run_id"], 999)
        self.assertEqual(self.api.dispatches, 1)
        self.assertEqual(self.api.merges, 0)
        self.assertEqual(json.loads((self.output / "head-check.json").read_text())["head_sha"], A)
    def test_wrong_head_is_rejected_before_dispatch(self):
        self.api.head = B
        with self.assertRaisesRegex(check.HeadCheckError, "HEAD_CHECK_TARGET_CHANGED"):
            self.run_check()
        self.assertEqual(self.api.dispatches, 0)
    def test_wrong_repository_or_run_id_is_rejected(self):
        for alteration in [{"repository": "terryncew/openline-wallet"}, {"run_id": "../main"},
                           {"head_ref": "main"}, {"head_sha": "bad"}]:
            with self.subTest(alteration=alteration):
                with self.assertRaises(check.HeadCheckError):
                    check.run_head_check(self.api, dict(plan(), **alteration), self.output)
        self.assertEqual(self.api.dispatches, 0)
    def test_lost_dispatch_ack_is_not_retried(self):
        self.api.run_id = None
        with self.assertRaisesRegex(check.HeadCheckError, "DISPATCH_ID_UNAVAILABLE"):
            self.run_check()
        self.assertEqual(self.api.dispatches, 1)
    def test_failed_or_skipped_workflow_never_authorizes(self):
        for status in ["failure", "cancelled", "skipped", "timed_out"]:
            self.api.conclusion = status
            with self.subTest(status=status):
                with self.assertRaisesRegex(check.HeadCheckError, "HEAD_CHECK_FAILED"):
                    self.run_check()
        self.assertEqual(self.api.merges, 0)
    def test_wrong_workflow_head_is_rejected(self):
        self.api.mismatched = True
        with self.assertRaisesRegex(check.HeadCheckError, "RUN_IDENTITY_INVALID"):
            self.run_check()
    def test_skipped_job_is_rejected_even_if_workflow_says_success(self):
        self.api.job_conclusion = "skipped"
        with self.assertRaisesRegex(check.HeadCheckError, "HEAD_CHECK_JOB_INVALID"):
            self.run_check()
    def test_missing_or_failed_step_is_rejected(self):
        original = self.api.head_check_jobs
        def missing(run_id):
            value = original(run_id)
            value["jobs"][0]["steps"] = []
            return value
        self.api.head_check_jobs = missing
        with self.assertRaisesRegex(check.HeadCheckError, "HEAD_CHECK_STEPS_INVALID"):
            self.run_check()
    def test_failed_or_duplicate_published_check_is_rejected(self):
        self.api.check_conclusion = "failure"
        with self.assertRaisesRegex(check.HeadCheckError, "HEAD_CHECK_PUBLISHED_INVALID"):
            self.run_check()
        self.api.check_conclusion = "success"
        self.api.duplicate = True
        with self.assertRaisesRegex(check.HeadCheckError, "HEAD_CHECK_DUPLICATE"):
            self.run_check()
    def test_dispatch_http_403_preserves_error_and_never_retries(self):
        api = mod.GitHubAPI("private-test-token")
        calls = []
        class Forbidden:
            def open(self, request, timeout):
                calls.append(request)
                raise HTTPError(request.full_url, 403, "Forbidden", {}, io.BytesIO(b'{"message":"Forbidden"}'))
        api.opener = Forbidden()
        with self.assertRaises(mod.ExperimentError) as caught:
            api.dispatch_head_check(RID, A)
        self.assertEqual(caught.exception.code, "GITHUB_HTTP_403")
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(api.mutations), 1)
    def test_dispatch_accepts_200_with_exact_run_id(self):
        api = mod.GitHubAPI("private-test-token")
        class Response:
            status = 200
            headers = {}
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, n=-1): return b'{"workflow_run_id":456}'
        class Opener:
            def open(self, request, timeout):
                self.request = request
                return Response()
        api.opener = Opener()
        self.assertEqual(api.dispatch_head_check(RID, A)["workflow_run_id"], RUN)
        self.assertEqual(api.opener.request.method, "POST")
        self.assertEqual(len(api.mutations), 1)
    def test_arbitrary_workflow_dispatch_and_mutation_paths_denied(self):
        api = mod.GitHubAPI("private-test-token")
        for path, body in [("/actions/workflows/ci.yml/dispatches", {}),
                ("/actions/workflows/provider-effect-head-check.yml/dispatches",
                 {"ref": "main", "inputs": {"parent_run_id": RID, "head_sha": A}}),
                ("/pulls/7/merge", {"sha": A})]:
            with self.assertRaises(mod.ExperimentError):
                api.request("POST", path, body)
        self.assertEqual(api.mutations, [])
    def test_execute_cannot_reach_receiver_if_head_check_fails(self):
        import openline_wallet.github_effect_live as live
        with patch.object(mod, "run_head_check", side_effect=check.HeadCheckError("HEAD_CHECK_FAILED")), \
             patch.object(mod, "wait_for_target") as discovery, \
             patch.object(live, "run_experiment") as experiment:
            with self.assertRaisesRegex(check.HeadCheckError, "HEAD_CHECK_FAILED"):
                mod.execute(type("Api", (), {"token": "private-test-token"})(), plan(),
                            self.output / "private", self.output)
            discovery.assert_not_called()
            experiment.assert_not_called()
    def test_timeout_is_bounded_and_never_retries(self):
        self.api.status = "in_progress"
        ticks = iter([0, 0, 0, 2])
        with self.assertRaisesRegex(check.HeadCheckError, "HEAD_CHECK_TIMEOUT"):
            self.run_check(clock=lambda: next(ticks), timeout=1)
        self.assertEqual(self.api.dispatches, 1)
        self.assertEqual(self.api.merges, 0)

if __name__ == "__main__":
    unittest.main()
