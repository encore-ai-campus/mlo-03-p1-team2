"""Durable shared write reservations and measured latency/error gates.

Budget is owned by one process/event loop. Reserve before sending a write;
never refund an uncertain outcome. No credentials are stored here.
"""
import json
import math
import os
import time
import uuid
from collections import defaultdict


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    with temp.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    for attempt in range(8):
        try:
            os.replace(temp, path)
            return
        except PermissionError:
            if attempt == 7:
                raise
            time.sleep(min(.025 * 2**attempt, .5))


class BudgetExceeded(RuntimeError):
    pass


class Budget:
    def __init__(self, path, total_limit=100000, tracking_limit=50000):
        self.path = path
        self.data = (json.loads(path.read_text(encoding='utf-8')) if path.exists() else
                     dict(total_limit=total_limit, tracking_limit=tracking_limit,
                          committed=[0, 0], pending={}))
        if (self.data['total_limit'], self.data['tracking_limit']) != (total_limit, tracking_limit):
            raise ValueError('Budget limits differ from the persisted run')
        save(self.path, self.data)

    def used(self):
        return tuple(self.data['committed'][i] + sum(v[i] for v in self.data['pending'].values())
                     for i in range(2))

    def reserve(self, total, tracking=0):
        if not (type(total) is int and type(tracking) is int and 0 <= tracking <= total):
            raise ValueError('Invalid write cost')
        used, logs = self.used()
        if used + total > self.data['total_limit'] or logs + tracking > self.data['tracking_limit']:
            raise BudgetExceeded('Shared database write budget reached')
        ticket = str(uuid.uuid4())
        self.data['pending'][ticket] = [total, tracking]
        try:
            save(self.path, self.data)
        except OSError:
            # Admission failed before any HTTP request could be sent.
            del self.data['pending'][ticket]
            raise
        return ticket

    def settle(self, ticket, total, tracking=0):
        reserved = self.data['pending'][ticket]
        if not (0 <= tracking <= total <= reserved[0] and tracking <= reserved[1]):
            raise ValueError('Actual cost exceeds the write reservation')
        self.data['committed'][0] += total
        self.data['committed'][1] += tracking
        del self.data['pending'][ticket]
        save(self.path, self.data)


def percentile(values, p):
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[max(0, math.ceil(len(ordered) * p) - 1)], 2)


def summarize(rows):
    if not rows:
        return dict(requests=0, errors=0, error_rate=None, p95=None, p99=None)
    return dict(requests=len(rows), errors=sum(not r['ok'] for r in rows),
                error_rate=round(100 * sum(not r['ok'] for r in rows) / len(rows), 3),
                p95=percentile([r['ms'] for r in rows], .95),
                p99=percentile([r['ms'] for r in rows], .99))


def stage_limit(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row['api']].append(row)
    apis = {name: dict(summarize(items), kind=items[0]['kind']) for name, items in groups.items()}
    passed = bool(rows) and all(v['error_rate'] < 1 and v['p95'] <= (1000 if v['kind'] == 'write' else 500)
                                for v in apis.values())
    return dict(passed=passed, apis=apis, **summarize(rows))


class Metrics:
    def __init__(self):
        self.rows = []

    def add(self, at, api, ms, ok, kind):
        row = dict(at=at, api=api, ms=round(ms, 2), ok=bool(ok), kind=kind)
        self.rows.append(row)
        return row

    def stop_reason(self, now):
        if not self.rows:
            return None
        recent30 = [r for r in self.rows if now - 30 <= r['at'] <= now]
        if now - self.rows[0]['at'] >= 30 and recent30 and summarize(recent30)['error_rate'] > 5:
            return 'rolling_30s_error_rate_over_5_percent'
        recent60 = [r for r in self.rows if now - 60 <= r['at'] <= now]
        if now - self.rows[0]['at'] >= 60 and recent60 and summarize(recent60)['p95'] > 3000:
            return 'rolling_60s_latency_over_3000ms'
        return None
