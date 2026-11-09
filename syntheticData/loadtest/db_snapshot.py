"""Before/after DB snapshot of the whole service DBs (not only the run's users), read-only.

    $PY syntheticData/loadtest/db_snapshot.py snap --run-id <id> --label before
    $PY syntheticData/loadtest/db_snapshot.py snap --run-id <id> --label after
    $PY syntheticData/loadtest/db_snapshot.py diff --run-id <id>        # writes db_delta.md

MariaDB: exact row count per table, data/index size, global status counters (statements, rows, InnoDB I/O,
locks, connections). MongoDB: document count and size per collection, serverStatus opcounters.
"""
import argparse
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import infra  # noqa: E402

STATUS = ('Uptime', 'Questions', 'Com_select', 'Com_insert', 'Com_update', 'Com_delete', 'Com_commit',
          'Com_rollback', 'Handler_write', 'Handler_update', 'Handler_read_rnd_next', 'Handler_read_key',
          'Innodb_rows_inserted', 'Innodb_rows_updated', 'Innodb_rows_read', 'Innodb_data_written',
          'Innodb_os_log_written', 'Innodb_buffer_pool_read_requests', 'Innodb_buffer_pool_reads',
          'Innodb_buffer_pool_pages_dirty', 'Innodb_buffer_pool_pages_free', 'Innodb_row_lock_waits',
          'Innodb_row_lock_time', 'Innodb_deadlocks', 'Slow_queries', 'Created_tmp_disk_tables',
          'Created_tmp_tables', 'Select_scan', 'Sort_merge_passes', 'Threads_connected', 'Threads_running',
          'Max_used_connections', 'Connections', 'Aborted_connects', 'Aborted_clients', 'Bytes_received',
          'Bytes_sent')
GAUGES = {'Threads_connected', 'Threads_running', 'Max_used_connections', 'Innodb_buffer_pool_pages_dirty',
          'Innodb_buffer_pool_pages_free', 'Uptime'}


def maria_status(conn) -> dict:
    from sqlalchemy import text, bindparam
    rows = conn.execute(text('show global status where Variable_name in :n')
                        .bindparams(bindparam('n', expanding=True)), {'n': list(STATUS)}).all()
    out = {}
    for k, v in rows:
        try:
            out[k] = float(v)
        except ValueError:
            out[k] = v
    return out


def snap(counter) -> dict:
    from sqlalchemy import text
    with counter.engine.connect() as c:
        tables = [r[0] for r in c.execute(text('select table_name from information_schema.tables '
                                               'where table_schema = database() order by table_name'))]
        sizes = {r[0]: {'data': r[1], 'index': r[2]} for r in c.execute(text(
            'select table_name, data_length, index_length from information_schema.tables '
            'where table_schema = database()'))}
        rows = {t: c.execute(text(f'select count(*) from `{t}`')).scalar() for t in tables}
        status = maria_status(c)
    mongo = {}
    for name in counter.mdb.list_collection_names():
        st = counter.mdb.command('collstats', name)
        mongo[name] = {'count': st['count'], 'size': st['size'], 'storage': st.get('storageSize'),
                       'indexes': st.get('totalIndexSize')}
    ss = counter.mongo.admin.command('serverStatus')
    return {'ts': time.time(), 'maria': {'rows': rows, 'sizes': sizes, 'status': status},
            'mongo': {'collections': mongo, 'opcounters': dict(ss['opcounters']),
                      'connections': ss['connections'].get('current')}}


def fmt(v):
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return f'{v:,}' if isinstance(v, (int, float)) else str(v)


def diff(d: Path) -> str:
    a = json.loads((d / 'db_before.json').read_text(encoding='utf-8'))
    b = json.loads((d / 'db_after.json').read_text(encoding='utf-8'))
    secs = b['ts'] - a['ts']
    out = [f'# DB 변화 (스냅샷 간격 {secs:.0f}초)\n', '## MariaDB 테이블\n',
           '| 테이블 | 전 | 후 | 증가 | 데이터+인덱스 전 KB | 후 KB |', '| --- | ---: | ---: | ---: | ---: | ---: |']
    for t in sorted(set(a['maria']['rows']) | set(b['maria']['rows'])):
        ra, rb = a['maria']['rows'].get(t, 0), b['maria']['rows'].get(t, 0)
        sa = sum(a['maria']['sizes'].get(t, {}).values()) / 1024
        sb = sum(b['maria']['sizes'].get(t, {}).values()) / 1024
        out.append(f'| {t} | {ra:,} | {rb:,} | {rb - ra:+,} | {sa:,.0f} | {sb:,.0f} |')
    out += ['\n## MariaDB 서버 상태 (누적 카운터는 증가량과 초당 값, 게이지는 전/후)\n',
            '| 항목 | 전 | 후 | 증가 | 초당 |', '| --- | ---: | ---: | ---: | ---: |']
    sa, sb = a['maria']['status'], b['maria']['status']
    for k in STATUS:
        if k not in sa or k not in sb:
            continue
        if k in GAUGES:
            out.append(f'| {k} | {fmt(sa[k])} | {fmt(sb[k])} | - | - |')
        else:
            dv = sb[k] - sa[k]
            out.append(f'| {k} | {fmt(sa[k])} | {fmt(sb[k])} | {fmt(dv)} | {dv / secs:,.1f} |')
    if sb.get('Uptime', 0) < sa.get('Uptime', 0):
        out.append('\n**주의: Uptime이 줄었다. 그 사이 MariaDB가 재시작되어 누적 카운터 증가량은 무효다.**')
    out += ['\n## MongoDB\n', '| 컬렉션 | 문서 전 | 후 | 증가 | 크기 전 KB | 후 KB |', '| --- | ---: | ---: | ---: | ---: | ---: |']
    ca, cb = a['mongo']['collections'], b['mongo']['collections']
    for n in sorted(set(ca) | set(cb)):
        x, y = ca.get(n, {}), cb.get(n, {})
        out.append(f"| {n} | {x.get('count', 0):,} | {y.get('count', 0):,} | {y.get('count', 0) - x.get('count', 0):+,} "
                   f"| {x.get('size', 0) / 1024:,.0f} | {y.get('size', 0) / 1024:,.0f} |")
    oa, ob = a['mongo']['opcounters'], b['mongo']['opcounters']
    out.append('\n| opcounter | 증가 | 초당 |')
    out.append('| --- | ---: | ---: |')
    for k in ob:
        out.append(f'| {k} | {ob[k] - oa.get(k, 0):,} | {(ob[k] - oa.get(k, 0)) / secs:,.1f} |')
    out.append(f"\nMongoDB 현재 연결: 전 {a['mongo']['connections']} / 후 {b['mongo']['connections']}")
    return '\n'.join(out) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('command', choices=['snap', 'diff'])
    ap.add_argument('--run-id', required=True)
    ap.add_argument('--label', choices=['before', 'after'])
    args = ap.parse_args()
    d = infra.run_dir(args.run_id)
    sys.stdout.reconfigure(encoding='utf-8')
    if args.command == 'snap':
        state = json.loads((d / 'state.json').read_text(encoding='utf-8')) if (d / 'state.json').exists() else {}
        counter = infra.Counter(infra.load_env(), state.get('mongo_collection') or 'events')
        s = snap(counter)
        infra.save_json(d / f'db_{args.label}.json', s)
        print(json.dumps({'label': args.label, 'rows': s['maria']['rows'],
                          'mongo': {k: v['count'] for k, v in s['mongo']['collections'].items()}}, ensure_ascii=False))
    else:
        md = diff(d)
        (d / 'db_delta.md').write_text(md, encoding='utf-8')
        print(md)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
