"""Read-only DB verification of a finished load-test run.

    syntheticData/loadtest/.venv/Scripts/python.exe syntheticData/loadtest/verify_load.py --run-id <id>

Checks (all against MariaDB / MongoDB, never the HTTP responses alone):
- new record counts per table / collection, total vs the 50,000 target and both caps
- every reservation has one payment and a consistent (reservation, payment) state pair
- status_history per reservation matches the final state; business events match the history
- every reservation the runner saw as created exists; no reservation exists that the runner never sent
- duplicate request_key test: exactly one reservation per key
- complete/cancel race: allowed transitions only, final reservation/payment states agree
- tracking: every event id of an accepted batch is stored once; resent ids are not duplicated
Writes verification.json into the run directory.
"""
import argparse
from collections import Counter, defaultdict
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import infra  # noqa: E402
from sqlalchemy import bindparam, text  # noqa: E402

PAIRS = {('REQUESTED', 'PENDING'), ('CONFIRMED', 'COMPLETED'), ('CANCELLED', 'CANCELLED')}
ALLOWED = {'reservation': {(None, 'REQUESTED'), ('REQUESTED', 'CONFIRMED'), ('REQUESTED', 'CANCELLED'),
                           ('CONFIRMED', 'CANCELLED')},
           'payment': {(None, 'PENDING'), ('PENDING', 'COMPLETED'), ('PENDING', 'CANCELLED'),
                       ('COMPLETED', 'CANCELLED')}}


def jsonl(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run-id', required=True)
    args = ap.parse_args()
    d = infra.ARTIFACTS / args.run_id
    state = json.loads((d / 'state.json').read_text(encoding='utf-8'))
    env = infra.load_env()
    counter = infra.Counter(env, state.get('mongo_collection') or 'events')
    counter.maria_baseline = state.get('maria_baseline') or {}
    reused = bool(state.get('reused_from'))
    baseline_res = set(json.loads((d / 'baseline_reservations.json').read_text(encoding='utf-8'))) \
        if reused else set()
    ids = [a['user_id'] for a in state['accounts'].values() if a.get('user_id')]
    errors, notes = [], []

    def check(cond, msg):
        if not cond:
            errors.append(msg)

    totals = counter.totals(args.run_id, ids)
    with counter.engine.connect() as c:
        def q(sql, **kw):
            st = text(sql)
            for k, v in kw.items():
                if isinstance(v, (list, tuple)):
                    st = st.bindparams(bindparam(k, expanding=True))
            return c.execute(st, kw).all()

        res = q('select r.id, r.user_id, r.status, r.request_key, r.amount, p.status, p.amount, p.id '
                'from reservations r left join payments p on p.reservation_id = r.id where r.user_id in :ids', ids=ids)
        hist = q('select reservation_id, entity, from_status, to_status, created_at, id from status_history '
                 'where user_id in :ids order by created_at, id', ids=ids)
        evs = q('select type, reservation_id from events where user_id in :ids', ids=ids)
        other_users = q('select count(*) from users where id in :ids and created_at < :t', ids=ids,
                        t=state['created_kst'][:10] + ' 00:00:00')[0][0]
    if not reused:   # reused accounts were created by an earlier run on purpose
        check(other_users == 0, f'{other_users} run users were created before the run date')

    all_res = {r[0] for r in res}
    # reused accounts: verify only reservations created by this run (earlier ones were verified by their run)
    res = [r for r in res if r[0] not in baseline_res]
    hist = [h for h in hist if h[0] not in baseline_res]
    evs = [e for e in evs if e[1] not in baseline_res]
    by_res = {r[0]: r for r in res}
    h_by = defaultdict(list)
    for h in hist:
        h_by[h[0]].append(h)
    ev_by = defaultdict(Counter)
    for t, rid in evs:
        if rid:
            ev_by[rid][t] += 1
    bad_pair = bad_hist = bad_event = missing_pay = bad_amount = 0
    for rid, r in by_res.items():
        if r[7] is None:
            missing_pay += 1
            continue
        if (r[2], r[5]) not in PAIRS:
            bad_pair += 1
        if r[4] != r[6]:
            bad_amount += 1
        hs = h_by.get(rid, [])
        chain = {'reservation': [], 'payment': []}
        for h in hs:
            chain[h[1]].append((h[2], h[3]))
        # created_at has 1 s precision, so rows of the same second have no reliable order:
        # rebuild each chain by following from_status -> to_status starting at None.
        for ent, steps in chain.items():
            rest, ordered, cur = list(steps), [], None
            while True:
                nxt = next((s for s in rest if s[0] == cur), None)
                if nxt is None:
                    break
                rest.remove(nxt)
                ordered.append(nxt)
                cur = nxt[1]
            chain[ent] = ordered + rest   # leftovers break the chain check below
        ok = True
        for ent, steps in chain.items():
            if not steps or any(s not in ALLOWED[ent] for s in steps) or len(set(steps)) != len(steps):
                ok = False
            elif any(steps[i][1] != steps[i + 1][0] for i in range(len(steps) - 1)):
                ok = False
        final_r = chain['reservation'][-1][1] if chain['reservation'] else None
        final_p = chain['payment'][-1][1] if chain['payment'] else None
        if not ok or final_r != r[2] or final_p != r[5] or len(chain['reservation']) != len(chain['payment']):
            bad_hist += 1
        e = ev_by.get(rid, Counter())
        conf = sum(1 for s in chain['reservation'] if s[1] == 'CONFIRMED')
        canc = sum(1 for s in chain['reservation'] if s[1] == 'CANCELLED')
        if e['reservation_requested'] != 1 or e['payment_completed'] != conf or e['reservation_cancelled'] != canc:
            bad_event += 1
    check(missing_pay == 0, f'{missing_pay} reservations without payment')
    check(bad_pair == 0, f'{bad_pair} reservations whose reservation/payment states disagree')
    check(bad_amount == 0, f'{bad_amount} reservations whose payment amount differs')
    check(bad_hist == 0, f'{bad_hist} reservations with an invalid or inconsistent status history')
    check(bad_event == 0, f'{bad_event} reservations whose business events do not match the history')
    orphan_hist = sum(1 for rid in h_by if rid not in all_res)
    check(orphan_hist == 0, f'{orphan_hist} history rows without reservation')

    # runner evidence vs DB
    log = jsonl(d / 'reservations.jsonl')
    created = {x['id'] for x in log if 'request_key' in x and x.get('status') == 201 and x.get('id')}
    unknown = [x for x in log if 'request_key' in x and (x.get('status', 0) == 0 or x.get('status', 0) >= 500)]
    cons = json.loads((d / 'consistency_requests.json').read_text(encoding='utf-8')) \
        if (d / 'consistency_requests.json').exists() else {'duplicate': [], 'race': [], 'tracking': []}
    known = created | {i for x in cons['duplicate'] for i in x['ids']} | {x['reservation_id'] for x in cons['race']}
    missing = created - set(by_res)
    unexplained = set(by_res) - known
    check(not missing, f'{len(missing)} reservations acknowledged with 201 are missing in DB')
    if unexplained:
        (errors if len(unexplained) > len(unknown) else notes).append(
            f'{len(unexplained)} DB reservations not acknowledged to the runner (unknown-outcome requests: {len(unknown)})')

    # duplicate request_key
    keys = Counter((r[1], r[3]) for r in res)
    dup_keys = [k for k, n in keys.items() if n > 1]
    check(not dup_keys, f'{len(dup_keys)} duplicated (user, request_key)')
    dup_results = []
    for x in cons['duplicate']:
        n = keys.get((x['user_id'], x['request_key']), 0)
        dup_results.append({'request_key': x['request_key'], 'db_rows': n, 'codes': Counter(x['codes'])})
        check(n == 1 and len(x['ids']) == 1, f'duplicate test key {x["request_key"]}: {n} rows, ids {x["ids"]}')
    race_results = []
    for x in cons['race']:
        r = by_res.get(x['reservation_id'])
        chain = [(h[2], h[3]) for h in h_by.get(x['reservation_id'], []) if h[1] == 'reservation']
        race_results.append({'reservation_id': x['reservation_id'], 'codes': Counter(x['codes']),
                             'final': (r[2], r[5]) if r else None, 'reservation_chain': chain})
        check(r is not None and (r[2], r[5]) in PAIRS, f'race {x["reservation_id"]}: bad final state')

    # tracking
    sent = jsonl(d / 'events_sent.jsonl')
    accepted_ids, resend_ids, failed_ids = set(), set(), set()
    acc_sum = dup_sum = sent_n = 0
    for b in sent:
        if b['status'] == 202 and b.get('result'):
            accepted_ids.update(b['ids'])
            acc_sum += b['result']['accepted']
            dup_sum += b['result']['duplicates']
            sent_n += len(b['ids'])
        else:
            failed_ids.update(b['ids'])
    for batch in cons['tracking']:
        resend_ids.update(batch)
    col = counter.mdb[counter.collection_name]
    stored = set()
    id_list = list(accepted_ids | failed_ids)
    for i in range(0, len(id_list), 5000):
        stored.update(x['_id'] for x in col.find({'_id': {'$in': id_list[i:i + 5000]}}, {'_id': 1}))
    lost = accepted_ids - stored
    check(not lost, f'{len(lost)} accepted tracking events missing in MongoDB')
    check(acc_sum + dup_sum == sent_n, f'tracking accepted+duplicates {acc_sum + dup_sum} != sent {sent_n}')
    run_docs = totals['mongo']
    check(run_docs == len(stored & accepted_ids) + len(stored & (failed_ids - accepted_ids)),
          'MongoDB docs for this run differ from the runner evidence')
    check(acc_sum == len(accepted_ids) or acc_sum <= len(accepted_ids),
          'more accepted events than unique ids (duplicate storage)')
    resend_stored = len(stored & resend_ids)
    check(resend_stored == len(resend_ids), f'resend test: {resend_stored}/{len(resend_ids)} stored once')

    # MariaDB business events vs runner (event_post) and server-side events
    ev_types = Counter(t for t, _ in evs)
    t = totals['total']
    report = {
        'run_id': args.run_id, 'passed': not errors, 'errors': errors, 'notes': notes,
        'counts': totals, 'event_types': dict(ev_types),
        'target_min_50000': t >= 50_000, 'cap_total_100000_ok': t <= 100_000,
        'cap_mongo_50000_ok': totals['mongo'] <= 50_000,
        'reservations': {'total': len(by_res), 'by_state': dict(Counter(f'{r[2]}/{r[5]}' for r in res))},
        'tracking': {'batches': len(sent), 'accepted_sum': acc_sum, 'duplicates_sum': dup_sum, 'sent_in_202': sent_n,
                     'unique_accepted_ids': len(accepted_ids), 'failed_batch_ids': len(failed_ids - accepted_ids),
                     'failed_but_stored': len(stored & (failed_ids - accepted_ids)), 'lost': len(lost)},
        'duplicate_test': dup_results, 'race_test': race_results,
    }
    infra.save_json(d / 'verification.json', report)
    print(json.dumps({k: report[k] for k in ('passed', 'errors', 'notes', 'counts', 'reservations', 'tracking')},
                     ensure_ascii=False, indent=1, default=str))
    return 0 if not errors else 1


if __name__ == '__main__':
    raise SystemExit(main())
