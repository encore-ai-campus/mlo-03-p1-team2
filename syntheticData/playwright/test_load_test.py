import tempfile
import unittest
import asyncio
import time
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

from syntheticData.playwright.load_control import Metrics
from syntheticData.playwright.load_test import Campaign, stage_plan, spike_vus, write_report


class RunTests(unittest.TestCase):
    def test_existing_browser_campaign_is_rejected_before_any_artifact_write(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            directory = root / 'old'
            directory.mkdir()
            (directory / 'state.json').write_text('{}')
            (directory / 'profiles-input.json').write_text('original-input')
            with patch('syntheticData.playwright.load_test.ARTIFACTS', root):
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
            with patch('syntheticData.playwright.load_test.ROOT', root):
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
        with tempfile.TemporaryDirectory() as d, patch('syntheticData.playwright.load_test.ARTIFACTS', Path(d)):
            campaign = Campaign('test-monitor')
            campaign.http = object()
            campaign.api = SimpleNamespace(epoch=time.monotonic(), inflight=0)
            spec = dict(name='test', mode='mixed', vus=1, seconds=5)
            started = time.monotonic()
            with patch('syntheticData.playwright.load_test.collect', blocked), patch('syntheticData.playwright.load_test.MONITOR_TIMEOUT', .02):
                await asyncio.wait_for(asyncio.gather(campaign.sample(spec, started),
                                                      campaign.resource_watch(spec, started)), timeout=.5)
            self.assertTrue(campaign.stop.is_set())
            self.assertGreaterEqual(len(campaign.state['samples']), 1)
