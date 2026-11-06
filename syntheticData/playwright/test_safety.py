import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from safety import run_bounded, safe_message, save_json, compare_payload, visit_errors, check_server_identity, retained_favorites


class SafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_failure_stops_queued_users(self):
        started = []
        async def worker(value):
            started.append(value)
            if value == 0:
                raise RuntimeError('failure')
        results = await run_bounded(list(range(10)), worker, 1)
        self.assertEqual(started, [0])
        self.assertTrue(any(isinstance(r, RuntimeError) for r in results))

    async def test_inflight_users_finish_after_another_fails(self):
        started, finished = [], []
        async def worker(value):
            started.append(value)
            await asyncio.sleep(0.01 if value == 0 else 0.03)
            if value == 0:
                raise RuntimeError('failure')
            finished.append(value)
        await run_bounded(list(range(10)), worker, 2)
        self.assertEqual(started, [0, 1])
        self.assertEqual(finished, [1])

    def test_password_is_removed_from_error(self):
        self.assertNotIn('dummy-password', safe_message(RuntimeError('fill("dummy-password") failed'), 'dummy-password'))

    def test_wrong_server_or_collection_is_refused_before_browser_actions(self):
        expected = {'run_id': 'run1', 'instance_id': 'instance1'}
        good = dict(expected, collection='simulation')
        check_server_identity(expected, good)
        for bad in (dict(good, collection='events'), dict(good, instance_id='other')):
            with self.assertRaises(ValueError):
                check_server_identity(expected, bad)

    def test_replayed_browse_keeps_previously_saved_favorites(self):
        self.assertEqual(retained_favorites(['old-show'], ['new-show', 'old-show']), ['new-show', 'old-show'])

    def test_atomic_save_retries_temporary_windows_lock(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'state.json'
            original = Path.replace
            calls = []
            def replace(source, target):
                calls.append(1)
                if len(calls) == 1:
                    raise PermissionError('temporary lock')
                return original(source, target)
            with patch.object(Path, 'replace', replace):
                save_json(path, {'value': 1})
            self.assertEqual(json.loads(path.read_text()), {'value': 1})
            self.assertEqual(len(calls), 2)

    def test_payload_comparison_detects_wrong_props_and_session(self):
        event = {'event_id': 'e', 'type': 'performance_view', 'occurred_at': '2026-11-06T05:00:00Z',
                 'session_id': 's', 'anonymous_id': 'a', 'schema_version': 1,
                 'page': {'path': '/', 'referrer': ''}, 'props': {'performance_id': 'jazz'}}
        self.assertEqual(compare_payload(event, event), [])
        self.assertIn('session_id', compare_payload(event, dict(event, session_id='wrong')))
        self.assertIn('props', compare_payload(event, dict(event, props={'performance_id': 'wrong'})))

    def test_visit_validation_detects_missing_views_and_wrong_reservation(self):
        visit = {'plan': {'outcome': 'purchase', 'category': '콘서트', 'views': 1},
                 'views': [{'performance_id': 'jazz', 'category': '콘서트'}],
                 'reservations': [{'id': 'r', 'performance_id': 'jazz', 'quantity': 2}],
                 'session_id': 's'}
        events = [{'type': kind, 'session_id': 's', 'props': props} for kind, props in [
            ('login', {}), ('logout', {}), ('category_select', {'category': '콘서트'}),
            ('performance_view', {'performance_id': 'jazz', 'category': '콘서트'}),
            ('booking_start', {}), ('reservation_request', {'reservation_id': 'wrong'}),
            ('payment_complete', {'reservation_id': 'wrong'}),
        ]]
        errors = visit_errors(visit, events)
        self.assertTrue(any('reservation' in e for e in errors))
        self.assertTrue(any('views' in e for e in visit_errors(visit, [])))


if __name__ == '__main__':
    unittest.main()
