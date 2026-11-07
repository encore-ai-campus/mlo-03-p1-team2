import tempfile
import unittest
import asyncio
import time
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

from syntheticData.playwright.loadControl import Metrics
from syntheticData.playwright.loadTest import Campaign, stage_plan, spike_vus, write_report, email, auth_resume_allowed, token_activation_delay


class RunTests(unittest.TestCase):
    def test_fresh_tokens_wait_past_issuance_but_large_clock_skew_fails_closed(self):
        import json
        import base64
        def token(iat):
            return 'header.' + base64.urlsafe_b64encode(json.dumps({'iat': iat}).encode()).decode().rstrip('=') + '.signature'
        self.assertAlmostEqual(token_activation_delay(token(100), 99.994), .106, places=3)
        self.assertEqual(token_activation_delay(token(100), 101), 0)
        with self.assertRaises(RuntimeError):
            token_activation_delay(token(200), 100)

    def test_new_profiles_do_not_reuse_the_legacy_signup_namespace(self):
        self.assertEqual(email({'email': 'persona0100@example.com'}), 'persona0100+synthetic@example.com')
        self.assertEqual(email({'email': 'persona0101@example.com'}), 'persona0101+synthetic-load@example.com')
        self.assertEqual(email({'email': 'persona0300@example.com'}), 'persona0300+synthetic-load@example.com')

    def test_only_audited_account_only_failures_can_resume(self):
        state = dict(started_at='2026-11-06T21:01:27+09:00', stages=[], reservations=[],
                     stop_reason='ApiFailure: POST /auth/login: HTTP 401',
                     evidence={'deltas': {'users': 0, 'reservations': 0, 'tracking': 100}, 'total': 100, 'issues': []})
        budget = dict(committed=[100, 100], pending={})
        self.assertTrue(auth_resume_allowed(state, budget))
        state['reservations'] = ['already-written']
        self.assertFalse(auth_resume_allowed(state, budget))
        state['reservations'] = []
        budget['pending'] = {'unknown': [5, 0]}
        self.assertFalse(auth_resume_allowed(state, budget))

    def test_account_creation_io_failure_requires_exact_database_ledger_match(self):
        state = dict(started_at='2026-11-06T21:01:27+09:00', stages=[], reservations=[],
                     stop_reason='Local state I/O error: PermissionError',
                     evidence={'deltas': {'users': 185, 'reservations': 0, 'tracking': 568}, 'total': 753, 'issues': []})
        budget = dict(committed=[753, 568], pending={})
        self.assertTrue(auth_resume_allowed(state, budget))
        state['evidence']['deltas']['users'] = 186
        self.assertFalse(auth_resume_allowed(state, budget))

    def test_existing_browser_campaign_is_rejected_before_any_artifact_write(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            directory = root / 'old'
            directory.mkdir()
            (directory / 'state.json').write_text('{}')
            (directory / 'profiles-input.json').write_text('original-input')
            with patch('syntheticData.playwright.loadTest.ARTIFACTS', root):
                with self.assertRaises(ValueError):
                    Campaign('old')
            self.assertEqual((directory / 'profiles-input.json').read_text(), 'original-input')
            self.assertFalse((directory / 'budget.json').exists())

    def test_progressive_stage_limits_and_spike_recovery(self):
        plan = stage_plan()
        self.assertEqual([s['vus'] for s in plan if s['name'].startswith('mixed-')],
                         [10, 25, 50, 100, 150, 200, 300])
        self.assertTrue(all(s['vus'] <= 300 for s in plan))
        self.assertEqual(plan[-1]['seconds'], 1800)
        for peak in (25, 100, 300):
            self.assertEqual(spike_vus(110, peak), peak)
            self.assertEqual(spike_vus(150, peak), 5)
            self.assertTrue(all(1 <= spike_vus(t / 10, peak) <= peak for t in range(3000)))

    def test_preparation_report_does_not_expose_credentials_or_invent_results(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'docs').mkdir()
            directory = root / 'artifacts/run'
            directory.mkdir(parents=True)
            state = dict(run_id='test', phase='PREPARED', credentials={'email': 'private-password'},
                         stages=[], samples=[], preparation_notes=[])
            with patch('syntheticData.playwright.loadTest.ROOT', root):
                write_report(state, Metrics(), directory)
            report = (root / 'docs/loadTestResult.md').read_text(encoding='utf-8')
            self.assertNotIn('private-password', report)
            self.assertNotIn('credentials', report)
            self.assertIn('PREPARED', report)
            self.assertNotIn('| **', report)


class MonitoringDeadlineTests(unittest.IsolatedAsyncioTestCase):
    async def test_stalled_monitor_does_not_block_sampler_or_stop_signal(self):
        async def blocked(_):
            await asyncio.sleep(10)
        with tempfile.TemporaryDirectory() as d, patch('syntheticData.playwright.loadTest.ARTIFACTS', Path(d)):
            campaign = Campaign('test-monitor')
            campaign.http = object()
            campaign.api = SimpleNamespace(epoch=time.monotonic(), inflight=0)
            spec = dict(name='test', mode='mixed', vus=1, seconds=5)
            started = time.monotonic()
            with patch('syntheticData.playwright.loadTest.collect', blocked), patch('syntheticData.playwright.loadTest.MONITOR_TIMEOUT', .02):
                await asyncio.wait_for(asyncio.gather(campaign.sample(spec, started),
                                                      campaign.resource_watch(spec, started)), timeout=.5)
            self.assertTrue(campaign.stop.is_set())
            self.assertGreaterEqual(len(campaign.state['samples']), 1)
