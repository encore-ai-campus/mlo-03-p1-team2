import asyncio
import tempfile
import unittest
from pathlib import Path

from syntheticData.playwright.load_control import Budget, BudgetExceeded, Metrics, stage_limit


class BudgetTests(unittest.IsolatedAsyncioTestCase):
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
