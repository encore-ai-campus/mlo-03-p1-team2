import tempfile
import unittest
from pathlib import Path

import httpx

from syntheticData.playwright.loadClient import Api, ApiFailure
from syntheticData.playwright.loadControl import Budget, Metrics


class ClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_favorite_204_success_is_not_parsed_as_json(self):
        with tempfile.TemporaryDirectory() as d:
            budget = Budget(Path(d) / 'b.json')
            async with httpx.AsyncClient(transport=httpx.MockTransport(
                    lambda req: httpx.Response(204))) as client:
                api = Api(client, 'https://example.test', budget, Metrics(), Path(d) / 'requests.jsonl')
                result = await api.call('PUT', '/favorites/city', total=1, expected=(204,))
            self.assertIsNone(result)
            self.assertEqual(budget.used(), (1, 0))

    async def test_tracking_counts_only_inserted_documents(self):
        with tempfile.TemporaryDirectory() as d:
            budget = Budget(Path(d) / 'b.json')
            async with httpx.AsyncClient(transport=httpx.MockTransport(
                    lambda req: httpx.Response(202, json={'accepted': 2, 'duplicates': 1}))) as client:
                api = Api(client, 'https://example.test', budget, Metrics(), Path(d) / 'requests.jsonl')
                await api.call('POST', '/tracking/events', payload={'events': [{}, {}, {}]},
                               total=3, tracking=3, expected=(202,))
            self.assertEqual(budget.used(), (2, 2))

    async def test_timeout_keeps_reserved_rows_and_records_failure(self):
        with tempfile.TemporaryDirectory() as d:
            budget = Budget(Path(d) / 'b.json')
            def fail(req):
                raise httpx.ReadTimeout('unknown commit outcome')
            metrics = Metrics()
            async with httpx.AsyncClient(transport=httpx.MockTransport(fail)) as client:
                api = Api(client, 'https://example.test', budget, metrics, Path(d) / 'requests.jsonl')
                with self.assertRaises(ApiFailure):
                    await api.call('POST', '/reservations', total=5, expected=(201,))
            self.assertEqual(budget.used(), (5, 0))
            self.assertFalse(metrics.rows[-1]['ok'])

    async def test_invalid_tracking_ack_cannot_be_treated_as_success(self):
        with tempfile.TemporaryDirectory() as d:
            budget = Budget(Path(d) / 'b.json')
            async with httpx.AsyncClient(transport=httpx.MockTransport(
                    lambda req: httpx.Response(202, json={'accepted': 0, 'duplicates': 0}))) as client:
                api = Api(client, 'https://example.test', budget, Metrics(), Path(d) / 'requests.jsonl')
                with self.assertRaises(ApiFailure):
                    await api.call('POST', '/tracking/events', payload={'events': [{}]}, total=1,
                                   tracking=1, expected=(202,))
            self.assertEqual(budget.used(), (1, 1))
