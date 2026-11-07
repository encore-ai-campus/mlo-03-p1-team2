import asyncio
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from syntheticData.playwright.loadControl import Budget, BudgetExceeded, Metrics, stage_limit, save


class BudgetTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_persistence_cannot_admit_a_request_or_consume_phantom_rows(self):
        with tempfile.TemporaryDirectory() as d:
            b = Budget(Path(d) / 'budget.json')
            with patch('syntheticData.playwright.loadControl.save', side_effect=PermissionError):
                with self.assertRaises(PermissionError):
                    b.reserve(2, 2)
            self.assertEqual(b.used(), (0, 0))

    async def test_transient_windows_replace_lock_is_retried_before_admitting_write(self):
        import os
        import json
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'state.json'
            save(path, {'value': 'old'})
            replace = os.replace
            attempts = []
            def locked_once(source, target):
                attempts.append(1)
                if len(attempts) == 1:
                    raise PermissionError('transient reader lock')
                return replace(source, target)
            with patch('syntheticData.playwright.loadControl.os.replace', locked_once):
                save(path, {'value': 'new'})
            self.assertEqual(json.loads(path.read_text())['value'], 'new')
            self.assertEqual(len(attempts), 2)

    async def test_parallel_writers_cannot_overrun_global_limit(self):
        with tempfile.TemporaryDirectory() as d:
            budget = Budget(Path(d) / 'budget.json', total_limit=10, tracking_limit=6)
            async def writer():
                try:
                    ticket = budget.reserve(3, 2)
                    await asyncio.sleep(0)
                    budget.settle(ticket, 3, 2)
                    return True
                except BudgetExceeded:
                    return False
            accepted = await asyncio.gather(*(writer() for _ in range(20)))
            self.assertEqual(sum(accepted), 3)
            self.assertEqual(budget.used(), (9, 6))

    async def test_uncertain_writes_survive_restart_and_keep_their_budget(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'budget.json'
            b = Budget(p, total_limit=10, tracking_limit=10)
            ticket = b.reserve(8, 0)
            restored = Budget(p, total_limit=10, tracking_limit=10)
            self.assertEqual(restored.used(), (8, 0))
            with self.assertRaises(BudgetExceeded):
                restored.reserve(3, 0)
            restored.settle(ticket, 5, 0)
            self.assertEqual(restored.used(), (5, 0))

    async def test_invalid_settlement_does_not_release_reserved_capacity(self):
        with tempfile.TemporaryDirectory() as d:
            b = Budget(Path(d) / 'b.json', total_limit=10, tracking_limit=5)
            t = b.reserve(5, 0)
            with self.assertRaises(ValueError):
                b.settle(t, 6, 0)
            self.assertEqual(b.used(), (5, 0))
            with self.assertRaises(ValueError):
                b.reserve(-1, 0)


class MetricsTests(unittest.TestCase):
    def test_slow_errors_cannot_hide_behind_fast_successes(self):
        m = Metrics()
        for i in range(100):
            m.add(i / 4, 'GET detail', 40, True, 'read')
        for i in range(10):
            m.add(26 + i / 4, 'POST booking', 20, False, 'write')
        self.assertIn('error', m.stop_reason(30))

    def test_latency_guard_and_api_specific_stage_gate(self):
        m = Metrics()
        for i in range(10):
            m.add(i * 7, 'POST booking', 1100, True, 'write')
        self.assertIsNone(m.stop_reason(64))
        self.assertFalse(stage_limit(m.rows)['passed'])
        m.add(64, 'POST booking', 5000, True, 'write')
        m.add(65, 'POST booking', 5000, True, 'write')
        self.assertIn('latency', m.stop_reason(66))


if __name__ == '__main__':
    unittest.main()
