import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('provider_live', ROOT/'scripts/provider_live.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
A = 'a'*40
B = 'b'*40
C = 'c'*40


class FakeAPI:
    def __init__(self):
        self.mutations=[]
        self.observations=[]
        self.repository_id=12345
        self.bad_marker=False
        self.fail_at=None
        self.refs={}
    def repo(self):
        return {'full_name':mod.SANDBOX,'owner':{'login':'terryncew'},'id':self.repository_id,
                'fork':False,'archived':False,'default_branch':'main'}
    def marker(self):
        value={'schema':mod.MARKER,'repository':mod.SANDBOX,
               'purpose':'Disposable GitHub merge experiments; no production data'}
        if self.bad_marker: value['repository']='terryncew/openline-wallet'
        return value
    def ref(self,name):
        return {'object':{'sha':A}}
    def create_ref(self,name,sha):
        self.mutations.append(('POST','refs/heads/'+name))
        if self.fail_at == len(self.mutations): raise mod.ExperimentError('GITHUB_TRANSPORT_UNCERTAIN')
        self.refs[name]=sha
    def put_test_file(self,branch,run_id,content):
        self.mutations.append(('PUT',branch))
        if self.fail_at == len(self.mutations): raise mod.ExperimentError('GITHUB_TRANSPORT_UNCERTAIN')
        return {'commit':{'sha':B}}
    def create_pr(self,head,base,run_id):
        self.mutations.append(('POST','pulls'))
        if self.fail_at == len(self.mutations): raise mod.ExperimentError('GITHUB_TRANSPORT_UNCERTAIN')
        return {'number':7,'base':{'ref':base},'head':{'sha':B}}


class BootstrapTests(unittest.TestCase):
    def test_exact_disposable_target_only(self):
        api=FakeAPI()
        plan=mod.bootstrap(api,'123')
        self.assertEqual(plan['repository_id'],12345)
        self.assertEqual(plan['head_sha'],B)
        self.assertEqual(len(api.mutations),4)
        self.assertEqual(api.mutations[0],('POST','refs/heads/olp-test-123-base'))
        self.assertNotIn('main',str(api.mutations))
    def test_unmarked_repository_never_mutates(self):
        api=FakeAPI();api.bad_marker=True
        with self.assertRaisesRegex(mod.ExperimentError,'MARKER_INVALID'):
            mod.bootstrap(api,'123')
        self.assertEqual(api.mutations,[])
    def test_wrong_repository_id_type_never_mutates(self):
        api=FakeAPI();api.repository_id=True
        with self.assertRaisesRegex(mod.ExperimentError,'SANDBOX_IDENTITY_INVALID'):
            mod.bootstrap(api,'123')
        self.assertEqual(api.mutations,[])
    def test_run_id_rejects_untrusted_path_and_zero(self):
        for value in ['0','../main','1/2','-1','1\n2','1'*30]:
            with self.subTest(value=value):
                api=FakeAPI()
                with self.assertRaises(mod.ExperimentError): mod.bootstrap(api,value)
                self.assertEqual(api.mutations,[])
    def test_mutation_failure_does_not_retry(self):
        for failure in range(1,5):
            with self.subTest(failure=failure):
                api=FakeAPI();api.fail_at=failure
                with self.assertRaises(mod.ExperimentError):mod.bootstrap(api,'123')
                self.assertEqual(len(api.mutations),failure)
    def test_api_refuses_arbitrary_mutation(self):
        api=mod.GitHubAPI('disposable-test-token')
        for method,path,body in [('PUT','/pulls/7/merge',{'sha':A}),
                                  ('DELETE','/git/refs/heads/main',None),
                                  ('POST','/actions/workflows/ci.yml/dispatches',{}),
                                  ('GET','/../../admin',None)]:
            with self.subTest(path=path):
                with self.assertRaises(mod.ExperimentError):api.request(method,path,body)
        self.assertEqual(api.mutations,[])
    def test_confirmation_required_before_any_api(self):
        with self.assertRaisesRegex(mod.ExperimentError,'EXPLICIT_CONFIRMATION_REQUIRED'):
            mod.main(['--run-id','123','--output','/tmp/unused-a','--state','/tmp/unused-b',
                      '--confirm','yes'])
    def test_source_pin_is_merged_provider_commit(self):
        self.assertEqual(mod.SOURCE_COMMIT,'c35e7f427a26cddfc4e7d300a74b84aacc0ea64e')


class EvidenceTests(unittest.TestCase):
    def test_wrong_result_never_promotes_to_live(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)
            (path/'result.json').write_text('{}')
            with self.assertRaises(Exception):
                mod.verify_observation({'result':{'verdict':'CONTROLLED_TRANSPORT_BOUNDARY_ENFORCED'},
                                        'directory':path}, {})
    def test_hash_changes_are_detected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'evidence.json';p.write_text('{"value":1}')
            before=mod.digest(p.read_bytes())
            p.write_text('{"value":2}')
            self.assertNotEqual(before,mod.digest(p.read_bytes()))
    def test_no_redirect_handler(self):
        self.assertIsNone(mod.NoRedirect().redirect_request(None,None,302,'Found',{},'https://evil.example/'))


if __name__=='__main__':unittest.main()

class DispatchBoundaryTests(unittest.TestCase):
    def test_transport_uncertainty_records_one_attempt_without_secret(self):
        from urllib.error import URLError
        api=mod.GitHubAPI('private-test-token')
        class FailingOpener:
            def open(self,*args,**kwargs):raise URLError('connection lost')
        api.opener=FailingOpener()
        with self.assertRaisesRegex(mod.ExperimentError,'GITHUB_TRANSPORT_UNCERTAIN'):
            api.create_ref('olp-test-123-base',A)
        self.assertEqual(len(api.mutations),1)
        self.assertEqual(api.observations[0]['status'],'UNKNOWN')
        self.assertNotIn('private-test-token',json.dumps(api.observations))

    def test_execution_failure_reconciles_without_retry(self):
        import openline_wallet.github_effect_live as live
        api=FakeAPI();api.token='private-test-token'
        with tempfile.TemporaryDirectory() as td:
            public=Path(td)/'public';private=Path(td)/'private'
            public.mkdir();private.mkdir()
            with patch.object(mod,'wait_for_target',return_value=(type('Target',(),{'to_record':lambda self:{'repository':mod.SANDBOX,'number':7}})(),{})),\
                 patch.object(live,'run_experiment',side_effect=RuntimeError('uncertain')) as run,\
                 patch.object(live,'recover',return_value={'phases':[],'effect_authority':'NONE'}) as recover:
                with self.assertRaisesRegex(RuntimeError,'uncertain'):
                    mod.execute(api,{'repository':mod.SANDBOX,'number':7},private,public)
                run.assert_called_once()
                recover.assert_called_once()
            self.assertEqual(json.loads((public/'recovery-summary.json').read_text())['effect_authority'],'NONE')

    def test_failed_final_verification_never_reissues_mutation(self):
        import openline_wallet.github_effect_live as live
        api=FakeAPI();api.token='private-test-token'
        with tempfile.TemporaryDirectory() as td:
            public=Path(td)/'public';private=Path(td)/'private'
            public.mkdir();private.mkdir()
            with patch.object(mod,'wait_for_target',return_value=(type('Target',(),{'to_record':lambda self:{'repository':mod.SANDBOX,'number':7}})(),{})),\
                 patch.object(live,'run_experiment',return_value={'verdict':'LIVE_GITHUB_MERGE_OBSERVED'}) as run,\
                 patch.object(mod,'verify_observation',side_effect=mod.ExperimentError('BAD_EVIDENCE')),\
                 patch.object(live,'recover',return_value={'phases':[],'effect_authority':'NONE'}) as recover:
                with self.assertRaisesRegex(mod.ExperimentError,'BAD_EVIDENCE'):
                    mod.execute(api,{'repository':mod.SANDBOX,'number':7},private,public)
                run.assert_called_once()
                recover.assert_called_once()
