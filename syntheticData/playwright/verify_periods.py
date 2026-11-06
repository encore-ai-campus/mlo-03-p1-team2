"""Read-only existing-account/transaction/log checks and fictional-period CSVs."""
import argparse
from collections import Counter
import csv
from datetime import date, datetime, timezone
import json
import hashlib
from pathlib import Path
import re
import subprocess
import sys

from periods import aggregate_periods, KST, transaction_snapshot, transaction_event_errors
from run import HERE
from safety import save_json, compare_payload, visit_errors
from scenarios import file_sha256, profiles_for_run

ROOT = HERE.parents[1]
sys.path.insert(0,str(ROOT/'backend'))


def verify_periods(args):
    from app.core.config import Settings
    from app.models import User, Favorite, Reservation, Event
    from sqlalchemy import create_engine, select, func
    from sqlalchemy.orm import Session
    from pymongo import MongoClient
    directory = HERE/'artifacts'/args.run_id
    state = json.loads((directory/'state.json').read_text(encoding='utf-8'))
    settings = Settings(_env_file=ROOT/'backend/.env')
    engine = create_engine(settings.database_url,pool_pre_ping=True)
    mongo = MongoClient(settings.mongodb_url,serverSelectionTimeoutMS=5000,tz_aware=True)
    collection = mongo[settings.mongodb_db]['simulation']
    ids = [a['user_id'] for a in state['accounts'].values()]
    with Session(engine) as db:
        users = {u.id:u for u in db.scalars(select(User).where(User.id.in_(ids)))}
        favorites = {(f.user_id,f.performance_id) for f in db.scalars(select(Favorite).where(Favorite.user_id.in_(ids)))}
        reservations = {r.id:r for r in db.scalars(select(Reservation).where(Reservation.user_id.in_(ids)))}
        sql_counts = dict(db.execute(select(Event.type,func.count()).where(Event.user_id.in_(ids)).group_by(Event.type)).all())
        synthetic_users = sorted(db.scalars(select(User.id).where(User.email.like('%+synthetic@example.com'))))
        if args.baseline:
            target = directory/'period-baseline.json'
            if target.exists() or collection.count_documents({'props.synthetic_run_id':args.run_id}):
                raise ValueError('Refusing to overwrite a baseline or snapshot after events were written')
            if len(users)!=100:
                raise ValueError('The existing 100 accounts are missing')
            for account in state['accounts'].values():
                user=users[account['user_id']]
                if (user.name,user.email,user.mbti)!=(account['name'],account['email'],account['mbti']):
                    raise ValueError('Existing account mapping does not match persona')
            tracked = subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
            protected = [p for p in tracked if p and (ROOT/p).is_file()]
            additions = {'PERIODS.md','test_periods.py','periods.py','run_periods.py','verify_periods.py','load_scenarios.json'}
            protected += [str(p.relative_to(ROOT)).replace('\\','/') for p in HERE.iterdir()
                          if p.is_file() and p.name not in additions]
            if (ROOT/'docs/erd.html').exists():
                protected.append('docs/erd.html')
            baseline={'fingerprint':state['fingerprint'],'synthetic_user_ids':synthetic_users,
                      'snapshot_git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),
                      'transaction_snapshots':{rid:transaction_snapshot(r) for rid,r in reservations.items()},
                      'favorites':[list(pair) for pair in sorted(favorites)],'sql_event_counts':sql_counts,
                      'reservations':{rid:{'user_id':r.user_id,'payment_status':r.payment.status,'amount':r.amount}
                                      for rid,r in reservations.items()},
                      'protected_files':{p:file_sha256(ROOT/p) for p in protected}}
            save_json(target,baseline)
            print(json.dumps({'baseline_saved':True,'existing_users':len(users),'existing_reservations':len(reservations),
                              'existing_favorites':len(favorites),'protected_files':len(baseline['protected_files'])}))
            return
        baseline = json.loads((directory/'period-baseline.json').read_text(encoding='utf-8'))
        if args.audit_interrupted:
            records=[json.loads(line) for line in (directory/'events.jsonl').read_text(encoding='utf-8').splitlines()]
            journal={r['event']['event_id']:r for r in records}
            persisted={e['event_id']:e for e in collection.find({'props.synthetic_run_id':args.run_id})}
            if set(journal)!=set(persisted):raise ValueError('Reconcile unacknowledged log IDs before recovery')
            known=set(baseline['reservations'])|{r['id'] for a in state['accounts'].values() for v in a['sessions'].values() for r in v['reservations']}
            if set(reservations)!=known:raise ValueError('Unrecorded reservation side effects; recovery refused')
            jobs=[]
            for account in state['accounts'].values():
                for key,visit in account['sessions'].items():
                    if visit['status']=='complete':continue
                    if visit['reservations']:raise ValueError('Automatic recovery will not replay an existing reservation')
                    events=[r['event'] for r in records if r['persona_id']==account['persona_id']
                            and r['event']['props']['synthetic_visit_id']==visit['plan']['visit_id']]
                    sids={e['session_id'] for e in events}
                    if len(sids)>1:raise ValueError('Interrupted visit has ambiguous session identity')
                    views=[{'performance_id':e['props']['performance_id'],'category':e['props']['category']}
                           for e in events if e['type']=='performance_view']
                    jobs.append({'persona_id':account['persona_id'],'visit':key,'events':events,
                                 'session_id':next(iter(sids),None),'views':views,
                                 'retained_favorites':[pid for uid,pid in favorites if uid==account['user_id']]})
            save_json(directory/'stopped-audit.json',{'state_sha256':file_sha256(directory/'state.json'),
                      'jobs':jobs,'unrecorded_reservations':0})
            print(json.dumps({'interrupted_visits':len(jobs),'unrecorded_reservations':0,'acknowledged_events':len(journal)}))
            return
        if args.strengthen_baseline:
            if baseline.get('transaction_snapshots'):
                raise ValueError('Full transaction snapshots already exist')
            for rid,before in baseline['reservations'].items():
                r=reservations[rid]
                if (r.user_id,r.amount,r.payment.status)!=(before['user_id'],before['amount'],before['payment_status']):
                    raise ValueError('Cannot strengthen a baseline whose known values changed')
            baseline['transaction_snapshots']={rid:transaction_snapshot(reservations[rid]) for rid in baseline['reservations']}
            baseline['strengthened_at']=datetime.now(timezone.utc).isoformat()
            save_json(directory/'period-baseline.json',baseline)
            print('Extended preexisting transaction evidence; no database writes:',len(baseline['transaction_snapshots']))
            return
        errors=[]
        def check(value,message):
            if not value: errors.append(message)
        check(baseline['fingerprint']==state['fingerprint'],'Campaign settings changed')
        check(file_sha256(profiles_for_run(directory,HERE.parent/'personas.json'))==state['fingerprint']['profiles_sha256'],'Profiles changed')
        source=HERE/'artifacts'/state['fingerprint']['source_run']/'state.json'
        check(file_sha256(source)==state['fingerprint']['source_sha256'],'Original account state changed')
        check(synthetic_users==baseline['synthetic_user_ids'],'Synthetic account set changed; no signup was expected')
        records = [json.loads(line) for line in (directory/'events.jsonl').read_text(encoding='utf-8').splitlines()]
        expected_events = {r['event']['event_id']:r for r in records}
        actual_events = {e['event_id']:e for e in collection.find({'props.synthetic_run_id':args.run_id})}
        check(set(expected_events)==set(actual_events),'Mongo event IDs differ from acknowledged requests')
        seen_sessions=set()
        expected_reservations={}
        expected_favorites={tuple(v) for v in baseline['favorites']}
        plans = json.loads((directory/'plan.json').read_text(encoding='utf-8'))
        accounts = [state['accounts'][p['persona_id']] for p in (plans[:3] if args.pilot else plans)]
        for account in accounts:
            user=users.get(account['user_id'])
            check(user is not None and (user.name,user.email,user.mbti)==(account['name'],account['email'],account['mbti']),
                  'User identity mismatch: '+account['persona_id'])
            visits=list(account['sessions'].values())
            expected_visits=next(len(p['sessions']) for p in plans if p['persona_id']==account['persona_id'])
            check(len(visits)==(1 if args.pilot else expected_visits),
                  'Incorrect visit count: '+account['persona_id'])
            for visit in visits:
                check(visit['status']=='complete','Incomplete visit: '+account['persona_id'])
                events=[actual_events[eid] for eid in visit['event_ids'] if eid in actual_events]
                check(not visit_errors(visit,events),'UI/event mismatch: '+account['persona_id']+' / '+str(visit_errors(visit,events)))
                sids={e['session_id'] for e in events}
                check(not sids&seen_sessions,'Session ID reused across visits')
                seen_sessions.update(sids)
                for event in events:
                    props=event['props']
                    virtual=datetime.fromisoformat(props['simulation_at'].replace('Z','+00:00')).astimezone(KST)
                    check(props.get('simulation_time_is_fictional') is True
                          and props['simulation_date']==visit['plan']['simulation_date']==virtual.date().isoformat()
                          and props['synthetic_visit_id']==visit['plan']['visit_id']
                          and props['simulation_at_kst']==virtual.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                          'Invalid analytical timestamp: '+event['event_id'])
                for r in visit['reservations']:
                    expected_reservations[r['id']]=(account['user_id'],r)
                expected_favorites.update((account['user_id'],pid) for pid in visit['favorite_ids'])
        check(favorites==expected_favorites,'Final favorites differ from baseline plus UI selections')
        check(set(reservations)==set(baseline['reservations'])|set(expected_reservations),'Unexpected or missing reservation')
        for rid,before in baseline['reservations'].items():
            actual=reservations.get(rid)
            check(actual is not None and actual.payment.status==before['payment_status'] and actual.amount==before['amount'],
                  'A preexisting reservation was changed: '+rid)
            check(actual is not None and transaction_snapshot(actual)==baseline['transaction_snapshots'][rid],
                  'A preexisting reservation/payment field changed: '+rid)
        for rid,(uid,expected) in expected_reservations.items():
            actual=reservations.get(rid)
            check(actual is not None and actual.user_id==uid and actual.performance_id==expected['performance_id']
                  and actual.quantity==expected['quantity'] and actual.payment.status==expected['payment_status']
                  and actual.amount==actual.payment.amount,
                  'New reservation/payment mismatch: '+rid)
        for eid,record in expected_events.items():
            actual=actual_events.get(eid)
            if actual is None:continue
            account=state['accounts'][record['persona_id']]
            check(not compare_payload(record['event'],actual),'Persisted payload mismatch: '+eid)
            check(actual['props']['synthetic_persona_id']==record['persona_id']
                  and actual['anonymous_id']==account['anonymous_id']
                  and actual['user_id']==(account['user_id'] if record['authenticated'] else None),
                  'Persisted user mapping mismatch: '+eid)
            if actual['type'] in ('reservation_request','payment_complete'):
                reservation=reservations.get(actual['props'].get('reservation_id'))
                check(reservation is not None and not transaction_event_errors(transaction_snapshot(reservation),actual),
                      'Tracking/SQL transaction amount or reference mismatch: '+eid)
        check(mongo[settings.mongodb_db]['events'].count_documents({'props.synthetic_run_id':args.run_id})==0,
              'Period campaign leaked into original events')
        externally_committed=[]
        for path,digest in baseline['protected_files'].items():
            current=file_sha256(ROOT/path)
            if current!=digest and Path(path).suffix in ('.md','.html'):
                committed=subprocess.run(['git','show','HEAD:'+path],cwd=ROOT,capture_output=True)
                if committed.returncode==0 and committed.stdout.replace(b'\r\n',b'\n')==(ROOT/path).read_bytes().replace(b'\r\n',b'\n'):
                    externally_committed.append(path)
                    continue
            check(current==digest,'Preexisting file changed: '+path)
        metrics=aggregate_periods(actual_events.values(),date.fromisoformat(state['fingerprint']['period_start']),state['fingerprint']['days'])
        sql_revenue=sum(reservations[rid].payment.amount for rid,(_,r) in expected_reservations.items()
                        if r['payment_status']=='COMPLETED')
        check(sum(row['revenue_krw'] for row in metrics['daily'])==sql_revenue,'Analytical revenue differs from SQL completed payments')
        if not args.pilot:
            for name,rows in metrics.items():
                with (directory/(name+'.csv')).open('w',encoding='utf-8-sig',newline='') as stream:
                    writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
                    writer.writeheader();writer.writerows(rows)
            save_json(directory/'analytics.json',metrics)
            save_json(directory/'daily-query.json',[
                {'$match':{'props.synthetic_run_id':args.run_id}},
                {'$group':{'_id':{'date':'$props.simulation_date','type':'$type'},'count':{'$sum':1}}},
                {'$sort':{'_id.date':1,'_id.type':1}}])
        visits=[s for a in accounts for s in a['sessions'].values()]
        report={'run_id':args.run_id,'passed':not errors,'fingerprint':state['fingerprint'],
                'checked_at':datetime.now(timezone.utc).isoformat(),'existing_users':len(users),'new_accounts':0,
                'visits':len(visits),'mongo_events':len(actual_events),'views':sum(len(v['views']) for v in visits),
                'new_favorites':len(favorites)-len(baseline['favorites']),
                'new_reservations':len(expected_reservations),
                'payment_statuses':dict(Counter(r['payment_status'] for _,r in expected_reservations.values())),
                'mongo_event_types':dict(Counter(e['type'] for e in actual_events.values())),
                'virtual_days_with_events':sum(row['events']>0 for row in metrics['daily']),
                'virtual_revenue_krw':sum(row['revenue_krw'] for row in metrics['daily']),
                'sql_event_deltas':{kind:count-baseline['sql_event_counts'].get(kind,0) for kind,count in sql_counts.items()},
                'original_collection_leakage':0,'protected_files':len(baseline['protected_files']),'errors':errors}
        report['externally_committed_documents']=externally_committed
        save_json(directory/('verification-periods-pilot.json' if args.pilot else 'verification-periods.json'),report)
        print(json.dumps(report,ensure_ascii=False,indent=2))
        if errors:raise SystemExit(1)
    engine.dispose();mongo.close()


if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--baseline',action='store_true')
    parser.add_argument('--pilot',action='store_true')
    parser.add_argument('--strengthen-baseline',action='store_true')
    parser.add_argument('--audit-interrupted',action='store_true')
    args=parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',args.run_id):parser.error('Invalid run ID')
    verify_periods(args)
