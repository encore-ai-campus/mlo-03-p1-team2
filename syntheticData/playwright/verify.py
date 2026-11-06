"""Read-only MariaDB/MongoDB evidence for a real browser campaign.

Run with the repository root Python environment (backend dependencies).
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

from scenarios import file_sha256
from safety import compare_payload, visit_errors


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'backend'))


def verify(args):
    from pymongo import MongoClient
    from sqlalchemy import create_engine, select, text
    from sqlalchemy.orm import Session
    from app.core.config import Settings
    from app.models import User, Favorite, Reservation, Event

    settings = Settings(_env_file=ROOT / 'backend' / '.env')
    mongo = MongoClient(settings.mongodb_url, serverSelectionTimeoutMS=5000, tz_aware=True)
    db = mongo[settings.mongodb_db]
    collection = db['simulation']
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    host = urlsplit(settings.mongodb_url)
    with engine.connect() as connection:
        version = connection.execute(text('SELECT VERSION()')).scalar_one()
    print(json.dumps({'sql_version': version, 'mongo_host': host.hostname,
                      'mongo_port': host.port, 'mongo_db': settings.mongodb_db,
                      'mongo_collection': 'simulation'}, ensure_ascii=False))
    mongo.admin.command('ping')
    if args.preflight:
        print('Read-only connection preflight passed')
        return
    directory = HERE / 'artifacts' / args.run_id
    state = json.loads((directory / 'state.json').read_text(encoding='utf-8'))
    if state['fingerprint']['collection'] != 'simulation':
        raise ValueError('Wrong campaign collection')
    if state['fingerprint']['profiles_sha256'] != file_sha256(HERE.parent / 'personas.json'):
        raise ValueError('Profile input changed')
    profiles = json.loads((HERE.parent / 'personas.json').read_text(encoding='utf-8'))['users'][:args.count]
    accounts = [state['accounts'][p['id']] for p in profiles]
    if len(accounts) != args.count or any(not a['user_id'] for a in accounts):
        raise ValueError('Missing account mappings')
    errors = []
    def check(condition, message):
        if not condition:
            errors.append(message)
    expected_records = []
    for line in (directory / 'events.jsonl').read_text(encoding='utf-8').splitlines():
        expected_records.append(json.loads(line))
    event_ids = {r['event']['event_id'] for r in expected_records}
    actual_events = {r['event_id']: r for r in collection.find({'event_id': {'$in': list(event_ids)}})}
    check(len(actual_events) == len(event_ids), 'Missing acknowledged events in simulation')
    user_ids = [a['user_id'] for a in accounts]
    with Session(engine) as session:
        users = {u.id: u for u in session.scalars(select(User).where(User.id.in_(user_ids)))}
        favorites = list(session.scalars(select(Favorite).where(Favorite.user_id.in_(user_ids))))
        reservations = list(session.scalars(select(Reservation).where(Reservation.user_id.in_(user_ids))))
        sql_events = list(session.scalars(select(Event).where(Event.user_id.in_(user_ids))))
        visit_session_ids = set()
        for account, profile in zip(accounts, profiles):
            uid = account['user_id']
            user = users.get(uid)
            check(user is not None and user.email == account['email'] and user.name == profile['name']
                  and user.mbti == profile['mbti'] and user.consent,
                  f'Persona/account mismatch: {profile["id"]}')
            visits = list(account['sessions'].values())
            check(len(visits) == {'occasional': 1, 'monthly': 2, 'frequent': 3}[profile['viewing_style']['attendance_frequency']],
                  f'Incomplete visits: {profile["id"]}')
            check(all(v['status'] == 'complete' for v in visits), f'Failed visit: {profile["id"]}')
            expected_favorites = {pid for v in visits for pid in v['favorite_ids']}
            check({f.performance_id for f in favorites if f.user_id == uid} == expected_favorites,
                  f'Favorite mismatch: {profile["id"]}')
            expected_reservations = {r['id']: r for v in visits for r in v['reservations']}
            actual_reservations = {r.id: r for r in reservations if r.user_id == uid}
            check(set(actual_reservations) == set(expected_reservations), f'Reservation mismatch: {profile["id"]}')
            for rid, expected in expected_reservations.items():
                actual = actual_reservations.get(rid)
                check(actual is not None and actual.payment is not None
                      and actual.payment.status == expected['payment_status']
                      and actual.status == ('CONFIRMED' if expected['payment_status'] == 'COMPLETED' else 'REQUESTED')
                      and actual.performance_id == expected['performance_id'] and actual.quantity == expected['quantity']
                      and actual.payment.amount == actual.amount,
                      f'Payment mismatch: {rid}')
            for visit in visits:
                observed = [actual_events[eid] for eid in visit['event_ids'] if eid in actual_events]
                evidence_errors = visit_errors(visit, observed)
                check(not evidence_errors, f'Visit evidence mismatch for {profile["id"]}: {evidence_errors}')
                session_ids = {e['session_id'] for e in observed}
                check(not (session_ids & visit_session_ids), f'Reused visit session_id: {profile["id"]}')
                visit_session_ids.update(session_ids)
                types = {e['type'] for e in observed}
                required = {'login', 'logout', 'performance_view', 'category_select'}
                outcome = visit['plan']['outcome']
                if outcome != 'view_only':
                    # A revisited already-favorited show need not emit another favorite_add.
                    check(bool(visit['favorite_ids']), 'Missing favorite selection')
                if outcome in ('booking_abandon', 'payment_abandon', 'purchase'):
                    required.add('booking_start')
                if outcome in ('payment_abandon', 'purchase'):
                    required.add('reservation_request')
                if outcome == 'purchase':
                    required.add('payment_complete')
                check(required <= types, f'Missing events for {profile["id"]}: {sorted(required - types)}')
                if outcome in ('view_only', 'favorite_only', 'booking_abandon'):
                    check(not visit['reservations'] and 'payment_complete' not in types,
                          f'Unexpected conversion in {outcome}')
        for record in expected_records:
            eid = record['event']['event_id']
            actual = actual_events.get(eid)
            if actual is None:
                continue
            persona_id = record['persona_id']
            account = state['accounts'][persona_id]
            payload_errors = compare_payload(record['event'], actual)
            check(not payload_errors, f'Mongo payload mismatch {eid}: {payload_errors}')
            check(actual['props'].get('synthetic') is True
                  and actual['props'].get('synthetic_run_id') == args.run_id
                  and actual['props'].get('synthetic_persona_id') == persona_id
                  and actual['anonymous_id'] == account['anonymous_id']
                  and actual.get('user_id') == (account['user_id'] if record['authenticated'] else None),
                  f'Mongo tag/user mismatch: {eid}')
        leaked = db['events'].count_documents({'props.synthetic_run_id': args.run_id})
        check(leaked == 0, 'Campaign logs leaked into the original events collection')
        check(collection.count_documents({'props.synthetic_run_id': args.run_id}) == len(actual_events),
              'Some campaign events have no acknowledged outbound evidence')
        baseline_path = HERE / 'artifacts' / 'baseline.json'
        if baseline_path.exists():
            for relative, digest in json.loads(baseline_path.read_text(encoding='utf-8')).items():
                check(file_sha256(ROOT / relative) == digest, f'Existing file changed: {relative}')
        report = {
            'run_id': args.run_id, 'fingerprint': state['fingerprint'], 'passed': not errors,
            'checked_at': datetime.now(timezone.utc).isoformat(), 'sql_version': version,
            'users': len(users), 'sessions': sum(len(a['sessions']) for a in accounts),
            'favorites': len(favorites), 'reservations': len(reservations),
            'payment_statuses': dict(Counter(r.payment.status for r in reservations)),
            'sql_event_types': dict(Counter(e.type for e in sql_events)),
            'mongo_db': settings.mongodb_db, 'mongo_collection': 'simulation',
            'mongo_events': len(actual_events),
            'mongo_event_types': dict(Counter(e['type'] for e in actual_events.values())),
            'original_events_leaked': leaked, 'errors': errors,
        }
    (directory / f'verification-{args.count}.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    mongo.close()
    engine.dispose()
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id')
    parser.add_argument('--count', type=int, default=3)
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args()
    if not args.preflight and (not args.run_id or not __import__('re').fullmatch(r'[A-Za-z0-9_-]{1,64}', args.run_id)):
        parser.error('a valid run-id is required')
    verify(args)
