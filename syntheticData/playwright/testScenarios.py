import copy
import json
from pathlib import Path
import unittest

from scenarios import build_plan, synthetic_email, tag_events, check_resume, session_pending


USERS = json.loads((Path(__file__).resolve().parents[1] / 'personas.json').read_text(encoding='utf-8'))['users']


class ScenarioTests(unittest.TestCase):
    def test_email_alias_keeps_original_and_marks_synthetic(self):
        self.assertEqual(synthetic_email('persona0001@example.com'), 'persona0001+synthetic@example.com')
        with self.assertRaises(ValueError):
            synthetic_email('real@gmail.com')

    def test_plan_is_reproducible_and_stable_when_expanded(self):
        full = build_plan(USERS, 42)
        self.assertEqual(full, build_plan(USERS, 42))
        self.assertEqual(build_plan(USERS[:3], 42), full[:3])
        self.assertNotEqual(full, build_plan(USERS, 43))

    def test_pilot_has_three_distinct_paths(self):
        plan = build_plan(USERS[:3], 42)
        self.assertEqual([p['sessions'][0]['outcome'] for p in plan], ['view_only', 'booking_abandon', 'purchase'])

    def test_frequency_and_companion_affect_plan_without_mutating_profiles(self):
        original = copy.deepcopy(USERS)
        for user, account in zip(USERS, build_plan(USERS, 42)):
            style = user['viewing_style']
            self.assertEqual(len(account['sessions']), {'occasional': 1, 'monthly': 2, 'frequent': 3}[style['attendance_frequency']])
            for session in account['sessions']:
                self.assertIn(session['category'], user['category_weights'])
                self.assertGreaterEqual(session['quantity'], 1)
                self.assertLessEqual(session['quantity'], 4)
                if style['companion'] == 'solo':
                    self.assertEqual(session['quantity'], 1)
        self.assertEqual(USERS, original)

    def test_weights_control_category_selection(self):
        users = copy.deepcopy(USERS)
        for user in users:
            user['category_weights'] = {'전시': 100, '스포츠': 0}
        self.assertTrue(all(s['category'] == '전시' for p in build_plan(users, 42) for s in p['sessions']))

    def test_tracking_tags_are_flat_and_do_not_mutate_events(self):
        event = {'event_id': 'original', 'type': 'login', 'props': {}}
        tagged = tag_events([event], {'run_id': 'run1', 'persona_id': 'p1', 'scenario': 'purchase'})
        self.assertTrue(tagged[0]['props']['synthetic'])
        self.assertEqual(tagged[0]['props']['synthetic_persona_id'], 'p1')
        self.assertEqual(tagged[0]['event_id'], 'original')
        self.assertEqual(event['props'], {})
        with self.assertRaises(ValueError):
            tag_events([dict(event, props={str(i): 1 for i in range(17)})], {'run_id': 'r', 'persona_id': 'p', 'scenario': 's'})

    def test_resume_rejects_changed_target_or_profiles(self):
        state = {'fingerprint': {'base_url': 'http://127.0.0.1:5174', 'profiles_sha256': 'a', 'seed': 42}}
        check_resume(state, dict(state['fingerprint']))
        with self.assertRaises(ValueError):
            check_resume(state, dict(state['fingerprint'], profiles_sha256='b'))

    def test_resume_skips_completed_but_refuses_uncertain_sessions(self):
        self.assertTrue(session_pending(None))
        self.assertFalse(session_pending({'status': 'complete'}))
        for status in ('in_progress', 'failed'):
            with self.assertRaises(ValueError):
                session_pending({'status': status})


if __name__ == '__main__':
    unittest.main()
