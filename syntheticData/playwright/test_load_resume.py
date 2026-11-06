"""Recovery must prove database/ledger agreement before sending new traffic."""
import copy
import unittest
import tempfile
import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from syntheticData.playwright.load_test import Campaign, load_resume_plan, stage_plan, idle_restart_hosts, digest, email


class ResumePlanTests(unittest.TestCase):
    def setUp(self):
        self.state = dict(started_at='2026-11-06T21:01:27+09:00', finished_at=None,
                          stop_reason=None, phase='mixed-50',
                          stages=[dict(name=s['name'], vus=s['vus'], passed=True)
                                  for s in stage_plan()[:4]])
        self.budget = dict(committed=[2680, 2014], pending={}, total_limit=100000, tracking_limit=50000)
        self.evidence = dict(total=2680, retained_total=2665, deltas={'tracking': 2014}, issues=[])

    def plan(self):
        return load_resume_plan(self.state, self.budget, self.evidence)

    def test_only_unfinished_stages_are_selected_without_mutating_evidence(self):
        original = copy.deepcopy(self.state)
        result = self.plan()
        self.assertEqual(result[0]['name'], 'mixed-50')
        self.assertEqual(result[-1]['name'], 'soak')
        self.assertEqual(result[-1]['seconds'], 1800)
        self.assertEqual(self.state, original)

    def test_uncertain_writes_or_mismatched_database_are_rejected(self):
        for mutate in (
            lambda: self.budget['pending'].update(unknown=[5, 0]),
            lambda: self.evidence.update(total=2681),
            lambda: self.evidence['deltas'].update(tracking=2015),
            lambda: self.evidence['issues'].append('missing reservation'),
            lambda: self.budget.update(total_limit=200000),
        ):
            self.setUp()
            mutate()
            with self.assertRaises(RuntimeError):
                self.plan()

    def test_stop_conditions_or_finished_runs_are_not_bypassed(self):
        for key, value in [('stop_reason', 'database_connections_exhausted'),
                           ('finished_at', '2026-11-06T22:00:00+09:00')]:
            self.setUp()
            self.state[key] = value
            with self.assertRaises(RuntimeError):
                self.plan()


    def test_missing_failed_or_out_of_order_stages_are_rejected(self):
        for mutate in (
            lambda: self.state['stages'][0].update(passed=False),
            lambda: self.state['stages'].pop(1),
            lambda: self.state.update(phase='mixed-300'),
            lambda: self.state['stages'][0].update(vus=300),
        ):
            self.setUp()
            mutate()
            with self.assertRaises(RuntimeError):
                self.plan()


class ResumeExecutionTests(unittest.IsolatedAsyncioTestCase):
    async def test_preparation_only_does_not_commit_restart_recovery_and_execution_still_works(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'docs').mkdir()
            profiles = [dict(id=f'persona{i:04}', email=f'persona{i:04}@example.com', name=f'User {i}', mbti='INTJ')
                        for i in range(1, 301)]
            source = root / 'profiles.json'
            source.write_text(json.dumps({'users': profiles}), encoding='utf-8')
            initial = ResumePlanTests()
            initial.setUp()
            for stage in initial.state['stages']:
                stage.update(elapsed=300, requests=100, error_rate=0, p95=10)
            initial.state.update(run_id='test-resume', profile_sha256=digest(source), reservations=[],
                samples=[], favorite_removals=[], preparation_notes=[],
                credentials={email(p): 'local-test-password' for p in profiles},
                account_map={email(p): p['id'] for p in profiles}, baseline={})
            evidence = dict(total=10, retained_total=10, deltas={'tracking': 6, 'reservations': 0}, issues=[])
            members = {email(p): dict(id=p['id'], name=p['name'], mbti=p['mbti'], consent=True) for p in profiles}
            fake_evidence = SimpleNamespace(members=lambda: members, verify=lambda *args: evidence,
                query=lambda sql, **kw: [dict(id=kw['id'], title=kw['id'])])
            start = datetime.fromisoformat(initial.state['started_at']).timestamp()
            def sample(boot):
                return {'metrics': {'boot_time': [dict(metric={'instance': '192.168.0.175:9100'}, value=[0, str(boot)])]}}
            before, current = sample(start-100), sample(start+200)
            async def get(url):
                pid = url.rsplit('/', 1)[-1]
                return SimpleNamespace(raise_for_status=lambda: None,
                    json=lambda: dict(id=pid, title=pid, available_dates=['2026-11-06'], slots=['18:00']))
            with (patch('syntheticData.playwright.load_test.ARTIFACTS', root / 'artifacts'),
                  patch('syntheticData.playwright.load_test.ROOT', root),
                  patch('syntheticData.playwright.load_test.PROFILES', source),
                  patch('syntheticData.playwright.load_test.Evidence', return_value=fake_evidence),
                  patch('syntheticData.playwright.load_test.collect', AsyncMock(return_value=current)),
                  patch('syntheticData.playwright.load_test.monitoring_reason',
                        side_effect=lambda a,b: 'critical_host_restarted' if a != b else None),
                  patch('syntheticData.playwright.load_test.asyncio.sleep', AsyncMock())):
                campaign = Campaign('test-resume')
                campaign.state = initial.state
                campaign.budget.data.update(committed=[10, 6])
                campaign.persist()
                campaign.budget.path.write_text(json.dumps(campaign.budget.data))
                (campaign.directory / 'profiles-input.json').write_bytes(source.read_bytes())
                baseline = campaign.directory / 'monitoring-baseline.json'
                baseline.write_text(json.dumps(before))
                row = dict(at=100, stage='mixed-50', api='GET /performances', ms=10, ok=True, kind='read')
                (campaign.directory / 'requests.jsonl').write_text(json.dumps(row)+'\n')
                original = copy.deepcopy(campaign.state)
                await campaign.prepare_load_resume(SimpleNamespace(get=get), recover_idle_restart=True, execute=False)
                self.assertEqual(campaign.state, original)
                self.assertEqual(json.loads(baseline.read_text()), before)
                reloaded = Campaign('test-resume')
                await reloaded.prepare_load_resume(SimpleNamespace(get=get), recover_idle_restart=True, execute=True)
                self.assertEqual(reloaded.resume_plan[0]['name'], 'smoke')
                self.assertEqual(reloaded.state['stage_segment_start'], 4)
                self.assertEqual(reloaded.budget.data['committed'], [10, 6])

    async def test_existing_account_disappearing_never_causes_signup_on_resume(self):
        with tempfile.TemporaryDirectory() as directory, patch(
                'syntheticData.playwright.load_test.ARTIFACTS', Path(directory)):
            campaign = Campaign('test-resume')
            campaign.profiles = [dict(email='persona0001@example.com')]
            campaign.evidence = SimpleNamespace(members=lambda: {})
            campaign.state['credentials'] = {'persona0001+synthetic@example.com': 'test-password'}
            campaign.api = SimpleNamespace(call=AsyncMock())
            with self.assertRaisesRegex(RuntimeError, 'no signup allowed'):
                await campaign.authenticate(allow_signup=False)
            campaign.api.call.assert_not_awaited()

    async def test_resume_execute_requires_prior_audit(self):
        with tempfile.TemporaryDirectory() as directory, patch(
                'syntheticData.playwright.load_test.ARTIFACTS', Path(directory)):
            campaign = Campaign('test-resume')
            with self.assertRaisesRegex(RuntimeError, 'read-only preparation'):
                await campaign.execute(object(), resume_load=True)


class IdleRestartTests(unittest.TestCase):
    def test_only_restarts_after_the_last_recorded_request_allow_a_new_segment(self):
        def sample(boot):
            return {'metrics': {'boot_time': [
                {'metric': {'instance': '192.168.0.175:9100'}, 'value': [0, str(boot)]}]}}
        state = {'started_at': '2026-11-06T12:00:00+00:00'}
        start = 1793966400
        rows = [{'at': 100}]
        self.assertEqual(idle_restart_hosts(state, rows, sample(start-100), sample(start+200)),
                         ['192.168.0.175:9100'])
        with self.assertRaisesRegex(RuntimeError, 'during measured traffic'):
            idle_restart_hosts(state, rows, sample(start-100), sample(start+50))
        with self.assertRaisesRegex(RuntimeError, 'No critical host restart'):
            idle_restart_hosts(state, rows, sample(start-100), sample(start-100))

