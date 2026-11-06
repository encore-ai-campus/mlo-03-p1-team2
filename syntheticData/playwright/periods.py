"""Fictional analytical time, kept separate from real browser timestamps."""
from collections import defaultdict
import copy
from datetime import date, datetime, time, timedelta, timezone
import random
import math
import uuid

from scenarios import OUTCOMES, OUTCOME_WEIGHTS, REVISIT_PROBABILITY, synthetic_email

KST = timezone(timedelta(hours=9))
NAMESPACE = uuid.UUID('8903975a-cbf2-4683-926e-ddc367211ff0')


def allocate_visit_counts(users, minimums, total=1000, seed=99):
    rng=random.Random(f'visit-counts:{seed}')
    means={'occasional':5,'monthly':10,'frequent':16}
    floors={u['id']:max(2,minimums.get(u['id'],0)) for u in users}
    if sum(floors.values())>total or total>24*len(users) or any(n>24 for n in floors.values()):
        raise ValueError('Requested total cannot preserve completed visits within 2..24 bounds')
    counts={u['id']:max(floors[u['id']],min(24,round(rng.lognormvariate(
        math.log(means[u['viewing_style']['attendance_frequency']]),0.45)))) for u in users}
    while sum(counts.values())!=total:
        add=sum(counts.values())<total
        candidates=[u for u in users if (counts[u['id']]<24 if add else counts[u['id']]>floors[u['id']])]
        weights=[means[u['viewing_style']['attendance_frequency']] if add else
                 1/means[u['viewing_style']['attendance_frequency']] for u in candidates]
        chosen=rng.choices(candidates,weights)[0]['id']
        counts[chosen]+=1 if add else -1
    return counts


def randomize_period_plan(users, existing_accounts, start, days=30, total=1000, seed=99):
    minimums={pid:len(a['sessions']) for pid,a in existing_accounts.items()}
    counts=allocate_visit_counts(users,minimums,total,seed)
    result=[]
    for user in users:
        count=counts[user['id']]
        plan=build_period_plan([user],start,days,count,seed)[0]
        saved=existing_accounts.get(user['id'],{}).get('sessions',{})
        prefix=[copy.deepcopy(saved[str(i)]['plan']) for i in range(len(saved))]
        rng=random.Random(f'random-visits:{seed}:{user["id"]}')
        for visit in plan['sessions'][len(prefix):]:
            visit['outcome']=rng.choices(OUTCOMES,OUTCOME_WEIGHTS[user['viewing_style']['attendance_frequency']])[0]
        if prefix:
            after=datetime.fromisoformat(prefix[-1]['simulation_start'])
            end=datetime.combine(start+timedelta(days=days-1),time(23,50),tzinfo=KST)
            remaining=count-len(prefix)
            minutes=int((end-after).total_seconds()//60)
            if remaining>minutes:raise ValueError('Not enough remaining fictional time for preserved visit prefix')
            slots=sorted(rng.sample(range(1,minutes+1),remaining))
            for visit,offset in zip(plan['sessions'][len(prefix):],slots):
                clock=after+timedelta(minutes=offset)
                visit['simulation_start']=clock.isoformat()
                visit['simulation_date']=clock.date().isoformat()
            plan['sessions'][:len(prefix)]=prefix
        result.append(plan)
    return result


def transaction_snapshot(reservation):
    def columns(row):
        result={}
        for column in row.__table__.columns:
            value=getattr(row,column.name)
            result[column.name]=value.isoformat() if isinstance(value,(date,datetime)) else value
        return result
    return {'reservation':columns(reservation),'payment':columns(reservation.payment)}


def transaction_event_errors(snapshot,event):
    reservation,payment=snapshot['reservation'],snapshot['payment']
    expected={'reservation_id':reservation['id'],'performance_id':reservation['performance_id'],
              'category':reservation['category'],'quantity':reservation['quantity'],
              'seat_grade':reservation['seat_grade'],'amount_krw':reservation['amount']}
    errors=[key for key,value in expected.items() if event['props'].get(key)!=value]
    if event.get('user_id')!=reservation['user_id']:errors.append('user_id')
    if payment['amount']!=reservation['amount']:errors.append('payment_amount')
    if event['type']=='payment_complete' and payment['status']!='COMPLETED':errors.append('payment_status')
    return errors


def build_period_plan(users, start, days=30, visits=10, seed=99):
    if days < 1 or visits < 1 or visits > days:
        raise ValueError('Require 1 <= visits <= days')
    plans = []
    for index, user in enumerate(users):
        rng = random.Random(f'periods:{seed}:{user["id"]}')
        style = user['viewing_style']
        offsets = sorted(rng.sample(range(days), visits))
        quantities = {'solo': (1,), 'partner': (2,), 'friends': (2,3,4), 'family': (2,3,4)}
        sessions = []
        for number, offset in enumerate(offsets):
            day = start + timedelta(days=offset)
            clock = datetime.combine(day, time(rng.randint(9,22), rng.randint(0,40)), tzinfo=KST)
            weights = user['category_weights']
            outcome = rng.choices(OUTCOMES, OUTCOME_WEIGHTS[style['attendance_frequency']])[0]
            if number == 0 and index < 3:
                outcome = ('view_only','booking_abandon','purchase')[index]
            sessions.append({'index':number, 'outcome':outcome,
                             'category':rng.choices(list(weights),list(weights.values()))[0],
                             'views':rng.randint(1,3), 'quantity':rng.choice(quantities[style['companion']]),
                             'selection_seed':rng.randrange(2**32),
                             'revisit_probability':REVISIT_PROBABILITY[style['discovery_style']],
                             'simulation_date':day.isoformat(), 'simulation_start':clock.isoformat(),
                             'visit_id':str(uuid.uuid5(NAMESPACE, f'{seed}:{user["id"]}:{start}:{days}:{number}'))})
        plans.append({'persona_id':user['id'],'name':user['name'],'mbti':user['mbti'],
                      'source_email':user['email'],'email':synthetic_email(user['email']),'sessions':sessions})
    return plans


def period_tags(events, visit, real_anchor):
    result = copy.deepcopy(events)
    scheduled = datetime.fromisoformat(visit['simulation_start'])
    for event in result:
        actual = datetime.fromisoformat(event['occurred_at'].replace('Z','+00:00'))
        simulated = scheduled + max(actual-real_anchor, timedelta(0))
        event.setdefault('props',{}).update({
            'simulation_at':simulated.astimezone(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z'),
            'simulation_at_kst':simulated.astimezone(KST).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
            'simulation_date':simulated.astimezone(KST).date().isoformat(),
            'simulation_time_is_fictional':True,
            'synthetic_visit_id':visit['visit_id'],
        })
        if len(event['props']) > 20:
            raise ValueError('Temporal and synthetic tags exceed 20 tracking props')
    return result


def aggregate_periods(events, start, days):
    unique = {e['event_id']:e for e in events}
    rows = []
    for offset in range(days):
        day = (start+timedelta(days=offset)).isoformat()
        rows.append((day,[e for e in unique.values() if e['props'].get('simulation_date')==day]))
    def metrics(label, group):
        def reservation_ids(kind):
            return {e['props'].get('reservation_id',e['event_id']) for e in group if e['type']==kind}
        payments = {e['props'].get('reservation_id',e['event_id']):e for e in group if e['type']=='payment_complete'}
        return {'date':label,'events':len(group),
                'visits':len({e['props']['synthetic_visit_id'] for e in group}),
                'users':len({e['user_id'] for e in group if e.get('user_id')}),
                'views':sum(e['type']=='performance_view' for e in group),
                'favorites':sum(e['type']=='favorite_add' for e in group),
                'booking_starts':sum(e['type']=='booking_start' for e in group),
                'reservations':len(reservation_ids('reservation_request')),
                'payments':len(payments),
                'revenue_krw':sum(e['props'].get('amount_krw',0) for e in payments.values())}
    daily = [metrics(day,group) for day,group in rows]
    weekly,monthly = defaultdict(list),defaultdict(list)
    seen_users = set()
    for row,(day,group) in zip(daily,rows):
        users = {e['user_id'] for e in group if e.get('user_id')}
        row['returning_users'] = len(users & seen_users)
        row['new_in_period_users'] = len(users - seen_users)
        seen_users.update(users)
        d = date.fromisoformat(day)
        weekly[(d-timedelta(days=d.weekday())).isoformat()].extend(group)
        monthly[day[:7]].extend(group)
    return {'daily':daily,'weekly':[metrics(label,group) for label,group in sorted(weekly.items())],
            'monthly':[metrics(label,group) for label,group in sorted(monthly.items())]}
