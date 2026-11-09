"""Load test runner for the deployed service (docs/loadTestPlan.md).

Run from the repository root with the loadtest venv:
    PY=syntheticData/loadtest/.venv/Scripts/python.exe
    $PY syntheticData/loadtest/run_load.py init     --run-id <id>
    $PY syntheticData/loadtest/run_load.py accounts --run-id <id>
    $PY syntheticData/loadtest/run_load.py run      --run-id <id> [--phases precheck,read,mixed,...]

Why not `postman performance run`: it needs a cloud collection id and has no shared write budget,
no interval-based auto stop and no way to keep per-VU accounts/tokens apart. Postman CLI is used
for the functional pre-check (`precheck.postman_collection.json`); the load itself runs here.

Safety:
- one process, one asyncio loop, one Budget shared by every VU and phase (persisted for resume)
- every write reserves its worst-case record count first; unknown outcomes stay reserved
- DB counts are polled every 30 s and raise the budget floor; quiet points reconcile exactly
- stop: >5 % failures in the last 30 s, p95 > 3 s in the last 60 s, host down/restart,
  MariaDB connections >= 90 % of max, disk < 1 GB, budget exhausted, or a STOP file in the run dir
- credentials come from backend/.env; passwords/tokens are never printed
"""
from __future__ import annotations

import argparse
import asyncio
import csv
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
import json
import math
import os
import random
import secrets
import statistics
import sys
import time
import uuid

import httpx
import psutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from budget import Budget  # noqa: E402
import infra  # noqa: E402

BASE_URL = 'https://www.yaaho.kro.kr'
API = '/api/v1'
KST = timezone(timedelta(hours=9))
TOTAL_CAP, MONGO_CAP = 100_000, 50_000
FIRST_NEW, LAST_NEW = 101, 200            # personas used as load accounts (new accounts only)
READ_P95_MS, WRITE_P95_MS, FAIL_PASS = 500, 1000, 0.01
STOP_FAIL_30S, STOP_P95_60S_MS = 0.05, 3000
REQUEST_TIMEOUT = 10.0
WRITE_APIS = {'reservation_create', 'reservation_complete', 'reservation_cancel', 'tracking', 'event_post', 'signup'}
PREMIUM = 30000

# Phase budget ceilings (cumulative used_total / used_mongo at which a phase must stop starting writes).
PHASE_LIMITS = {
    'accounts': (500, 0), 'precheck': (1_500, 700), 'read': (1_500, 700),
    'mixed': (34_000, 17_000), 'spike_city': (43_000, 21_500), 'spike_baseball': (52_000, 26_000),
    'consistency': (54_000, 27_000), 'sustained': (TOTAL_CAP - 2_000, MONGO_CAP - 1_000),
    'stress': (TOTAL_CAP - 2_000, MONGO_CAP - 1_000),
}
RAMP = [10, 25, 50, 100]
STAGE_SECONDS = 300


class Stop(Exception):
    pass


def now_kst() -> str:
    return datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')


def iso_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def p(values, q):
    if not values:
        return None
    s = sorted(values)
    k = max(0, math.ceil(q * len(s)) - 1)
    return s[k]


# ---------------------------------------------------------------------------------------------
@dataclass
class Account:
    persona: dict
    email: str
    user_id: str | None = None
    token: str | None = None
    token_at: float = 0.0
    anonymous_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class Run:
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.dir = infra.run_dir(run_id)
        self.state_path = self.dir / 'state.json'
        self.state = json.loads(self.state_path.read_text(encoding='utf-8'))
        self.budget = Budget.restore(self.state['budget']) if self.state.get('budget') else Budget(TOTAL_CAP, MONGO_CAP)
        self.env = infra.load_env()
        self.counter = infra.Counter(self.env, self.state.get('mongo_collection') or 'events')
        self.counter.maria_baseline = self.state.get('maria_baseline') or {}
        profiles = {u['id']: u for u in json.loads(infra.PROFILES.read_text(encoding='utf-8'))['users']}
        self.accounts = [Account(profiles[pid], a['email'], a.get('user_id'), anonymous_id=a['anonymous_id'])
                         for pid, a in self.state['accounts'].items()]
        self.phase = self.stage = ''
        self.stop_reason: str | None = None     # run-wide abort
        self.stop_fatal = False                  # False: performance stop (later, smaller phases may run)
        self.stage_stop: str | None = None      # current stage only (e.g. phase budget)
        self.rows: deque = deque()              # (t, latency_ms, ok, normal) of current stage, for monitoring
        self.stage_rows: list = []              # full rows of current stage, for pass/fail
        self.csv_file = open(self.dir / 'requests.csv', 'a', newline='', encoding='utf-8')
        self.csv = csv.writer(self.csv_file)
        if self.csv_file.tell() == 0:
            self.csv.writerow(['ts', 'phase', 'stage', 'vu', 'api', 'method', 'status', 'latency_ms', 'ok',
                               'class', 'error'])
        self.timeline = open(self.dir / 'timeline.jsonl', 'a', encoding='utf-8')
        self.events_log = open(self.dir / 'events_sent.jsonl', 'a', encoding='utf-8')
        self.res_log = open(self.dir / 'reservations.jsonl', 'a', encoding='utf-8')
        self.prom_log = open(self.dir / 'prom.jsonl', 'a', encoding='utf-8')
        self.inflight_http = 0
        self.active = set()
        self.visits_done = 0
        self.visit_stats: list = []             # (duration_s, kind) of completed visits in stage
        self.prom_baseline: dict | None = None
        self.performances: list = []
        self.by_category: dict = {}
        self.search_words: list = []
        self.max_vu_seen = 0
        self.ramps: dict = {}
        self.monitor_tick = 0.0
        self.max_connections = 0
        self.stress = dict(STRESS)
        self.stress_mix = 'blend'

    # ---- persistence -------------------------------------------------------------------------
    def save(self):
        self.state['budget'] = self.budget.snapshot()
        infra.save_json(self.state_path, self.state)

    def log_event(self, kind: str, **data):
        rec = {'ts': iso_utc(), 'kst': now_kst(), 'kind': kind, 'phase': self.phase, 'stage': self.stage, **data}
        with open(self.dir / 'progress.jsonl', 'a', encoding='utf-8') as f:
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + '\n')
        print(f"[{rec['kst']}] {kind} {json.dumps(data, ensure_ascii=False, default=str)}", flush=True)

    def user_ids(self):
        return [a.user_id for a in self.accounts if a.user_id]

    def stopping(self) -> bool:
        if self.monitor_tick and time.time() - self.monitor_tick > 10 and not self.stop_reason:
            self.abort('monitor loop not running (watchdog)')
        return bool(self.stop_reason or self.stage_stop or (self.dir / 'STOP').exists())

    def abort(self, reason: str, fatal: bool = True):
        if not self.stop_reason:
            self.stop_reason, self.stop_fatal = reason, fatal
            self.log_event('abort', reason=reason, fatal=fatal)

    def clear_performance_abort(self, stage: str) -> bool:
        """After a non-fatal (latency/error) stop: record it and allow the next phase."""
        if self.stop_reason and not self.stop_fatal:
            self.state.setdefault('aborts', []).append({'stage': stage, 'reason': self.stop_reason})
            self.stop_reason = None
            return True
        return False

    # ---- HTTP ---------------------------------------------------------------------------------
    async def call(self, client: httpx.AsyncClient, vu: int, api: str, method: str, path: str, *,
                   acc: Account | None = None, body=None, cost: tuple[int, int] | None = None,
                   check=None, stored=None, expected=(200,), conflict_ok=(), normal=True):
        """One request. `stored(resp)` returns (total, mongo) records actually stored for a known outcome."""
        if self.stopping():
            raise Stop()
        res = None
        if cost:
            lt, lm = PHASE_LIMITS[self.phase]
            res = self.budget.reserve(cost[0], cost[1], lt, lm)
            if res is None:
                used = self.budget.snapshot()
                at_global = (used['used_total'] + cost[0] > TOTAL_CAP or used['used_mongo'] + cost[1] > MONGO_CAP)
                if at_global:
                    self.abort('global write budget reached')
                elif not self.stage_stop:
                    self.stage_stop = f'phase write budget reached ({self.phase})'
                    self.log_event('stage_stop', reason=self.stage_stop, budget=used)
                raise Stop()
        headers = {'Authorization': f'Bearer {acc.token}'} if acc and acc.token else {}
        t0 = time.perf_counter()
        status, err, resp = 0, '', None
        self.inflight_http += 1
        try:
            resp = await client.request(method, API + path, json=body, headers=headers)
            status = resp.status_code
        except httpx.TimeoutException as exc:
            err = 'timeout:' + type(exc).__name__
        except httpx.HTTPError as exc:
            err = 'http:' + type(exc).__name__
        finally:
            self.inflight_http -= 1
        lat = (time.perf_counter() - t0) * 1000
        klass = 'ok'
        ok = status in expected
        if ok and check:
            try:
                ok = bool(check(resp))
            except Exception:
                ok = False
            if not ok:
                err = err or 'check_failed'
        if not ok and status in conflict_ok:
            klass, ok = 'expected_conflict', True
        elif not ok:
            klass = 'fail'
        if res is not None:
            if status == 0 or status >= 500:
                self.budget.mark_unknown(res)
            elif 400 <= status < 500:
                self.budget.settle(res, 0, 0)
            else:
                try:
                    t, m = stored(resp) if stored else cost
                except Exception:
                    t, m = cost
                    self.budget.mark_unknown(res)
                    res = None
                if res is not None:
                    self.budget.settle(res, t, m)
        ts = time.time()
        self.csv.writerow([f'{ts:.3f}', self.phase, self.stage, vu, api, method, status, f'{lat:.1f}',
                           int(ok), klass, err])
        row = (ts, api, status, lat, ok, klass, normal)
        self.stage_rows.append(row)
        if normal:
            self.rows.append((ts, lat, ok))
        return resp, ok

    # ---- account helpers ------------------------------------------------------------------------
    async def login(self, client, acc: Account, vu: int):
        body = {'email': acc.email, 'password': self.state['password']}
        r, ok = await self.call(client, vu, 'login', 'POST', '/auth/login', body=body,
                                check=lambda r: r.json()['user']['id'] == acc.user_id, normal=False)
        if not ok:
            self.abort(f'login failed for {acc.email} ({r.status_code if r is not None else "no response"})')
            raise Stop()
        acc.token, acc.token_at = r.json()['access_token'], time.time()

    async def ensure_token(self, client, acc: Account, vu: int):
        if not acc.token or time.time() - acc.token_at > 45 * 60:
            await self.login(client, acc, vu)

    # ---- tracking -------------------------------------------------------------------------------
    def ev(self, acc: Account, session: str, etype: str, path: str, **props):
        props.update(synthetic=True, loadtest=True, loadtest_run_id=self.run_id, synthetic_run_id=self.run_id,
                     synthetic_persona_id=acc.persona['id'], loadtest_stage=self.stage)
        return {'event_id': str(uuid.uuid4()), 'type': etype, 'occurred_at': iso_utc(), 'session_id': session,
                'anonymous_id': acc.anonymous_id, 'page': {'path': path, 'referrer': ''}, 'props': props,
                'schema_version': 1}

    async def flush(self, client, vu, acc, events: list, api='tracking', normal=True, expected_dup=False):
        for i in range(0, len(events), 10):
            batch = events[i:i + 10]
            n = len(batch)

            def check(r, n=n):
                d = r.json()
                return d['accepted'] + d['duplicates'] == n and (expected_dup or d['duplicates'] == 0)

            r, ok = await self.call(client, vu, api, 'POST', '/tracking/events', acc=acc, body={'events': batch},
                                    cost=(n, n), expected=(202,), check=check, normal=normal,
                                    stored=lambda r: (r.json()['accepted'], r.json()['accepted']))
            info = r.json() if (r is not None and r.status_code == 202) else None
            self.events_log.write(json.dumps({'ts': time.time(), 'stage': self.stage,
                                              'status': r.status_code if r is not None else 0,
                                              'ids': [e['event_id'] for e in batch], 'result': info}) + '\n')

    # ---- data -----------------------------------------------------------------------------------
    async def load_catalog(self, client):
        r = await client.get(API + '/performances', params={'sort': 'date'})
        r.raise_for_status()
        self.performances = r.json()
        self.by_category = {}
        for perf in self.performances:
            self.by_category.setdefault(perf['category'], []).append(perf['id'])
        words = set()
        for perf in self.performances:
            for w in perf['title'].replace(':', ' ').split():
                if len(w) >= 2 and w.isalnum():
                    words.add(w)
        self.search_words = sorted(words)[:300]

    def pick_performance(self, acc: Account) -> str:
        weights = acc.persona['category_weights']
        cats = [c for c in weights if c in self.by_category]
        cat = random.choices(cats, [weights[c] for c in cats])[0]
        return random.choice(self.by_category[cat])


# ---------------------------------------------------------------------------------------------
# Visit scenarios. Each returns the visit kind. All requests go through Run.call.
async def think(lo, hi):
    await asyncio.sleep(random.uniform(lo, hi))


def is_list(r):
    d = r.json()   # parse once: the popular list is ~266 KB and the generator is CPU bound
    return isinstance(d, list) and len(d) > 0


async def visit_read(run: Run, c, vu, acc, cfg):
    await run.call(c, vu, 'list', 'GET', '/performances?sort=popular', check=is_list)
    await think(*cfg['think'])
    await run.call(c, vu, 'ranking', 'GET', '/performances/ranking', check=is_list)
    if random.random() < 0.3:
        await think(*cfg['think'])
        q = random.choice(run.search_words)
        await run.call(c, vu, 'search', 'GET', f'/performances?q={q}', check=lambda r: isinstance(r.json(), list))
    if random.random() < 0.3:
        await think(*cfg['think'])
        cat = random.choice(list(run.by_category))
        sort = random.choice(['date', 'price'])
        await run.call(c, vu, 'category', 'GET', f'/performances?category={cat}&sort={sort}', check=is_list)
    for _ in range(random.randint(1, 3)):
        await think(*cfg['think'])
        pid = run.pick_performance(acc)
        await run.call(c, vu, 'detail', 'GET', f'/performances/{pid}', check=lambda r, pid=pid: r.json()['id'] == pid)
    return 'read'


async def reserve_flow(run: Run, c, vu, acc, session, events, detail: dict, pay: bool, cfg):
    pid = detail['id']
    await run.call(c, vu, 'event_post', 'POST', '/events', acc=acc,
                   body={'performance_id': pid, 'type': 'booking_started'}, cost=(1, 0), expected=(201,),
                   stored=lambda r: (1, 0))
    events.append(run.ev(acc, session, 'booking_start', '/', performance_id=pid))
    await think(*cfg['think'])
    grade = random.choice(['STANDARD', 'STANDARD', 'PREMIUM'])
    qty = random.choices([1, 2, 3, 4], [45, 35, 12, 8])[0]
    body = {'performance_id': pid, 'performance_date': random.choice(detail['available_dates']),
            'session_time': random.choice(detail['slots']), 'seat_grade': grade, 'quantity': qty,
            'request_key': str(uuid.uuid4())}
    amount = (detail['price'] + (PREMIUM if grade == 'PREMIUM' else 0)) * qty

    def check_created(r):
        d = r.json()
        return d['status'] == 'REQUESTED' and d['payment_status'] == 'PENDING' and d['amount'] == amount

    r, ok = await run.call(c, vu, 'reservation_create', 'POST', '/reservations', acc=acc, body=body,
                           cost=(5, 0), expected=(201,), check=check_created,
                           stored=lambda r: (5, 0) if r.status_code == 201 else (0, 0))
    rid = r.json().get('id') if (r is not None and r.status_code in (200, 201)) else None
    run.res_log.write(json.dumps({'ts': time.time(), 'stage': run.stage, 'user_id': acc.user_id,
                                  'request_key': body['request_key'], 'status': r.status_code if r is not None else 0,
                                  'id': rid, 'amount': amount, 'pay': pay}) + '\n')
    if not rid:
        return
    events.append(run.ev(acc, session, 'reservation_request', '/', performance_id=pid, reservation_id=rid))
    await think(*cfg['think'])
    await run.call(c, vu, 'reservations_list', 'GET', '/reservations', acc=acc,
                   check=lambda r: any(x['id'] == rid for x in r.json()))
    if pay:
        await think(*cfg['think'])
        r2, ok2 = await run.call(c, vu, 'reservation_complete', 'POST', f'/reservations/{rid}/complete', acc=acc,
                                 cost=(3, 0), check=lambda r: r.json()['status'] == 'CONFIRMED'
                                 and r.json()['payment_status'] == 'COMPLETED', stored=lambda r: (3, 0))
        run.res_log.write(json.dumps({'ts': time.time(), 'id': rid, 'action': 'complete',
                                      'status': r2.status_code if r2 is not None else 0}) + '\n')
        if ok2:
            events.append(run.ev(acc, session, 'payment_complete', '/mypage', reservation_id=rid, amount=amount))
            await think(*cfg['think'])
            await run.call(c, vu, 'payments_list', 'GET', '/payments', acc=acc,
                           check=lambda r: any(x['reservation_id'] == rid and x['status'] == 'COMPLETED'
                                               for x in r.json()))


async def view_detail(run: Run, c, vu, acc, session, events, pid):
    r, ok = await run.call(c, vu, 'detail', 'GET', f'/performances/{pid}', check=lambda r: r.json()['id'] == pid)
    if not ok:
        return None
    await run.call(c, vu, 'event_post', 'POST', '/events', acc=acc, body={'performance_id': pid},
                   cost=(1, 0), expected=(201,), stored=lambda r: (1, 0))
    events.append(run.ev(acc, session, 'performance_view', f'/performances/{pid}', performance_id=pid))
    return r.json()


async def visit_mixed(run: Run, c, vu, acc, cfg):
    await run.ensure_token(c, acc, vu)
    session = str(uuid.uuid4())
    roll = random.random()
    mix = cfg['mix']
    kind = 'browse' if roll < mix[0] else ('reserve' if roll < mix[0] + mix[1] else 'pay')
    events = [run.ev(acc, session, 'page_view', '/', visit_kind=kind)]
    try:
        await run.call(c, vu, 'list', 'GET', '/performances?sort=popular', check=is_list)
        if random.random() < 0.5:
            await think(*cfg['think'])
            await run.call(c, vu, 'ranking', 'GET', '/performances/ranking', check=is_list)
        if random.random() < 0.2:
            await think(*cfg['think'])
            q = random.choice(run.search_words)
            await run.call(c, vu, 'search', 'GET', f'/performances?q={q}', check=lambda r: isinstance(r.json(), list))
            events.append(run.ev(acc, session, 'search', '/', query=q))
        picks = random.randint(1, 2) if kind == 'browse' else 1
        detail = None
        for _ in range(picks):
            await think(*cfg['think'])
            detail = await view_detail(run, c, vu, acc, session, events, run.pick_performance(acc))
        if kind != 'browse' and detail:
            await think(*cfg['think'])
            await reserve_flow(run, c, vu, acc, session, events, detail, kind == 'pay', cfg)
    finally:
        if events and not run.stopping():
            await run.flush(c, vu, acc, events)
    return kind


async def visit_focus(run: Run, c, vu, acc, cfg):
    """Opening rush on one performance (city / baseball)."""
    await run.ensure_token(c, acc, vu)
    session = str(uuid.uuid4())
    pid = cfg['performance']
    events = [run.ev(acc, session, 'page_view', '/', visit_kind='focus')]
    kind = 'focus_view'
    try:
        detail = await view_detail(run, c, vu, acc, session, events, pid)
        if detail and random.random() < cfg['book_p']:
            pay = random.random() < cfg['pay_p']
            kind = 'focus_pay' if pay else 'focus_reserve'
            await think(*cfg['think'])
            await reserve_flow(run, c, vu, acc, session, events, detail, pay, cfg)
    finally:
        if events and not run.stopping():
            await run.flush(c, vu, acc, events)
    return kind


SCENARIOS = {'read': visit_read, 'mixed': visit_mixed, 'focus': visit_focus}


# ---------------------------------------------------------------------------------------------
def new_client():
    return httpx.AsyncClient(base_url=BASE_URL, timeout=REQUEST_TIMEOUT, http2=False,
                             headers={'User-Agent': 'tikit-loadtest/1.0 (synthetic)'},
                             limits=httpx.Limits(max_connections=4, max_keepalive_connections=2))


class Monitor:
    def __init__(self, run: Run):
        self.run = run
        self.prom = httpx.Client()
        self.last_prom = 0.0
        self.last_db = 0.0
        self.proc = psutil.Process()
        self.proc.cpu_percent(None)

    def check_http(self):
        run = self.run
        now = time.time()
        while run.rows and run.rows[0][0] < now - 60:
            run.rows.popleft()
        last30 = [r for r in run.rows if r[0] >= now - 30]
        if len(last30) >= 20:
            fail = sum(1 for r in last30 if not r[2]) / len(last30)
            if fail > STOP_FAIL_30S:
                run.abort(f'failure rate {fail:.1%} in last 30 s > 5 %', fatal=False)
        if len(run.rows) >= 20:
            p95 = p([r[1] for r in run.rows], 0.95)
            if p95 > STOP_P95_60S_MS:
                run.abort(f'p95 {p95:.0f} ms in last 60 s > 3 s', fatal=False)

    def check_prom(self, sample: dict):
        """Only numeric values are compared; query errors are handled by the staleness check."""
        run = self.run

        def nums(name):
            v = sample.get(name, {})
            return {k: x for k, x in v.items() if isinstance(x, (int, float))} if isinstance(v, dict) else {}
        up = nums('up')
        if not any(h in up for h in infra.APP_HOSTS):
            return False   # sample unusable
        if run.prom_baseline is None:
            run.prom_baseline = {'boot_time': nums('boot_time')}
        for host in infra.HOSTS.values():
            if up.get(host) == 0.0:
                run.abort(f'host {host} is down (node exporter up=0)')
        base_boot = run.prom_baseline.get('boot_time', {})
        for host, bt in nums('boot_time').items():
            if host in base_boot and abs(bt - base_boot[host]) > 5:
                run.abort(f'host {host} rebooted')
        tc = nums('mysql_threads_connected').get('mariadb-171')
        mc = nums('mysql_max_connections').get('mariadb-171')
        if tc and mc and tc >= 0.9 * mc:
            run.abort(f'MariaDB connections {tc:.0f}/{mc:.0f} >= 90 %')
        for host, avail in nums('disk_avail_bytes').items():
            if avail < 1e9:
                run.abort(f'disk on {host} below 1 GB')
        return True

    async def _prom_poll(self):
        sample = await asyncio.wait_for(asyncio.to_thread(infra.prom_sample, self.prom), timeout=40)
        sample.update(phase=self.run.phase, stage=self.run.stage)
        self.run.prom_log.write(json.dumps(sample) + '\n')
        if self.check_prom(sample):
            self.last_prom_ok = time.time()

    async def _db_poll(self):
        run = self.run
        tot = await asyncio.wait_for(asyncio.to_thread(run.counter.totals, run.run_id, run.user_ids()), timeout=25)
        run.budget.observe_db(tot['total'], tot['mongo'])
        self.last_db_ok = time.time()
        with open(run.dir / 'budget.jsonl', 'a', encoding='utf-8') as f:
            f.write(json.dumps({'ts': time.time(), 'stage': run.stage, 'db': tot, 'budget': run.budget.snapshot()}) + '\n')

    def _db_status_sync(self):
        import db_snapshot
        with self.run.counter.engine.connect() as c:
            st = db_snapshot.maria_status(c)
        return st

    async def _db_status_poll(self):
        run = self.run
        st = await asyncio.wait_for(asyncio.to_thread(self._db_status_sync), timeout=8)
        rec = {'ts': time.time(), 'stage': run.stage, 'target_vu': run.target_vu, **st}
        with open(run.dir / 'db_status.jsonl', 'a', encoding='utf-8') as f:
            f.write(json.dumps(rec) + '\n')
        tc = st.get('Threads_connected')
        if isinstance(tc, float) and run.max_connections and tc >= 0.9 * run.max_connections:
            run.abort(f'MariaDB connections {tc:.0f}/{run.max_connections} >= 90 % (direct status)')

    async def loop(self, stop_evt: asyncio.Event):
        """Never awaits slow I/O inline: polls run as separate tasks and only their age is checked here."""
        run = self.run
        psutil.cpu_percent(None)
        net0 = psutil.net_io_counters()
        t_net = time.time()
        self.last_prom_ok = self.last_db_ok = time.time()
        prom_task = db_task = st_task = None
        last_st = 0.0
        while not stop_evt.is_set():
            await asyncio.sleep(1)
            try:
                now = time.time()
                run.monitor_tick = now
                net = psutil.net_io_counters()
                dt = max(1e-6, now - t_net)
                rec = {'ts': round(now, 3), 'phase': run.phase, 'stage': run.stage, 'target_vu': run.target_vu,
                       'active_vu': len(run.active), 'inflight_http': run.inflight_http,
                       'visits_done': run.visits_done,
                       'gen_cpu_pct': psutil.cpu_percent(None), 'gen_proc_cpu_pct': self.proc.cpu_percent(None),
                       'gen_tx_Bps': round((net.bytes_sent - net0.bytes_sent) / dt),
                       'gen_rx_Bps': round((net.bytes_recv - net0.bytes_recv) / dt),
                       'budget_used_total': run.budget.used_total(), 'budget_used_mongo': run.budget.used_mongo()}
                net0, t_net = net, now
                run.timeline.write(json.dumps(rec) + '\n')
                self.check_http()
                if (run.dir / 'STOP').exists():
                    run.abort('STOP file present')
                for task, name in ((prom_task, 'prometheus'), (db_task, 'db'), (st_task, 'db_status')):
                    if task is not None and task.done() and task.exception() is not None:
                        run.log_event('poll_error', source=name, error=type(task.exception()).__name__)
                if (prom_task is None or prom_task.done()) and now - self.last_prom >= 15:
                    self.last_prom = now
                    prom_task = asyncio.create_task(self._prom_poll())
                if (st_task is None or st_task.done()) and now - last_st >= 10:
                    last_st = now
                    st_task = asyncio.create_task(self._db_status_poll())
                if (db_task is None or db_task.done()) and now - self.last_db >= 30:
                    self.last_db = now
                    db_task = asyncio.create_task(self._db_poll())
                    for fh in (run.csv_file, run.timeline, run.events_log, run.res_log, run.prom_log):
                        fh.flush()
                    run.save()
                # Without observation no load is allowed (docs/loadTestPlan.md 3.1-9).
                if run.target_vu and now - self.last_prom_ok > 45:
                    run.abort(f'Prometheus unavailable for {now - self.last_prom_ok:.0f} s (no observation)')
                if run.target_vu and now - self.last_db_ok > 90:
                    run.abort(f'DB count poll unavailable for {now - self.last_db_ok:.0f} s (budget floor stale)')
            except Exception as exc:
                run.abort(f'monitor error {type(exc).__name__}: {exc}'[:200])
        for t in (prom_task, db_task, st_task):
            if t is not None and not t.done():
                t.cancel()


Run.target_vu = 0


async def run_stage(run: Run, phase: str, name: str, scenario: str, cfg: dict, duration: float, profile) -> dict:
    """profile(t) -> target VU at second t of the stage."""
    run.phase, run.stage, run.stage_stop = phase, name, None
    run.rows.clear()
    run.stage_rows = []
    run.visit_stats = []
    run.visits_done = 0
    max_vu = max(profile(t) for t in range(int(duration) + 1))
    start = time.time()
    committed0 = (run.budget.committed_total, run.budget.committed_mongo)
    run.log_event('stage_start', scenario=scenario, max_vu=max_vu, duration_s=duration, cfg=cfg,
                  budget=run.budget.snapshot())
    done = asyncio.Event()

    blend = cfg.get('blend')

    async def vu_loop(i: int):
        if blend:   # VU i runs blend[i % n]; consecutive VUs share one account, so writers never share
            sc_name, vcfg = blend[i % len(blend)]
            acc = run.accounts[(i // len(blend)) % len(run.accounts)]
        else:
            sc_name, vcfg = scenario, cfg
            acc = run.accounts[i % len(run.accounts)]
        async with new_client() as c:
            while not done.is_set() and not run.stopping():
                if i >= run.target_vu:
                    run.active.discard(i)
                    await asyncio.sleep(0.1)
                    continue
                run.active.add(i)
                t0 = time.time()
                try:
                    kind = await SCENARIOS[sc_name](run, c, i, acc, vcfg)
                    run.visits_done += 1
                    run.visit_stats.append((time.time() - t0, kind))
                except Stop:
                    break
                except Exception as exc:  # unexpected client-side error: record, keep going
                    run.log_event('vu_error', vu=i, error=f'{type(exc).__name__}: {exc}'[:200])
                    await asyncio.sleep(1)
                if done.is_set() or run.stopping():
                    break
                await think(*vcfg['pause'])
        run.active.discard(i)

    async def controller():
        while not done.is_set():
            t = time.time() - start
            if t >= duration or run.stopping():
                done.set()
                break
            run.target_vu = profile(t)
            await asyncio.sleep(0.2)
        run.target_vu = 0

    tasks = [asyncio.create_task(vu_loop(i)) for i in range(max_vu)]
    ctl = asyncio.create_task(controller())
    await ctl
    # Let in-flight requests finish so the budget knows their outcome (requests time out after 10 s).
    finished, pending = await asyncio.wait(tasks, timeout=REQUEST_TIMEOUT + 20)
    for t in pending:
        t.cancel()
    run.active.clear()
    end = time.time()
    result = evaluate(run, phase, name, scenario, start, end, max_vu, cfg, committed0)
    run.state.setdefault('stages', []).append(result)
    run.save()
    run.log_event('stage_end', **{k: result[k] for k in ('name', 'passed', 'reason', 'requests', 'rps', 'fail_rate',
                                                         'visits', 'records_committed')})
    return result


def evaluate(run: Run, phase, name, scenario, start, end, max_vu, cfg, committed0) -> dict:
    rows = run.stage_rows
    normal = [r for r in rows if r[6]]
    per_api = {}
    for r in rows:
        per_api.setdefault(r[1], []).append(r)
    apis = {}
    problems = []
    for api, rs in sorted(per_api.items()):
        lats = [r[3] for r in rs]
        fails = sum(1 for r in rs if not r[4])
        conflicts = sum(1 for r in rs if r[5] == 'expected_conflict')
        statuses = {}
        for r in rs:
            statuses[str(r[2])] = statuses.get(str(r[2]), 0) + 1
        limit = WRITE_P95_MS if api in WRITE_APIS else READ_P95_MS
        d = {'requests': len(rs), 'fail': fails, 'fail_rate': fails / len(rs), 'expected_conflicts': conflicts,
             'rps': len(rs) / max(1e-9, end - start), 'p50': p(lats, .5), 'p95': p(lats, .95), 'p99': p(lats, .99),
             'max': max(lats), 'p95_limit': limit, 'statuses': statuses}
        apis[api] = d
        if rs[0][6] and len(rs) >= 20:
            if d['p95'] > limit:
                problems.append(f'{api} p95 {d["p95"]:.0f} ms > {limit}')
            if d['fail_rate'] >= FAIL_PASS:
                problems.append(f'{api} failures {d["fail_rate"]:.2%}')
    fail_rate = (sum(1 for r in normal if not r[4]) / len(normal)) if normal else 0.0
    if fail_rate >= FAIL_PASS:
        problems.append(f'overall failures {fail_rate:.2%}')
    if run.stop_reason:
        problems.append('aborted: ' + run.stop_reason)
    if (run.dir / 'STOP').exists():
        problems.append('interrupted by STOP file')
    if not rows:
        problems.append('no requests')
    kinds = {}
    for _, k in run.visit_stats:
        kinds[k] = kinds.get(k, 0) + 1
    rec_t = run.budget.committed_total - committed0[0]
    rec_m = run.budget.committed_mongo - committed0[1]
    return {
        'phase': phase, 'name': name, 'scenario': scenario, 'max_vu': max_vu, 'cfg': cfg,
        'start': start, 'end': end, 'start_kst': datetime.fromtimestamp(start, KST).strftime('%H:%M:%S'),
        'end_kst': datetime.fromtimestamp(end, KST).strftime('%H:%M:%S'), 'duration_s': end - start,
        'requests': len(rows), 'rps': len(rows) / max(1e-9, end - start), 'fail_rate': fail_rate,
        'p95_all': p([r[3] for r in normal], .95), 'p99_all': p([r[3] for r in normal], .99),
        'visits': len(run.visit_stats), 'visit_kinds': kinds,
        'visit_avg_s': statistics.mean([d for d, _ in run.visit_stats]) if run.visit_stats else None,
        'records_committed': {'total': rec_t, 'mongo': rec_m}, 'apis': apis,
        'passed': not problems and not run.stage_stop, 'problems': problems,
        'reason': run.stop_reason or run.stage_stop or ('; '.join(problems) if problems else 'passed'),
        'budget_limited': bool(run.stage_stop and 'budget' in run.stage_stop),
        'budget_after': run.budget.snapshot(),
    }


async def recover(run: Run, seconds=60):
    """Idle gap between stages; reconcile budget exactly while nothing is in flight."""
    run.stage = 'recovery'
    await asyncio.sleep(seconds)
    try:
        tot = await asyncio.to_thread(run.counter.totals, run.run_id, run.user_ids())
        rec = run.budget.reconcile_quiet(tot['total'], tot['mongo'])
        rec['db'] = tot
        with open(run.dir / 'reconcile.jsonl', 'a', encoding='utf-8') as f:
            f.write(json.dumps({'ts': time.time(), 'kst': now_kst(), **rec}, default=str) + '\n')
        run.save()
        run.log_event('reconciled', db_total=tot['total'], db_mongo=tot['mongo'], maria=tot['maria'])
    except Exception as exc:
        run.log_event('reconcile_error', error=f'{type(exc).__name__}: {exc}'[:200])


def flat(v):
    return lambda t: v


RAMP_IN_S = 30


def ramp_in(v, secs=RAMP_IN_S):
    """Start VUs gradually over `secs` instead of all at the same instant (avoids a 0->v burst)."""
    return lambda t: max(1, min(v, round(v * t / secs))) if t < secs else v


def spike(base, peak):
    """Postman-like spike over 300 s: base 90 s -> ramp up 20 s -> ramp down 40 s -> base."""
    def f(t):
        if t < 90:
            return base
        if t < 110:
            return round(base + (peak - base) * (t - 90) / 20)
        if t < 150:
            return round(peak - (peak - base) * (t - 110) / 40)
        return base
    return f


def stress_profile(peak=200, up=900, hold=180, down=120):
    """Stress curve: 1 -> peak linearly over `up` s, hold `hold` s, peak -> 0 over `down` s."""
    def f(t):
        if t < up:
            return max(1, round(1 + (peak - 1) * t / up))
        if t < up + hold:
            return peak
        return max(0, round(peak * (up + hold + down - t) / down))
    return f


STRESS = {'peak': 200, 'up': 900, 'hold': 180, 'down': 120}


MIXED_CFG = {'mix': (0.80, 0.15, 0.05), 'think': (1.0, 2.0), 'pause': (5.0, 10.0)}
READ_CFG = {'think': (0.2, 0.6), 'pause': (0.5, 1.5)}


def focus_cfg(pid):
    return {'performance': pid, 'book_p': 0.4, 'pay_p': 0.5, 'think': (0.3, 0.8), 'pause': (1.0, 3.0)}


# ---------------------------------------------------------------------------------------------
async def consistency(run: Run):
    """Duplicate request_key, complete/cancel race, tracking resend. Small, budgeted."""
    run.phase, run.stage, run.stage_stop = 'consistency', 'consistency', None
    t_start = time.time()
    run.stage_rows, run.visit_stats = [], []
    run.rows.clear()
    out = {'duplicate': [], 'race': [], 'tracking': []}
    accs = run.accounts[:10]
    async with new_client() as c:
        for i, acc in enumerate(accs):
            await run.ensure_token(c, acc, i)
        detail = (await c.get(API + '/performances/city')).json()
        # 1) same member, same request_key, same body, 8 concurrent requests
        for i, acc in enumerate(accs):
            body = {'performance_id': 'city', 'performance_date': detail['available_dates'][0],
                    'session_time': detail['slots'][0], 'seat_grade': 'STANDARD', 'quantity': 1,
                    'request_key': str(uuid.uuid4())}
            calls = [run.call(c, i, 'dup_reservation', 'POST', '/reservations', acc=acc, body=body, cost=(5, 0),
                              expected=(200, 201), normal=False,
                              stored=lambda r: (5, 0) if r.status_code == 201 else (0, 0)) for _ in range(8)]
            rs = await asyncio.gather(*calls, return_exceptions=True)
            ids = sorted({r[0].json()['id'] for r in rs if not isinstance(r, Exception) and r[0] is not None
                          and r[0].status_code in (200, 201)})
            codes = [r[0].status_code if not isinstance(r, Exception) and r[0] is not None else 0 for r in rs]
            out['duplicate'].append({'user_id': acc.user_id, 'request_key': body['request_key'], 'ids': ids,
                                     'codes': codes})
        # 2) complete x3 and cancel x3 at the same time on a fresh reservation
        for i, acc in enumerate(accs):
            body = {'performance_id': 'baseball', 'performance_date': '2026-11-08', 'session_time': '18:00',
                    'seat_grade': 'STANDARD', 'quantity': 2, 'request_key': str(uuid.uuid4())}
            r, ok = await run.call(c, i, 'race_setup', 'POST', '/reservations', acc=acc, body=body, cost=(5, 0),
                                   expected=(201,), normal=False, stored=lambda r: (5, 0))
            if not ok:
                continue
            rid = r.json()['id']
            calls = []
            for action in ['complete', 'cancel'] * 3:
                calls.append(run.call(c, i, f'race_{action}', 'POST', f'/reservations/{rid}/{action}', acc=acc,
                                      cost=(3, 0), expected=(200,), conflict_ok=(409,), normal=False,
                                      stored=lambda r: (3, 0)))
            random.shuffle(calls)
            rs = await asyncio.gather(*calls, return_exceptions=True)
            codes = [r[0].status_code if not isinstance(r, Exception) and r[0] is not None else 0 for r in rs]
            final = (await c.get(API + '/reservations', headers={'Authorization': f'Bearer {acc.token}'})).json()
            fr = next((x for x in final if x['id'] == rid), None)
            out['race'].append({'reservation_id': rid, 'codes': codes,
                                'final': (fr['status'], fr['payment_status']) if fr else None})
        # 3) tracking: send 5 batches of 10, then resend each twice (concurrently)
        acc = accs[0]
        session = str(uuid.uuid4())
        for b in range(5):
            batch = [run.ev(acc, session, 'page_view', '/consistency', batch=b, seq=k) for k in range(10)]
            await run.flush(c, 0, acc, batch, api='track_first', normal=False)
            await asyncio.gather(*[run.flush(c, 0, acc, batch, api='track_resend', normal=False, expected_dup=True)
                                   for _ in range(2)])
            out['tracking'].append([e['event_id'] for e in batch])
    infra.save_json(run.dir / 'consistency_requests.json', out)
    res = evaluate(run, 'consistency', 'consistency', 'consistency', t_start, time.time(), 10, {}, (0, 0))
    res['details_file'] = 'consistency_requests.json'
    run.state.setdefault('stages', []).append(res)
    run.save()
    run.log_event('consistency_done', duplicate=len(out['duplicate']), race=len(out['race']))
    return out


# ---------------------------------------------------------------------------------------------
def sustained_cfg(run: Run, vu: int, minutes=30) -> dict:
    """Choose the pause between visits so 30 min at `vu` fits inside the remaining budget."""
    ref = [s for s in run.state.get('stages', []) if s['scenario'] == 'mixed' and s['visits'] > 0]
    ref = max(ref, key=lambda s: s['max_vu'])
    per_visit_t = ref['records_committed']['total'] / ref['visits']
    per_visit_m = ref['records_committed']['mongo'] / ref['visits']
    active = ref['visit_avg_s']
    lt, lm = PHASE_LIMITS['sustained']
    rem_t = lt - run.budget.used_total()
    rem_m = lm - run.budget.used_mongo()
    seconds = minutes * 60
    rate = min(rem_t / seconds / per_visit_t, rem_m / seconds / per_visit_m) * 0.95   # visits/s, 5 % margin
    cycle = vu / rate
    pause = max(1.0, cycle - active)
    cfg = dict(MIXED_CFG)
    cfg['pause'] = (pause * 0.8, pause * 1.2)
    cfg['pacing'] = {'reference_stage': ref['name'], 'records_per_visit': per_visit_t,
                     'mongo_per_visit': per_visit_m, 'visit_active_s': active, 'remaining_total': rem_t,
                     'remaining_mongo': rem_m, 'target_visits_per_s': rate, 'pause_mean_s': pause}
    return cfg


async def main_run(run: Run, phases: list[str]):
    done_phases = set(run.state.get('phases_done', []))
    mon = Monitor(run)
    mon_stop = asyncio.Event()
    mon_task = asyncio.create_task(mon.loop(mon_stop))
    run.log_event('run_start', phases=phases, budget=run.budget.snapshot())
    try:
        async with new_client() as c:
            await run.load_catalog(c)
        # baseline reconcile before any traffic
        await recover(run, seconds=0)
        try:
            from sqlalchemy import text
            with run.counter.engine.connect() as conn:
                run.max_connections = int(conn.execute(text('select @@max_connections')).scalar())
        except Exception as exc:
            run.log_event('max_connections_error', error=type(exc).__name__)
        results = run.state.setdefault('results', {})

        async def phase(name, make):
            if name not in phases or name in done_phases or run.stop_reason:
                return
            await make()
            if not run.stop_reason:
                run.state.setdefault('phases_done', []).append(name)
                done_phases.add(name)
            run.save()

        async def precheck():
            r = await run_stage(run, 'precheck', 'precheck-1vu', 'mixed',
                                {'mix': (0.4, 0.3, 0.3), 'think': (1.0, 2.0), 'pause': (3.0, 6.0)}, 120, flat(1))
            results['precheck_passed'] = r['passed']
            await recover(run, 30)
            tot = await asyncio.to_thread(run.counter.totals, run.run_id, run.user_ids())
            results['precheck_db'] = tot
            if tot['mongo'] == 0:
                found = await asyncio.to_thread(run.counter.find_run_collections, run.run_id)
                run.abort(f'no tracking docs found in {run.counter.collection_name}; found in {found}')
            if not r['passed']:
                run.abort('precheck failed: ' + r['reason'])

        async def ramp(phase_name, scenario, cfg):
            best = 0
            for vu in run.ramps.get(phase_name, RAMP):
                if run.stop_reason:
                    break
                r = await run_stage(run, phase_name, f'{phase_name}-{vu}vu', scenario, cfg, STAGE_SECONDS, ramp_in(vu))
                await recover(run, 60)
                if r['passed']:
                    best = vu
                else:
                    run.log_event('ramp_halt', stage=r['name'], reason=r['reason'])
                    run.clear_performance_abort(r['name'])
                    break
            results[f'{phase_name}_max_passed_vu'] = max(best, results.get(f'{phase_name}_max_passed_vu', 0))
            run.save()

        async def spikes(pid, name):
            peak = results.get('mixed_max_passed_vu', 0)
            if peak < 5:
                run.log_event('skip', phase=name, reason='no mixed stage passed with >= 5 VU')
                return
            r = await run_stage(run, name, f'{name}-5to{peak}vu', 'focus', focus_cfg(pid), STAGE_SECONDS, spike(5, peak))
            run.clear_performance_abort(r['name'])
            await recover(run, 60)

        async def sustained():
            vu = results.get('mixed_max_passed_vu', 0)
            if vu < 1:
                run.log_event('skip', phase='sustained', reason='no mixed stage passed')
                return
            cfg = sustained_cfg(run, vu)
            run.log_event('sustained_pacing', **cfg['pacing'])
            await run_stage(run, 'sustained', f'sustained-{vu}vu-30min', 'mixed', cfg, 30 * 60, ramp_in(vu))
            await recover(run, 60)

        async def stress():
            sp, mix = run.stress, run.stress_mix
            if mix == 'blend':
                scenario, cfg = 'blend', {'blend': [['read', READ_CFG], ['mixed', MIXED_CFG]]}
            else:
                scenario, cfg = mix, dict(READ_CFG if mix == 'read' else MIXED_CFG)
            cfg['profile'] = sp
            dur = sp['up'] + sp['hold'] + sp['down']
            r = await run_stage(run, 'stress', f"stress-{mix}-1to{sp['peak']}vu", scenario, cfg, dur,
                                stress_profile(**sp))
            results['stress_passed'] = r['passed']
            run.clear_performance_abort(r['name'])
            await recover(run, 60)

        async def consist():
            await consistency(run)
            await recover(run, 20)

        await phase('precheck', precheck)
        await phase('read', lambda: ramp('read', 'read', READ_CFG))
        await phase('mixed', lambda: ramp('mixed', 'mixed', MIXED_CFG))
        await phase('spike_city', lambda: spikes('city', 'spike_city'))
        await phase('spike_baseball', lambda: spikes('baseball', 'spike_baseball'))
        await phase('consistency', consist)
        await phase('sustained', sustained)
        await phase('stress', stress)
    finally:
        mon_stop.set()
        await mon_task
        for fh in (run.csv_file, run.timeline, run.events_log, run.res_log, run.prom_log):
            fh.flush()
        run.save()
        run.log_event('run_end', stop_reason=run.stop_reason, budget=run.budget.snapshot(),
                      results=run.state.get('results'))


# ---------------------------------------------------------------------------------------------
def cmd_init(args):
    d = infra.run_dir(args.run_id)
    path = d / 'state.json'
    if path.exists():
        print(f'{path} exists: resume with the same run id instead of re-initialising', file=sys.stderr)
        return 1
    if args.reuse_accounts_from:
        return init_reused(args, d, path)
    profiles = json.loads(infra.PROFILES.read_text(encoding='utf-8'))
    users = profiles['users'][FIRST_NEW - 1:LAST_NEW]
    assert len(users) == LAST_NEW - FIRST_NEW + 1 and users[0]['email'] == f'persona{FIRST_NEW:04d}@example.com'
    state = {
        'run_id': args.run_id, 'target': BASE_URL, 'created_kst': now_kst(),
        'profiles_sha256': infra_sha(infra.PROFILES), 'personas_used': f'{FIRST_NEW}-{LAST_NEW}',
        'caps': {'total': TOTAL_CAP, 'mongo': MONGO_CAP, 'phase_limits': PHASE_LIMITS},
        'password': secrets.token_urlsafe(24),
        'accounts': {u['id']: {'email': u['email'].replace('@', '+synthetic@'), 'user_id': None,
                               'created_by_run': False, 'anonymous_id': str(uuid.uuid4())} for u in users},
        'budget': Budget(TOTAL_CAP, MONGO_CAP).snapshot(),
    }
    infra.save_json(path, state)
    print(json.dumps({'run_dir': str(d), 'accounts': len(users)}))
    return 0


def init_reused(args, d, path):
    """New run on the accounts of an earlier run: no sign-up. Rows those users already own are a baseline."""
    src = json.loads((infra.ARTIFACTS / args.reuse_accounts_from / 'state.json').read_text(encoding='utf-8'))
    accounts = {pid: {'email': a['email'], 'user_id': a['user_id'], 'created_by_run': False,
                      'anonymous_id': str(uuid.uuid4())} for pid, a in src['accounts'].items()}
    if any(not a['user_id'] for a in accounts.values()):
        print('source run has accounts without user_id', file=sys.stderr)
        return 1
    ids = [a['user_id'] for a in accounts.values()]
    counter = infra.Counter(infra.load_env(), src.get('mongo_collection') or 'events')
    baseline = counter.maria(ids)
    if baseline['users'] != len(ids):
        print(f"only {baseline['users']}/{len(ids)} source accounts exist in DB", file=sys.stderr)
        return 1
    from sqlalchemy import text, bindparam
    with counter.engine.connect() as c:
        res_ids = [r[0] for r in c.execute(text('select id from reservations where user_id in :ids')
                                           .bindparams(bindparam('ids', expanding=True)), {'ids': ids})]
    infra.save_json(d / 'baseline_reservations.json', res_ids)
    state = {
        'run_id': args.run_id, 'target': BASE_URL, 'created_kst': now_kst(),
        'profiles_sha256': infra_sha(infra.PROFILES), 'personas_used': src.get('personas_used'),
        'reused_from': args.reuse_accounts_from, 'maria_baseline': baseline,
        'caps': {'total': TOTAL_CAP, 'mongo': MONGO_CAP, 'phase_limits': PHASE_LIMITS},
        'password': src['password'], 'accounts': accounts,
        'budget': Budget(TOTAL_CAP, MONGO_CAP).snapshot(),
    }
    infra.save_json(path, state)
    print(json.dumps({'run_dir': str(d), 'accounts': len(accounts), 'reused_from': args.reuse_accounts_from,
                      'maria_baseline': baseline, 'baseline_reservations': len(res_ids)}))
    return 0


def infra_sha(path):
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def accounts_async(run: Run):
    """Sign up only the accounts that do not exist yet; existing emails are never re-registered."""
    from sqlalchemy import text, bindparam
    run.phase, run.stage = 'accounts', 'accounts'
    emails = [a.email for a in run.accounts]
    with run.counter.engine.connect() as conn:
        existing = dict(conn.execute(text('select email, id from users where email in :e')
                                     .bindparams(bindparam('e', expanding=True)), {'e': emails}).all())
    mapping = run.state['accounts']
    by_email = {a['email']: pid for pid, a in mapping.items()}
    created = skipped = 0
    async with new_client() as c:
        for acc in run.accounts:
            pid = by_email[acc.email]
            if acc.email in existing:
                if not mapping[pid]['user_id'] or mapping[pid]['user_id'] != existing[acc.email]:
                    print(f'account {acc.email} exists but is not mapped to this run; refusing', file=sys.stderr)
                    return 1
                skipped += 1
                continue
            body = {'name': acc.persona['name'], 'email': acc.email, 'password': run.state['password'],
                    'password_confirm': run.state['password'], 'mbti': acc.persona['mbti'], 'consent': True}
            r, ok = await run.call(c, 0, 'signup', 'POST', '/auth/signup', body=body, cost=(1, 0), expected=(201,),
                                   check=lambda r: r.json()['user']['email'] == acc.email, stored=lambda r: (1, 0),
                                   normal=False)
            if not ok:
                print(f'signup failed for {acc.email}: {r.status_code if r is not None else "no response"}',
                      file=sys.stderr)
                run.save()
                return 1
            u = r.json()['user']
            mapping[pid].update(user_id=u['id'], created_by_run=True)
            acc.user_id = u['id']
            created += 1
            run.save()
            await asyncio.sleep(0.2)
    tot = run.counter.totals(run.run_id, run.user_ids())
    run.budget.reconcile_quiet(tot['total'], tot['mongo'])
    run.save()
    run.log_event('accounts_done', created=created, already_present=skipped, db=tot)
    return 0


def lock(run_id):
    path = infra.ARTIFACTS / 'loadtest.lock'
    if path.exists():
        other = json.loads(path.read_text(encoding='utf-8'))
        if psutil.pid_exists(other['pid']):
            raise SystemExit(f'another load test is running: {other}')
    infra.save_json(path, {'pid': os.getpid(), 'run_id': run_id, 'started_kst': now_kst()})
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('command', choices=['init', 'accounts', 'run'])
    ap.add_argument('--run-id', required=True)
    ap.add_argument('--phases', default='precheck,read,mixed,spike_city,spike_baseball,consistency,sustained')
    ap.add_argument('--read-vus', help='override read ramp, e.g. 100 (re-run one step)')
    ap.add_argument('--mixed-vus', help='override mixed ramp')
    ap.add_argument('--redo', default='', help='phases to run again although marked done')
    ap.add_argument('--reuse-accounts-from', help='init: reuse the accounts of this earlier run (no sign-up)')
    ap.add_argument('--stress', help='stress curve peak,up_s,hold_s,down_s (default 200,900,180,120)')
    ap.add_argument('--stress-mix', default='blend', choices=['blend', 'mixed', 'read'])
    args = ap.parse_args()
    if args.command == 'init':
        return cmd_init(args)
    lk = lock(args.run_id)
    try:
        run = Run(args.run_id)
        if args.command == 'accounts':
            return asyncio.run(accounts_async(run))
        if any(not a.user_id for a in run.accounts):
            print('run `accounts` first', file=sys.stderr)
            return 1
        run.ramps = {k: [int(x) for x in v.split(',')] for k, v in
                     (('read', args.read_vus), ('mixed', args.mixed_vus)) if v}
        if args.stress:
            run.stress = dict(zip(('peak', 'up', 'hold', 'down'), (int(x) for x in args.stress.split(','))))
        run.stress_mix = args.stress_mix
        redo = [x for x in args.redo.split(',') if x]
        if redo:
            run.state['phases_done'] = [x for x in run.state.get('phases_done', []) if x not in redo]
            run.log_event('redo', phases=redo, ramps=run.ramps)
        asyncio.run(main_run(run, args.phases.split(',')))
        return 0 if not run.stop_reason else 2
    finally:
        lk.unlink(missing_ok=True)


if __name__ == '__main__':
    raise SystemExit(main())
