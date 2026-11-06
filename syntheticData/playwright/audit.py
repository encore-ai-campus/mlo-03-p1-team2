"""Read-only reconciliation before recovery; never alters a DB or campaign state."""
import json
from pathlib import Path
import sys

from safety import visit_errors, save_json
from scenarios import file_sha256

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'backend'))


def audit(run_id):
    from app.core.config import Settings
    from app.models import Reservation
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    directory = HERE / 'artifacts' / run_id
    path = directory / 'state.json'
    state = json.loads(path.read_text(encoding='utf-8'))
    records = [json.loads(line) for line in (directory / 'events.jsonl').read_text(encoding='utf-8').splitlines()]
    events = {r['event']['event_id']: r['event'] for r in records}
    settings = Settings(_env_file=ROOT / 'backend' / '.env')
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    jobs, blocked = [], []
    with Session(engine) as db:
        for account in state['accounts'].values():
            if not account['user_id']:
                continue
            actual = {r.id: r for r in db.scalars(select(Reservation).where(Reservation.user_id == account['user_id']))}
            expected = {r['id']: r for v in account['sessions'].values() for r in v['reservations']}
            if set(actual) != set(expected) or any(actual[rid].payment.status != r['payment_status'] for rid, r in expected.items()):
                blocked.append({'email': account['email'], 'reason': 'Unreconciled reservation side effects'})
                continue
            for key, visit in account['sessions'].items():
                observed = [events[eid] for eid in visit['event_ids'] if eid in events]
                problems = visit_errors(visit, observed)
                if not problems and visit['status'] == 'complete':
                    continue
                if not problems:
                    action = 'mark_complete'
                elif problems == ['missing types: logout']:
                    action = 'finish_auth'
                elif not visit['views'] and not visit['reservations'] and visit['status'] in ('in_progress', 'failed'):
                    action = 'reset_unstarted'
                elif not visit['reservations'] and visit['plan']['outcome'] in ('view_only', 'favorite_only', 'booking_abandon'):
                    action = 'replay_browse'
                else:
                    blocked.append({'email': account['email'], 'visit': key, 'reason': problems})
                    continue
                jobs.append({'persona_id': account['persona_id'], 'email': account['email'], 'visit': key,
                             'action': action, 'problems': problems})
    engine.dispose()
    report = {'run_id': run_id, 'state_sha256': file_sha256(path), 'jobs': jobs, 'blocked': blocked}
    save_json(directory / 'recovery-audit.json', report)
    print(json.dumps({'jobs': len(jobs), 'actions': {kind: sum(j['action'] == kind for j in jobs)
                                                  for kind in {j['action'] for j in jobs}}, 'blocked': blocked}))
    if blocked:
        raise SystemExit(1)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not __import__('re').fullmatch(r'[A-Za-z0-9_-]{1,64}', args.run_id):
        parser.error('Invalid run-id')
    audit(args.run_id)
