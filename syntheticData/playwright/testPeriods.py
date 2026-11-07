import copy
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import unittest

from periods import build_period_plan, period_tags, aggregate_periods, transaction_snapshot, transaction_event_errors, allocate_visit_counts, randomize_period_plan

# This suite verifies the original 100-person historical campaign.
USERS = json.loads((Path(__file__).resolve().parents[1] / 'personas.json').read_text(encoding='utf-8'))['users'][:100]


class PeriodTests(unittest.TestCase):
    def test_100_existing_personas_get_10_stable_visits_in_30_days(self):
        original = copy.deepcopy(USERS)
        plan = build_period_plan(USERS, date(2026, 10, 8), 30, 10, 99)
        self.assertEqual(len(plan), 100)
        self.assertEqual(sum(len(p['sessions']) for p in plan), 1000)
        self.assertEqual(plan[:3], build_period_plan(USERS[:3], date(2026, 10, 8), 30, 10, 99))
        ids = []
        all_days = set()
        for user, account in zip(USERS, plan):
            self.assertEqual(account['name'], user['name'])
            days = [s['simulation_date'] for s in account['sessions']]
            self.assertEqual(days, sorted(set(days)))
            self.assertEqual(len(days), 10)
            for session in account['sessions']:
                self.assertTrue('2026-10-08' <= session['simulation_date'] <= '2026-11-06')
                self.assertIn(session['category'], user['category_weights'])
                ids.append(session['visit_id'])
                all_days.add(session['simulation_date'])
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(all_days), 30)
        self.assertEqual(USERS, original)

    def test_temporal_tags_preserve_real_timestamp_and_use_kst_day(self):
        visit = {'visit_id': 'v', 'simulation_start': '2026-10-08T16:00:00+09:00'}
        event = {'event_id': 'e', 'occurred_at': '2026-11-06T06:00:05Z', 'props': {}}
        tagged = period_tags([event], visit, datetime(2026, 11, 6, 6, tzinfo=timezone.utc))
        self.assertEqual(event['props'], {})
        self.assertEqual(tagged[0]['occurred_at'], event['occurred_at'])
        self.assertEqual(tagged[0]['props']['simulation_date'], '2026-10-08')
        self.assertEqual(tagged[0]['props']['simulation_at'], '2026-10-08T07:00:05.000Z')
        self.assertEqual(tagged[0]['props']['simulation_at_kst'], '2026-10-08 16:00:05.000')
        self.assertTrue(tagged[0]['props']['simulation_time_is_fictional'])

    def test_props_limit_is_checked_after_all_tags(self):
        visit = {'visit_id': 'v', 'simulation_start': '2026-10-08T16:00:00+09:00'}
        with self.assertRaises(ValueError):
            period_tags([{'occurred_at':'2026-11-06T06:00:00Z','props':{str(i):i for i in range(16)}}],visit,
                        datetime(2026,11,6,6,tzinfo=timezone.utc))

    def test_daily_weekly_monthly_metrics_use_fictional_date_and_deduplicate_ids(self):
        events = []
        for kind, extra in [('login',{}),('performance_view',{}),('reservation_request',{'reservation_id':'r'}),
                            ('payment_complete',{'reservation_id':'r','amount_krw':50000})]:
            events.append({'event_id': kind, 'user_id':'u', 'type':kind, 'occurred_at':'2026-11-06T06:00:00Z',
                           'props':dict(extra,simulation_date='2026-10-08',synthetic_visit_id='v')})
        metrics=aggregate_periods(events + [events[-1]],date(2026,10,8),30)
        day=metrics['daily'][0]
        self.assertEqual(day['date'],'2026-10-08')
        self.assertEqual(day['visits'],1)
        self.assertEqual(day['users'],1)
        self.assertEqual(day['payments'],1)
        self.assertEqual(day['revenue_krw'],50000)
        self.assertEqual(len(metrics['daily']),30)
        self.assertEqual(sum(d['payments'] for d in metrics['weekly']),1)
        self.assertEqual(sum(d['payments'] for d in metrics['monthly']),1)

    def test_invalid_period_is_rejected(self):
        for days,visits in [(0,10),(5,10),(30,0)]:
            with self.assertRaises(ValueError):
                build_period_plan(USERS,date(2026,10,8),days,visits,99)

    def test_transaction_snapshot_includes_dates_quantity_status_and_payment_amount(self):
        from types import SimpleNamespace as NS
        def row(**values):
            return NS(**values,__table__=NS(columns=[NS(name=k) for k in values]))
        payment=row(amount=20000,status='COMPLETED',completed_at=datetime(2026,11,6,6,tzinfo=timezone.utc))
        reservation=row(quantity=2,status='CONFIRMED',performance_date=date(2026,11,14),amount=20000)
        reservation.payment=payment
        before=transaction_snapshot(reservation)
        self.assertEqual(before['reservation']['performance_date'],'2026-11-14')
        reservation.quantity=3
        self.assertNotEqual(before,transaction_snapshot(reservation))
        reservation.quantity=2
        payment.amount=999
        self.assertNotEqual(before,transaction_snapshot(reservation))

    def test_event_revenue_and_references_are_checked_against_sql(self):
        snapshot={'reservation':{'id':'r','user_id':'u','performance_id':'p','category':'전시',
                                  'quantity':2,'amount':20000,'seat_grade':'STANDARD'},
                  'payment':{'amount':20000,'status':'COMPLETED'}}
        event={'type':'payment_complete','user_id':'u','props':{'reservation_id':'r','performance_id':'p',
                'category':'전시','quantity':2,'amount_krw':20000,'seat_grade':'STANDARD'}}
        self.assertEqual(transaction_event_errors(snapshot,event),[])
        event['props']['amount_krw']=10
        self.assertIn('amount_krw',transaction_event_errors(snapshot,event))

    def test_random_visit_counts_preserve_existing_work_and_total(self):
        floors={u['id']:10 for u in USERS[:20]}
        counts=allocate_visit_counts(USERS,floors,1000,99)
        self.assertEqual(sum(counts.values()),1000)
        self.assertGreater(len(set(counts.values())),8)
        self.assertTrue(all(2<=n<=24 for n in counts.values()))
        self.assertTrue(all(counts[pid]>=floor for pid,floor in floors.items()))
        self.assertEqual(counts,allocate_visit_counts(USERS,floors,1000,99))
        means={kind:sum(counts[u['id']] for u in USERS if u['viewing_style']['attendance_frequency']==kind)
                    /sum(u['viewing_style']['attendance_frequency']==kind for u in USERS)
               for kind in ('occasional','frequent')}
        self.assertGreater(means['frequent'],means['occasional'])

    def test_random_schedule_preserves_completed_prefix_and_valid_dates(self):
        old=build_period_plan(USERS,date(2026,10,8),30,10,99)
        existing={old[0]['persona_id']:{'sessions':{'0':{'plan':copy.deepcopy(old[0]['sessions'][0])}}}}
        revised=randomize_period_plan(USERS,existing,date(2026,10,8),30,1000,99)
        self.assertEqual(revised[0]['sessions'][0],old[0]['sessions'][0])
        self.assertEqual(sum(len(p['sessions']) for p in revised),1000)
        ids=[s['visit_id'] for p in revised for s in p['sessions']]
        self.assertEqual(len(ids),len(set(ids)))
        for p in revised:
            clocks=[datetime.fromisoformat(s['simulation_start']) for s in p['sessions']]
            self.assertEqual(clocks,sorted(clocks))
            self.assertTrue(all('2026-10-08'<=s['simulation_date']<='2026-11-06' for s in p['sessions']))


if __name__=='__main__':
    unittest.main()
