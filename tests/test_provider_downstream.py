"""Exercise the full provider path with a simulated receiver and real signatures.

This fixture is never evidence that a live GitHub mutation took place.
"""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from openline_wallet.crypto import sign_record
from openline_wallet.github_effect_live import run_experiment
ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "wallet/tests/test_github_effect.py"
FIXTURE_SPEC = importlib.util.spec_from_file_location("wallet_provider_fixture", FIXTURE_PATH)
FIXTURE = importlib.util.module_from_spec(FIXTURE_SPEC)
FIXTURE_SPEC.loader.exec_module(FIXTURE)
FakeGitHub, TARGET = FIXTURE.FakeGitHub, FIXTURE.TARGET
SPEC = importlib.util.spec_from_file_location("sandbox_launcher", ROOT / "scripts/provider_live.py")
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

def plan():
    return dict(repository=TARGET.repository, repository_id=TARGET.repository_id,
                number=TARGET.number, head_sha=TARGET.head_sha,
                base_ref=TARGET.base_ref, base_sha=TARGET.base_sha)

class ProviderReads:
    def __init__(self, client):
        self.client = client
        self.observations = []
    def pr(self, number):
        if number != TARGET.number:
            raise AssertionError("wrong target")
        return self.client.pr(TARGET)
    def commit(self, sha):
        return self.client.commit(TARGET, sha)

class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.client = FakeGitHub()
        self.api = ProviderReads(self.client)
        self.result = run_experiment(self.client, TARGET, self.root / "private",
                                     self.root / "public", transport="fixture")
        self.assertEqual(self.result["verdict"], "CONTROLLED_TRANSPORT_BOUNDARY_ENFORCED")
        self.assertEqual(self.result["merge_requests"], 1)
        # Re-sign a disposable copy solely to traverse the live-verifier branch.
        path = self.root / "public" / "result.json"
        record = json.loads(path.read_text())
        record.update(transport="github", verdict="LIVE_GITHUB_MERGE_OBSERVED")
        record = sign_record({k:v for k,v in record.items()
                              if k not in ("signature","payload_hash")},
                             Ed25519PrivateKey.generate())
        path.write_text(json.dumps(record))
        self.evidence = {p.stem: json.loads(p.read_text())
                         for p in (self.root / "public").glob("*.json")}
        self.evidence["directory"] = self.root / "public"

    def test_complete_signed_path_and_provider_reconciliation(self):
        result = mod.verify_observation(self.evidence, plan(), self.api)
        self.assertEqual(result["scope"], "ONE_DISPOSABLE_PR_HELD_ACKNOWLEDGEMENT")
        self.assertEqual(result["merge_commit_sha"], self.result["after_b"]["merge_commit_sha"])
        self.assertEqual(self.client.mutation_count, 1)

    def test_unsigned_or_modified_result_rejected(self):
        evidence = dict(self.evidence)
        evidence["result"] = dict(evidence["result"], verdict="INCONCLUSIVE")
        with self.assertRaisesRegex(mod.ExperimentError, "RESULT_SIGNATURE_INVALID"):
            mod.verify_observation(evidence, plan())

    def test_wrong_wallet_principal_rejected(self):
        evidence = dict(self.evidence)
        evidence["revoked_b"] = dict(evidence["revoked_b"])
        evidence["revoked_b"]["principal"] = dict(evidence["revoked_b"]["principal"])
        evidence["revoked_b"]["principal"]["principal_id"] = "wrong"
        with self.assertRaises(Exception):
            mod.verify_observation(evidence, plan())

    def test_wrong_gate_or_closure_target_rejected(self):
        evidence = copy.deepcopy({k:v for k,v in self.evidence.items() if k!="directory"})
        evidence["directory"] = self.evidence["directory"]
        evidence["closure_b"]["gate_id"] = "other"
        with self.assertRaisesRegex(mod.ExperimentError, "CLOSURE_BINDING_INVALID|SIGNED_EVIDENCE_INVALID"):
            mod.verify_observation(evidence, plan())

    def test_timing_order_rejected(self):
        evidence = copy.deepcopy({k:v for k,v in self.evidence.items() if k!="directory"})
        evidence["directory"] = self.evidence["directory"]
        evidence["timing"]["closure_returned_ns"] = 0
        with self.assertRaisesRegex(mod.ExperimentError, "CLOSURE_TIMING_INVALID"):
            mod.verify_observation(evidence, plan())

    def test_wrong_effect_parent_rejected(self):
        evidence = copy.deepcopy({k:v for k,v in self.evidence.items() if k!="directory"})
        evidence["directory"] = self.evidence["directory"]
        evidence["effect_b"]["effect_receipt"]["merge_commit"]["parents"][1] = "d"*40
        with self.assertRaises(Exception):
            mod.verify_observation(evidence, plan())

    def test_missing_evidence_file_rejected(self):
        (self.root / "public" / "closure_b.json").unlink()
        with self.assertRaisesRegex(mod.ExperimentError, "EVIDENCE_FILE_SET_MISMATCH"):
            mod.verify_observation(self.evidence, plan())

    def test_final_provider_identity_mismatch_rejected(self):
        self.client.head = "d"*40
        with self.assertRaisesRegex(mod.ExperimentError, "PROVIDER_FINAL_STATE_MISMATCH"):
            mod.verify_observation(self.evidence, plan(), self.api)

    def test_prior_failed_attempts_are_not_rewritten(self):
        records = ROOT / "proofs/provider-effect-live-001"
        a=json.loads((records/"attempt-1.json").read_text())
        b=json.loads((records/"attempt-2.json").read_text())
        self.assertEqual(a["verdict"], "INCONCLUSIVE")
        self.assertEqual(b["verdict"], "INCONCLUSIVE")
        self.assertEqual(a["bootstrap_mutations"], 0)
        self.assertEqual(b["bootstrap_mutations"], 4)
        self.assertEqual(b["provider_merge_requests"], 0)

if __name__ == "__main__":
    unittest.main()
