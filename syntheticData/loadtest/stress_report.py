"""Knee analysis of a stress stage (VU rising over time): at which VU did each criterion break first.

    syntheticData/loadtest/.venv/Scripts/python.exe syntheticData/loadtest/stress_report.py --run-id <id>

Reads requests.csv, timeline.jsonl, prom.jsonl, progress.jsonl of the run and writes stress_report.md.
Windows are 30 s; a window is judged only with >= 20 requests in the group (same rule as the plan).
"""
import argparse
import bisect
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
WIN = 30
WRITE = {'reservation_create', 'reservation_complete', 'tracking', 'event_post'}
READ_OTHER = {'ranking', 'detail', 'search', 'category', 'reservations_list', 'payments_list'}
NA = '-'


def pct(v, q):
    if not v:
        return None
    s = sorted(v)
    return s[max(0, math.ceil(q * len(s)) - 1)]


def f0(v):
    return NA if v is None else f'{v:,.0f}'


def kst(ts, fmt='%H:%M:%S'):
    return datetime.fromtimestamp(ts, KST).strftime(fmt)


def jsonl(path):
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run-id', required=True)
    ap.add_argument('--stage-prefix', default='stress')
    args = ap.parse_args()
    d = infra.ARTIFACTS / args.run_id

    rows = []
    with open(d / 'requests.csv', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r['stage'].startswith(args.stage_prefix) and r['api'] != 'login':
                rows.append((float(r['ts']), r['api'], int(r['status']), float(r['latency_ms']), r['ok'] == '1',
                             r['error']))
    if not rows:
        print('no stress rows')
        return 1
    tl = [x for x in jsonl(d / 'timeline.jsonl') if x['stage'].startswith(args.stage_prefix)]
    prom = [x for x in jsonl(d / 'prom.jsonl') if str(x.get('stage', '')).startswith(args.stage_prefix)]
    prog = jsonl(d / 'progress.jsonl')
    t0 = min(x['ts'] for x in tl) if tl else rows[0][0]

    win = defaultdict(lambda: {'list': [], 'read': [], 'write': [], 'all': [], 'fail': 0, 'n': 0,
                               'status': defaultdict(int)})
    for ts, api, st, lat, ok, err in rows:
        w = win[int((ts - t0) // WIN)]
        w['n'] += 1
        w['all'].append(lat)
        w['status'][str(st) if st else (err.split(':')[0] or '0')] += 1
        if not ok:
            w['fail'] += 1
        if api == 'list':
            w['list'].append(lat)
        elif api in WRITE:
            w['write'].append(lat)
        elif api in READ_OTHER:
            w['read'].append(lat)
    tlw = defaultdict(list)
    for x in tl:
        tlw[int((x['ts'] - t0) // WIN)].append(x)
    prom_ts = [x['ts'] for x in prom]

    def prom_at(ts):
        """Last Prometheus sample taken inside the window end (rate[1m] => lags ~30 s)."""
        i = bisect.bisect_right(prom_ts, ts) - 1
        return prom[i] if i >= 0 else {}

    def num(sample, name, host):
        v = sample.get(name, {}).get(host) if isinstance(sample.get(name), dict) else None
        return v if isinstance(v, (int, float)) else None

    table, crossings = [], {}
    crit = [('list_p95_500', '목록 p95 > 500ms'), ('read_p95_500', '목록 외 조회 p95 > 500ms'),
            ('write_p95_1000', '쓰기 p95 > 1,000ms'), ('fail_1pct', '실패율 ≥ 1%'),
            ('all_p95_3000', '전체 p95 > 3,000ms'), ('fail_5pct', '실패율 > 5%')]
    best_rps = (0, None)
    for k in sorted(set(win) | set(tlw)):
        w, t = win[k], tlw.get(k, [])
        start = t0 + k * WIN
        vu = max((x['target_vu'] for x in t), default=None)
        act = max((x['active_vu'] for x in t), default=None)
        infl = max((x['inflight_http'] for x in t), default=None)
        gcpu = max((x['gen_proc_cpu_pct'] for x in t), default=None)
        rps = w['n'] / WIN
        lp, rp, wp, ap_ = pct(w['list'], .95), pct(w['read'], .95), pct(w['write'], .95), pct(w['all'], .95)
        fr = w['fail'] / w['n'] if w['n'] else None
        s = prom_at(start + WIN)
        row = {'k': k, 'start': start, 'vu': vu, 'active': act, 'inflight': infl, 'rps': rps, 'n': w['n'],
               'list_p95': lp, 'read_p95': rp, 'write_p95': wp, 'all_p95': ap_, 'all_p50': pct(w['all'], .5),
               'fail': fr, 'gen_cpu': gcpu, 'status': dict(w['status']),
               'cpu175': num(s, 'cpu_pct', 'fastapi-175'), 'cpu176': num(s, 'cpu_pct', 'fastapi-176'),
               'cpu_db': num(s, 'cpu_pct', 'mariadb-171'), 'cpu_nginx': num(s, 'cpu_pct', 'nginx-177'),
               'cpu_ha': num(s, 'cpu_pct', 'haproxy-181'), 'db_conn': num(s, 'mysql_threads_connected', 'mariadb-171'),
               'db_run': num(s, 'mysql_threads_running', 'mariadb-171')}
        table.append(row)
        if w['n'] and rps > best_rps[0]:
            best_rps = (rps, row)
        checks = {
            'list_p95_500': len(w['list']) >= 20 and lp > 500,
            'read_p95_500': len(w['read']) >= 20 and rp > 500,
            'write_p95_1000': len(w['write']) >= 20 and wp > 1000,
            'fail_1pct': w['n'] >= 20 and fr >= 0.01,
            'all_p95_3000': w['n'] >= 20 and ap_ > 3000,
            'fail_5pct': w['n'] >= 20 and fr > 0.05,
        }
        for c, hit in checks.items():
            if hit and c not in crossings:
                crossings[c] = row

    out = [f'# 스트레스 단계 분석 — `{args.run_id}`\n']
    aborts = [x for x in prog if x['kind'] in ('abort', 'stage_stop')]
    ends = [x for x in prog if x['kind'] == 'stage_end' and str(x.get('name', '')).startswith(args.stage_prefix)]
    max_vu = max((r['vu'] or 0) for r in table)
    out.append(f'- 단계 시작: {kst(t0)} KST, 마지막 요청: {kst(rows[-1][0])} KST, 요청 {len(rows):,}건')
    out.append(f'- 도달한 최대 목표 VU: **{max_vu}**')
    for a in aborts:
        out.append(f"- 중단: {a['kst']} — {a.get('reason')}")
    for e in ends:
        out.append(f"- 단계 결과: {e.get('reason')}")
    if best_rps[1]:
        r = best_rps[1]
        out.append(f"- 최대 처리량(30초 구간): **{r['rps']:.1f} RPS** @ VU {r['vu']} ({kst(r['start'])})")
    out.append('\n## 기준별 최초 이탈 지점 (30초 구간)\n')
    out.append('| 기준 | 최초 이탈 시각 | 목표 VU | 해당 값 |')
    out.append('| --- | --- | ---: | --- |')
    val = {'list_p95_500': 'list_p95', 'read_p95_500': 'read_p95', 'write_p95_1000': 'write_p95',
           'all_p95_3000': 'all_p95'}
    for c, label in crit:
        r = crossings.get(c)
        if not r:
            out.append(f'| {label} | 이탈 없음 | - | - |')
            continue
        v = f"{r[val[c]]:,.0f} ms" if c in val else f"{r['fail']:.2%}"
        out.append(f"| {label} | {kst(r['start'])} | {r['vu']} | {v} |")

    out.append('\n## 30초 구간 표\n')
    out.append('| 시각 | 목표 VU | 활성 VU | RPS | p50 | p95 전체 | p95 목록 | p95 조회(기타) | p95 쓰기 | 실패율 | 진행 중 HTTP 최대 '
               '| FastAPI 175/176 CPU % | Nginx177 CPU % | HAProxy CPU % | MariaDB CPU % | DB 연결/실행 | 발생기 CPU % |')
    out.append('| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- | ---: |')
    for r in table:
        fr = NA if r['fail'] is None else f"{r['fail']:.2%}"
        out.append(f"| {kst(r['start'])} | {f0(r['vu'])} | {f0(r['active'])} | {r['rps']:.1f} | {f0(r['all_p50'])} "
                   f"| {f0(r['all_p95'])} | {f0(r['list_p95'])} | {f0(r['read_p95'])} | {f0(r['write_p95'])} | {fr} "
                   f"| {f0(r['inflight'])} | {f0(r['cpu175'])} / {f0(r['cpu176'])} | {f0(r['cpu_nginx'])} "
                   f"| {f0(r['cpu_ha'])} | {f0(r['cpu_db'])} | {f0(r['db_conn'])} / {f0(r['db_run'])} | {f0(r['gen_cpu'])} |")
    bad = [r for r in table if r['fail']]
    if bad:
        out.append('\n## 실패가 있던 구간의 상태 코드\n')
        out.append('| 시각 | 목표 VU | 상태 코드(0=응답 없음, timeout/http=클라이언트 오류) |')
        out.append('| --- | ---: | --- |')
        for r in bad:
            out.append(f"| {kst(r['start'])} | {f0(r['vu'])} | {r['status']} |")
    out.append('\n- CPU는 Prometheus `rate[1m]` 평균이고 15초마다 수집했다. 각 30초 구간이 끝날 때 가장 최근 샘플을 썼으므로 '
               '약 30초 늦게 반영된다.')
    out.append('- 발생기 CPU는 부하 발생 프로세스 1개의 CPU 사용률이다(100% = 1코어). 이 값이 100% 가까이면 측정 지연에 발생기 영향이 섞인다.')
    (d / 'stress_report.md').write_text('\n'.join(out) + '\n', encoding='utf-8')
    json.dump({'crossings': {c: {k: r[k] for k in ('start', 'vu', 'rps', 'list_p95', 'read_p95', 'write_p95',
                                                    'all_p95', 'fail')} for c, r in crossings.items()},
               'max_vu': max_vu, 'best_rps': best_rps[0], 'best_rps_vu': best_rps[1]['vu'] if best_rps[1] else None},
              open(d / 'stress_summary.json', 'w', encoding='utf-8'), indent=1, default=str)
    sys.stdout.reconfigure(encoding='utf-8')
    print('\n'.join(out[:20]))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
