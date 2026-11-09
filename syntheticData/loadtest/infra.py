"""Paths, credentials, DB record counting and Prometheus sampling for the load test.

Credentials are read from backend/.env (local, git-ignored) or the same variable names in the
environment: DATABASE_URL, MONGODB_URL, MONGODB_DB. They are never printed or written to artifacts.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import time

import httpx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ARTIFACTS = ROOT / 'syntheticData' / 'playwright' / 'artifacts'   # git-ignored
PROFILES = ROOT / 'syntheticData' / 'personas.json'
PROM_URL = os.environ.get('LOADTEST_PROMETHEUS_URL', 'http://192.168.0.187:9090')

# Hosts of the deployed path, from docs/networkInfo.md (verified against Prometheus targets).
HOSTS = {
    '192.168.0.181:9100': 'haproxy-181', '192.168.0.177:9100': 'nginx-177', '192.168.0.178:9100': 'nginx-178',
    '192.168.0.175:9100': 'fastapi-175', '192.168.0.176:9100': 'fastapi-176',
    '192.168.0.171:9100': 'mariadb-171', '192.168.0.174:9100': 'mongodb-174',
}
APP_HOSTS = ('fastapi-175', 'fastapi-176', 'nginx-177', 'nginx-178', 'haproxy-181')


def load_env() -> dict:
    env = {}
    path = ROOT / 'backend' / '.env'
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    for k in ('DATABASE_URL', 'MONGODB_URL', 'MONGODB_DB'):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


def run_dir(run_id: str) -> Path:
    d = ARTIFACTS / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_json(path: Path, data) -> None:
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    os.replace(tmp, path)


# ---- DB counting ---------------------------------------------------------------------------
MARIA_TABLES = ('users', 'favorites', 'reservations', 'payments', 'status_history', 'events',
                'orders', 'notification_settings')


class Counter:
    """Counts records created by this run: rows owned by the run's new users, Mongo docs by run tag."""

    def __init__(self, env: dict, mongo_collection: str):
        from sqlalchemy import create_engine
        from pymongo import MongoClient
        self.engine = create_engine(env['DATABASE_URL'], pool_pre_ping=True, pool_size=2, max_overflow=0)
        self.mongo = MongoClient(env['MONGODB_URL'], serverSelectionTimeoutMS=5000, tz_aware=True)
        self.mdb = self.mongo[env.get('MONGODB_DB', 'tikit')]
        self.collection_name = mongo_collection
        self.maria_baseline: dict = {}   # rows the (reused) run users owned before this run

    def maria(self, user_ids: list[str]) -> dict:
        from sqlalchemy import text, bindparam
        if not user_ids:
            return {t: 0 for t in MARIA_TABLES}
        out = {}
        with self.engine.connect() as c:
            for t in MARIA_TABLES:
                col = 'id' if t == 'users' else 'user_id'
                if t == 'payments':
                    q = text('select count(*) from payments p join reservations r on r.id=p.reservation_id '
                             'where r.user_id in :ids')
                else:
                    q = text(f'select count(*) from `{t}` where {col} in :ids')
                out[t] = c.execute(q.bindparams(bindparam('ids', expanding=True)), {'ids': user_ids}).scalar()
        return out

    def mongo_count(self, run_id: str, user_ids: list[str] | None = None) -> int:
        q = {'props.loadtest_run_id': run_id}
        if user_ids:
            q['user_id'] = {'$in': user_ids}   # uses the (user_id, occurred_at) index
        return self.mdb[self.collection_name].count_documents(q)

    def find_run_collections(self, run_id: str) -> dict:
        return {name: n for name in self.mdb.list_collection_names()
                if (n := self.mdb[name].count_documents({'props.loadtest_run_id': run_id}))}

    def totals(self, run_id: str, user_ids: list[str]) -> dict:
        m = {t: max(0, n - self.maria_baseline.get(t, 0)) for t, n in self.maria(user_ids).items()}
        mongo = self.mongo_count(run_id, user_ids)
        return {'maria': m, 'maria_total': sum(m.values()), 'mongo': mongo, 'total': sum(m.values()) + mongo}


# ---- Prometheus ----------------------------------------------------------------------------
PROM_QUERIES = {
    'cpu_pct': '100*(1-avg by(instance)(rate(node_cpu_seconds_total{mode="idle"}[1m])))',
    'iowait_pct': '100*avg by(instance)(rate(node_cpu_seconds_total{mode="iowait"}[1m]))',
    'mem_used_pct': '100*(1-node_memory_MemAvailable_bytes/node_memory_MemTotal_bytes)',
    'load1': 'node_load1',
    'net_rx_Bps': 'sum by(instance)(rate(node_network_receive_bytes_total{device!~"lo"}[1m]))',
    'net_tx_Bps': 'sum by(instance)(rate(node_network_transmit_bytes_total{device!~"lo"}[1m]))',
    'disk_avail_bytes': 'node_filesystem_avail_bytes{mountpoint="/"}',
    'disk_io_util': 'max by(instance)(rate(node_disk_io_time_seconds_total[1m]))',
    'boot_time': 'node_boot_time_seconds',
    'up': 'up{job="node"}',
    'tcp_estab': 'node_netstat_Tcp_CurrEstab',
    'mysql_threads_connected': 'mysql_global_status_threads_connected',
    'mysql_threads_running': 'mysql_global_status_threads_running',
    'mysql_max_connections': 'mysql_global_variables_max_connections',
    'mysql_max_used_connections': 'mysql_global_status_max_used_connections',
    'mysql_questions_ps': 'rate(mysql_global_status_questions[1m])',
    'mysql_row_lock_waits_ps': 'rate(mysql_global_status_innodb_row_lock_waits[1m])',
    'mysql_row_lock_current_waits': 'mysql_global_status_innodb_row_lock_current_waits',
    'mysql_slow_queries_ps': 'rate(mysql_global_status_slow_queries[1m])',
    'mysql_deadlocks': 'mysql_global_status_innodb_deadlocks',
    'mysql_aborted_connects': 'mysql_global_status_aborted_connects',
    'mongo_connections': 'mongodb_ss_connections{conn_type="current"}',
    'mongo_write_latency_us': 'rate(mongodb_ss_opLatencies_latency{op_type="writes"}[1m])'
                              '/clamp_min(rate(mongodb_ss_opLatencies_ops{op_type="writes"}[1m]),1e-9)',
    'mongo_write_ops_ps': 'rate(mongodb_ss_opLatencies_ops{op_type="writes"}[1m])',
}


def _label(metric: dict) -> str:
    inst = metric.get('instance', '')
    return HOSTS.get(inst, inst)


def prom_sample(client: httpx.Client) -> dict:
    out = {'ts': time.time()}
    for name, q in PROM_QUERIES.items():
        try:
            r = client.get(f'{PROM_URL}/api/v1/query', params={'query': q}, timeout=3)
            vals = {}
            for row in r.json()['data']['result']:
                lab = _label(row['metric'])
                if name.startswith(('mongo_', 'mysql_')):
                    lab = 'mariadb-171' if name.startswith('mysql_') else 'mongodb-174'
                if name == 'up' or lab in HOSTS.values():
                    vals[lab] = float(row['value'][1])
            out[name] = vals
        except Exception as exc:  # monitoring must never break the run
            out[name] = {'error': type(exc).__name__}
    return out
