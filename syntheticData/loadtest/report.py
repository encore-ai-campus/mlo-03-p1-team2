"""Build markdown tables from a run's raw artifacts (requests.csv, timeline.jsonl, prom.jsonl, state.json).

    syntheticData/loadtest/.venv/Scripts/python.exe syntheticData/loadtest/report.py --run-id <id>

Writes report_tables.md into the run directory. Only measured values are printed; missing ones are '미측정'.
"""
import argparse
import csv
from collections import defaultdict
from datetime import datetime, timezone, timedelta
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import infra  # noqa: E402

KST = timezone(timedelta(hours=9))
NA = '미측정'


def pct(values, q):
    if not values:
        return None
    s = sorted(values)
    return s[max(0, math.ceil(q * len(s)) - 1)]


def fmt(v, nd=0):
    if v is None:
        return NA
    return f'{v:,.{nd}f}'


def kst(ts, f='%H:%M'):
    return datetime.fromtimestamp(ts, KST).strftime(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run-id', required=True)
    args = ap.parse_args()
    d = infra.ARTIFACTS / args.run_id
    state = json.loads((d / 'state.json').read_text(encoding='utf-8'))
    out = []

    # ---- per-minute table ---------------------------------------------------------------------
    minute = defaultdict(lambda: {'req': 0, 'fail': 0, 'lat': [], 'stage': set(), 'reqs_normal': 0})
    with open(d / 'requests.csv', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            ts = float(row['ts'])
            m = int(ts // 60) * 60
            b = minute[m]
            b['req'] += 1
            b['stage'].add(row['stage'])
            if row['class'] != 'expected_conflict' and row['api'] not in ('login', 'signup') \
                    and not row['api'].startswith(('dup_', 'race_', 'track_')):
                b['reqs_normal'] += 1
                b['lat'].append(float(row['latency_ms']))
                if row['ok'] == '0':
                    b['fail'] += 1
    tl = defaultdict(lambda: {'target': [], 'active': [], 'visits': [], 'gen_cpu': [], 'tx': [], 'rx': []})
    with open(d / 'timeline.jsonl', encoding='utf-8') as f:
        for line in f:
            r = json.loads(line)
            m = int(r['ts'] // 60) * 60
            t = tl[m]
            t['target'].append(r['target_vu'])
            t['active'].append(r['active_vu'])
            t['visits'].append((r['stage'], r['visits_done']))
            t['gen_cpu'].append(r['gen_cpu_pct'])
            t['tx'].append(r['gen_tx_Bps'])
            t['rx'].append(r['gen_rx_Bps'])
    # visits completed per minute = increase of the per-stage counter
    last_visits = {}
    out.append('### 분 단위 접속·처리 표 (KST)\n')
    out.append('| 시각 | 단계 | 목표 VU (최소/평균/최대) | 실제 활성 VU (최소/평균/최대) | 완료 방문 | 요청 수 | RPS | p95 ms | 실패율 | 발생기 CPU % 최대 |')
    out.append('| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |')
    for m in sorted(set(minute) | set(tl)):
        b, t = minute.get(m), tl.get(m)
        stages = sorted(s for s in (b['stage'] if b else set()) if s and s != 'recovery') or \
            sorted({s for s, _ in (t['visits'] if t else [])} - {'recovery', ''})
        done = 0
        if t:
            for st, v in t['visits']:
                prev = last_visits.get(st, 0)
                if v >= prev:
                    done += v - prev
                last_visits[st] = v
        tgt = f"{min(t['target'])}/{sum(t['target'])/len(t['target']):.1f}/{max(t['target'])}" if t else NA
        act = f"{min(t['active'])}/{sum(t['active'])/len(t['active']):.1f}/{max(t['active'])}" if t else NA
        req = b['req'] if b else 0
        p95 = pct(b['lat'], .95) if b else None
        fr = (b['fail'] / b['reqs_normal']) if b and b['reqs_normal'] else None
        cpu = max(t['gen_cpu']) if t else None
        out.append(f"| {kst(m)} | {', '.join(stages) or '-'} | {tgt} | {act} | {done if t else NA} | {req:,} | "
                   f"{req/60:.1f} | {fmt(p95)} | {('%.2f%%' % (fr*100)) if fr is not None else '-'} | {fmt(cpu)} |")

    # ---- spike fine-grained (5 s buckets) -----------------------------------------------------
    for st in state.get('stages', []):
        if st['scenario'] != 'focus':
            continue
        out.append(f"\n### {st['name']} 5초 간격 (KST)\n")
        out.append('| 시각 | 목표 VU | 실제 활성 VU 최대 | 진행 중 HTTP 최대 |')
        out.append('| --- | ---: | ---: | ---: |')
        buckets = defaultdict(list)
        with open(d / 'timeline.jsonl', encoding='utf-8') as f:
            for line in f:
                r = json.loads(line)
                if r['stage'] == st['name']:
                    buckets[int(r['ts'] // 5) * 5].append(r)
        peak_ts = None
        for k in sorted(buckets):
            rs = buckets[k]
            amax = max(r['active_vu'] for r in rs)
            if peak_ts is None and amax >= st['max_vu']:
                peak_ts = k
            out.append(f"| {kst(k, '%H:%M:%S')} | {max(r['target_vu'] for r in rs)} | {amax} | "
                       f"{max(r['inflight_http'] for r in rs)} |")
        out.append(f"\n최대 VU({st['max_vu']}) 실제 도달 시각: {kst(peak_ts, '%H:%M:%S') if peak_ts else '도달 기록 없음'}")

    # ---- per-stage API tables -----------------------------------------------------------------
    out.append('\n### 단계별 API 지표\n')
    for st in state.get('stages', []):
        out.append(f"\n#### {st['name']} ({st['start_kst']}–{st['end_kst']}, 최대 {st['max_vu']} VU) — "
                   f"{'통과' if st['passed'] else '미통과'}: {st['reason']}\n")
        out.append(f"요청 {st['requests']:,}건, 전체 RPS {st['rps']:.1f}, 정상 요청 실패율 {st['fail_rate']:.2%}, "
                   f"방문 {st['visits']:,}회 {st['visit_kinds']}, 신규 레코드 {st['records_committed']}\n")
        out.append('| API | 요청 | 성공 | 실패 | 예상 충돌 | RPS | p50 | p95 | p99 | 최대 | p95 기준 | 상태 코드 |')
        out.append('| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |')
        for api, a in st['apis'].items():
            out.append(f"| {api} | {a['requests']:,} | {a['requests']-a['fail']-a['expected_conflicts']:,} | "
                       f"{a['fail']:,} | {a['expected_conflicts']} | {a['rps']:.2f} | {a['p50']:.0f} | {a['p95']:.0f} | "
                       f"{a['p99']:.0f} | {a['max']:.0f} | {a['p95_limit']} | {a['statuses']} |")

    # ---- server metrics per stage -------------------------------------------------------------
    prom = [json.loads(line) for line in open(d / 'prom.jsonl', encoding='utf-8')]
    out.append('\n### 단계별 서버 지표 최댓값 (Prometheus 15초 샘플)\n')
    hosts = ['haproxy-181', 'nginx-177', 'nginx-178', 'fastapi-175', 'fastapi-176', 'mariadb-171', 'mongodb-174']
    out.append('| 단계 | ' + ' | '.join(f'{h} CPU%' for h in hosts) +
               ' | MariaDB 연결 | 실행 스레드 | 행 잠금 대기/s | Mongo 쓰기 지연 µs | Mongo 연결 |')
    out.append('| --- |' + ' ---: |' * (len(hosts) + 5))
    for st in state.get('stages', []):
        ss = [s for s in prom if st['start'] <= s['ts'] <= st['end'] + 5]
        if not ss:
            continue

        def mx(name, host):
            vals = [s.get(name, {}).get(host) for s in ss]
            vals = [v for v in vals if isinstance(v, (int, float))]
            return max(vals) if vals else None
        cells = [fmt(mx('cpu_pct', h)) for h in hosts]
        cells += [fmt(mx('mysql_threads_connected', 'mariadb-171')), fmt(mx('mysql_threads_running', 'mariadb-171')),
                  fmt(mx('mysql_row_lock_waits_ps', 'mariadb-171'), 2), fmt(mx('mongo_write_latency_us', 'mongodb-174')),
                  fmt(mx('mongo_connections', 'mongodb-174'))]
        out.append(f"| {st['name']} | " + ' | '.join(cells) + ' |')
    out.append('\n### 단계별 메모리·네트워크 최댓값\n')
    out.append('| 단계 | ' + ' | '.join(f'{h} MEM%' for h in hosts) + ' | haproxy-181 송신 MB/s | 발생기 송신/수신 MB/s 최대 |')
    out.append('| --- |' + ' ---: |' * (len(hosts) + 2))
    tl_rows = [json.loads(line) for line in open(d / 'timeline.jsonl', encoding='utf-8')]
    for st in state.get('stages', []):
        ss = [s for s in prom if st['start'] <= s['ts'] <= st['end'] + 5]
        gs = [r for r in tl_rows if r['stage'] == st['name']]
        if not ss:
            continue

        def mx(name, host):
            vals = [s.get(name, {}).get(host) for s in ss]
            vals = [v for v in vals if isinstance(v, (int, float))]
            return max(vals) if vals else None
        tx = mx('net_tx_Bps', 'haproxy-181')
        gen = f"{max(r['gen_tx_Bps'] for r in gs)/1e6:.2f}/{max(r['gen_rx_Bps'] for r in gs)/1e6:.2f}" if gs else NA
        out.append(f"| {st['name']} | " + ' | '.join(fmt(mx('mem_used_pct', h)) for h in hosts) +
                   f" | {fmt(tx/1e6 if tx else None, 2)} | {gen} |")
    (d / 'report_tables.md').write_text('\n'.join(out) + '\n', encoding='utf-8')
    print(f'wrote {d / "report_tables.md"} ({len(out)} lines)')


if __name__ == '__main__':
    raise SystemExit(main())
