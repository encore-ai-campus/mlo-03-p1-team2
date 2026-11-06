"""Prepare by default. Production writes require the explicit --execute flag.

From the repository root: python -m syntheticData.playwright.load_test --run-id ID
Artifacts contain credentials: never commit or print them.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import random
import re
import secrets
import ssl
import time
import uuid
from datetime import datetime, timezone, timedelta

import httpx

from .load_client import Api, ApiFailure
from .load_control import Budget, BudgetExceeded, Metrics, save, stage_limit, summarize
from .load_database import Evidence
from .load_monitoring import collect, reason as monitoring_reason
from .load_preparation import digest, expand_file
from syntheticData.playwright.scenarios import save_profiles_snapshot

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / 'syntheticData/playwright/artifacts'
PROFILES = ROOT / 'syntheticData/personas.json'
BASE = 'https://www.yaaho.kro.kr'
KST = timezone(timedelta(hours=9))
MONITOR_TIMEOUT = 10


def now():
    return datetime.now(KST).isoformat(timespec='seconds')


def tls_context():
    context = ssl.create_default_context()
    if hasattr(ssl, 'enum_certificates'):
        for store in ('ROOT', 'CA'):
            for data, encoding, trust in ssl.enum_certificates(store):
                if encoding == 'x509_asn':
                    try:
                        context.load_verify_locations(cadata=ssl.DER_cert_to_PEM_cert(data))
                    except ssl.SSLError:
                        pass
    return context


def email(profile):
    local, domain = profile['email'].split('@')
    return local + '+synthetic@' + domain


def stage_plan(maximum=300):
    stages = [dict(name='smoke', vus=1, seconds=120, mode='mixed'),
              dict(name='browse-baseline', vus=10, seconds=300, mode='browse')]
    stages += [dict(name=f'mixed-{v}', vus=v, seconds=300, mode='mixed')
               for v in (10, 25, 50, 100, 150, 200, 300) if v <= maximum]
    stages += [dict(name='concert-spike', vus=maximum, seconds=300, mode='spike', performance='city'),
               dict(name='baseball-spike', vus=maximum, seconds=300, mode='spike', performance='baseball'),
               dict(name='soak', vus=maximum, seconds=1800, mode='mixed')]
    return stages


def spike_vus(elapsed, peak):
    if elapsed < 90:
        return min(5, peak)
    if elapsed < 110:
        return max(1, round(min(5, peak) + (peak - min(5, peak)) * (elapsed - 90) / 20))
    if elapsed < 150:
        return max(1, round(peak - (peak - min(5, peak)) * (elapsed - 110) / 40))
    return min(5, peak)


def write_report(state, metrics, directory):
    target = ROOT / 'docs/loadTestResult.md'
    rows = metrics.rows
    lines = ['# 부하 테스트 결과', '', f'- 실행 ID: `{state["run_id"]}`',
             f'- 대상: `{BASE}` (실제 서비스)', f'- 상태: {state["phase"]}',
             f'- 기록 시각(KST): {now()}', f'- 시작 시각(KST): {state.get("started_at", "미실행")}',
             f'- 종료/준비 완료 시각(KST): {state.get("finished_at", "진행 중")}',
             f'- 중단 이유: {state.get("stop_reason") or "없음"}', '',
             '## 실행 조건', '',
             '- 페르소나 300명. 동시 접속 1 → 10 → 25 → 50 → 100 → 150 → 200 → 300명.',
             '- 전체 신규 레코드 최소 50,000건·최대 100,000건, 그중 행동 로그 최대 50,000건.',
             '- 기능 확인: Postman CLI. 본 부하: HTTPX 실행기(공유 예산·중단 감시 통합).',
             '- Postman 성능 실행은 로컬 컬렉션 초기화 오류(`error while parsing createbBy`)로 시작하지 못함.',
             '- Grafana 지표 API는 인증 필요. Prometheus 직접 조회로 서버·DB 지표 수집.',
             '- API로 합성 행동 로그를 생성하며 실제 브라우저 방문 데이터와 구분.', '',
             '## 준비 상태', '']
    for note in state.get('preparation_notes', []):
        lines.append('- ' + note)
    lines += ['', '## 단계별 결과', '', '| 단계 | 목표 VU | 실제 소요(초) | 요청 | 오류율(%) | p95(ms) | 통과 |',
              '| --- | ---: | ---: | ---: | ---: | ---: | --- |']
    for stage in state.get('stages', []):
        lines.append(f'| {stage["name"]} | {stage["vus"]} | {stage["elapsed"]:.1f} | '
                     f'{stage["requests"]} | {stage["error_rate"]} | {stage["p95"]} | {stage["passed"]} |')
    if not state.get('stages'):
        lines.append('| 부하 실행 전 | — | — | — | — | — | 미실행 |')
    lines += ['', '## 분 단위 접속 인원과 성능', '',
              '실제 VU는 살아 있는 가상 사용자 작업 수이며 대기 시간을 포함한다. HTTP 동시 처리 수는 별도로 기록한다.', '',
              '| 경과(분) | 목표 VU 범위 | 실제 VU 범위 | 최대 진행 중 HTTP | 완료 방문 | 요청 | RPS | p95(ms) | 오류율(%) |',
              '| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    samples = state.get('samples', [])
    for minute in sorted({int(v['elapsed'] // 60) for v in samples}):
        group = [v for v in samples if int(v['elapsed'] // 60) == minute]
        requests = [r for r in rows if minute * 60 <= r['at'] < (minute + 1) * 60]
        summary = summarize(requests)
        start = minute * 60
        duration = min(60, max(1, max(v['elapsed'] for v in samples) - start))
        goals = [v['target'] for v in group]
        actual = [v['actual'] for v in group]
        visits = sum(v.get('completed_delta', 0) for v in group)
        lines.append(f'| {minute}–{minute+1} | {min(goals)}–{max(goals)} | {min(actual)}–{max(actual)} | '
                     f'{max(v["inflight"] for v in group)} | {visits} | {summary["requests"]} | '
                     f'{summary["requests"]/duration:.2f} | {summary["p95"]} | {summary["error_rate"]} |')
    if not samples:
        lines.append('| 미실행 | — | 미측정 | 미측정 | — | — | — | — | — |')
    lines += ['', '## API별 결과', '', 'RPS는 준비 인증을 포함한 API 측정 구간 전체 시간 기준이다.', '',
              '| API | 요청 | RPS | 오류율(%) | p95(ms) | p99(ms) |', '| --- | ---: | ---: | ---: | ---: | ---: |']
    duration = max((r['at'] for r in rows), default=0)
    for name, data in stage_limit(rows)['apis'].items():
        rps = f'{data["requests"]/duration:.3f}' if duration else '미측정'
        lines.append(f'| {name} | {data["requests"]} | {rps} | {data["error_rate"]} | {data["p95"]} | {data["p99"]} |')
    evidence = state.get('evidence')
    lines += ['', '## 신규 레코드 및 정합성', '']
    if evidence:
        lines += ['| 저장소/테이블 | 이번 실행 신규 건수 |', '| --- | ---: |']
        for table, count in evidence['deltas'].items():
            lines.append(f'| {table} | {count} |')
        lines += [f'| **합계** | **{evidence["total"]}** |', '',
                  f'- 최소 50,000건 충족: {evidence["total"] >= 50000}',
                  f'- 전체 100,000건 상한 준수: {evidence["total"] <= 100000}',
                  f'- 행동 로그 50,000건 상한 준수: {evidence["deltas"]["tracking"] <= 50000}',
                  f'- 성공한 모의 결제(DB 업무 이벤트 기준): {evidence.get("business_events", {}).get("payment_completed", 0)}건',
                  f'- 확인된 예매의 최종 상태별 건수: {evidence.get("reservation_states", {})}',
                  '- 정합성 검사: ' + ('; '.join(evidence['issues']) or '검사 범위 내 오류 없음')]
    else:
        lines.append('준비 단계로 API 쓰기는 실행하지 않음. 부하에 의한 신규 레코드 수와 정합성 결과는 아직 없음.')
    lines += ['', '## 관측 및 한계', '',
              '- 실제 활성 VU는 1초 간격 표본, 서버·DB 지표는 30초 간격으로 원시 파일에 보관.',
              '- 지표를 수집하지 못한 항목은 미측정이며, 계획값으로 대체하지 않음.',
              '- 좌석 재고·홀드 모델이 없어 초과 판매 방지는 검증하지 않음.',
              '- 여러 담당자의 중복 실행과 실행 중 프로필 변경은 지원하지 않음.',
              '- 실행 중단 후 자동 거래 재생은 지원하지 않음. 불명확한 쓰기를 DB와 대조한 후 별도 재개 절차 필요.',
              f'- 원시 결과 위치: `{directory.relative_to(ROOT).as_posix()}/` (Git 제외; 자격 증명 포함 가능).', '']
    content = '\n'.join(lines)
    if target.exists() and not (directory / 'previous-report.md').exists() and state.get('report_initialized') is not True:
        (directory / 'previous-report.md').write_bytes(target.read_bytes())
    target.write_text(content, encoding='utf-8')
    state['report_initialized'] = True


class Campaign:
    def __init__(self, run_id):
        self.directory = ARTIFACTS / run_id
        if self.directory.exists() and any(self.directory.iterdir()) and not (self.directory / 'load-state.json').exists():
            raise ValueError('Run ID belongs to existing artifacts; choose a new load-test run ID')
        if (self.directory / 'state.json').exists():
            raise ValueError('Run ID belongs to a historical browser campaign')
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / 'load-state.json'
        self.state = (json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else
                      dict(run_id=run_id, phase='준비 중', stages=[], samples=[],
                           reservations=[], credentials={}, preparation_notes=[]))
        self.metrics = Metrics()
        self.budget = Budget(self.directory / 'budget.json')
        self.stop = asyncio.Event()
        self.workers = self.visits = 0
        self.active = set()
        self.evidence = None

    def persist(self):
        save(self.path, self.state)

    def halt(self, message):
        if not self.stop.is_set():
            self.state['stop_reason'] = message
            self.stop.set()

    async def prepare(self, client):
        if self.state.get('profile_sha256') and digest(PROFILES) != self.state['profile_sha256']:
            raise ValueError('Shared profiles changed after preparation; refusing to replace the saved run input')
        profiles = expand_file(PROFILES, ARTIFACTS)['users']
        save_profiles_snapshot(self.directory, PROFILES)
        self.state['profile_sha256'] = digest(PROFILES)
        self.profiles = profiles
        self.evidence = Evidence([email(p) for p in profiles], self.state['run_id'])
        members = await asyncio.to_thread(self.evidence.members)
        source = Path(os.environ.get('TIKIT_ACCOUNT_STATE', str(ARTIFACTS / 'persona-20261106/state.json')))
        old = json.loads(source.read_text(encoding='utf-8')) if source.exists() else None
        old_accounts = {a['email']: a for a in old.get('accounts', {}).values()} if old else {}
        if old and old.get('account_map'):
            old_accounts.update({address: {'user_id': identity} for address, identity in old['account_map'].items()})
        for profile in profiles:
            address = email(profile)
            if address in self.state['credentials']:
                continue
            if address in members:
                if not old or address not in old_accounts or old_accounts[address]['user_id'] != members[address]['id']:
                    raise RuntimeError('Existing account mapping/credentials unavailable; provide a local mapping file')
                if members[address]['name'] != profile['name'] or members[address]['mbti'] != profile['mbti']:
                    raise RuntimeError('An existing persona account identity differs from the source profile')
                self.state['credentials'][address] = old.get('credentials', {}).get(address) or old.get('password')
                if not self.state['credentials'][address]:
                    raise RuntimeError('Mapped account password is unavailable in the local account state')
            else:
                self.state['credentials'][address] = secrets.token_urlsafe(24)
        for pid in ('city', 'baseball'):
            r = await client.get(BASE + '/api/v1/performances/' + pid)
            r.raise_for_status()
            body = r.json()
            if body.get('id') != pid or not body.get('available_dates') or not body.get('slots'):
                raise RuntimeError('Target performance is not bookable')
            stored = await asyncio.to_thread(self.evidence.query, 'SELECT id,title FROM performances WHERE id=:id', id=pid)
            if len(stored) != 1 or stored[0]['title'] != body['title']:
                raise RuntimeError('Configured database does not match the target API')
        monitoring = await asyncio.wait_for(collect(client), timeout=MONITOR_TIMEOUT)
        issue = monitoring_reason(monitoring, monitoring)
        if issue:
            raise RuntimeError(issue)
        self.monitor_baseline = monitoring
        save(self.directory / 'monitoring-baseline.json', monitoring)
        self.state['baseline'] = await asyncio.to_thread(self.evidence.counts)
        self.state['preparation_notes'] = [
            '기존 100명 프로필 보존 및 총 300명 로컬 프로필 준비',
            f'실제 DB에서 기존 계정 {len(members)}명 확인; 신규 가입 예정 {len(profiles)-len(members)}명',
            '콘서트·야구 API와 DB의 공연 ID·제목 일치 확인',
            'MariaDB·MongoDB 읽기 연결 및 실행 범위 기준 건수 확인',
            'Prometheus 서버·DB 지표 및 중단 감시 기준선 확인',
            '전체 100,000건·행동 로그 50,000건 공유 쓰기 예산 파일 준비',
            '이 준비 명령은 실제 서비스 회원가입·예매·행동 로그 API를 호출하지 않음',
        ]
        self.state['phase'], self.state['finished_at'] = '준비 완료 / 부하 미실행', now()
        self.persist()
        write_report(self.state, self.metrics, self.directory)
        self.persist()
        print('PREPARED: 300 local profiles; no production writes.', flush=True)

    async def authenticate(self):
        members = await asyncio.to_thread(self.evidence.members)
        self.accounts = []
        for profile in self.profiles:
            address = email(profile)
            password = self.state['credentials'][address]
            if address in members:
                data = await self.api.call('POST', '/auth/login', payload=dict(email=address, password=password))
            else:
                data = await self.api.call('POST', '/auth/signup', total=1, expected=(201,),
                         payload=dict(email=address, password=password, password_confirm=password,
                                      name=profile['name'], mbti=profile['mbti'], consent=True))
            user = data['user']
            if user['email'] != address or user['name'] != profile['name'] or user['mbti'] != profile['mbti'] or not user['consent']:
                raise RuntimeError('Authenticated account identity/consent mismatch')
            if address in members and user['id'] != members[address]['id']:
                raise RuntimeError('API account ID differs from database mapping')
            self.accounts.append(dict(profile=profile, token=data['access_token'], user_id=user['id'], logged_at=time.monotonic()))
            self.state.setdefault('account_map', {})[address] = user['id']
            self.persist()
            await asyncio.sleep(.15)
        self.state['account_ids'] = [a['user_id'] for a in self.accounts]
        self.persist()

    def events(self, account, detail, kinds, reservation=None):
        session = str(uuid.uuid4())
        output = []
        for kind in kinds:
            props = dict(synthetic=True, synthetic_run_id=self.state['run_id'],
                         synthetic_persona_id=account['profile']['id'], synthetic_scenario=self.api.stage,
                         synthetic_transport='api_load', performance_id=detail['id'])
            if reservation:
                props.update(reservation_id=reservation['id'], amount=reservation['amount'])
            output.append(dict(event_id=str(uuid.uuid4()), type=kind,
                          occurred_at=datetime.now(timezone.utc).isoformat(), session_id=session,
                          anonymous_id=str(uuid.uuid5(uuid.NAMESPACE_URL, account['profile']['id'])),
                          page={'path': '/', 'referrer': ''}, props=props, schema_version=1))
        return output

    async def visit(self, account, index, mode, performance=None):
        token = account['token']
        if time.monotonic() - account['logged_at'] > 2700:
            address = email(account['profile'])
            data = await self.api.call('POST', '/auth/login', payload=dict(email=address, password=self.state['credentials'][address]))
            token = data['access_token']
            account['token'], account['logged_at'] = token, time.monotonic()
        sorting = ('popular', 'date', 'price')[index % 3]
        listings = await self.api.call('GET', '/performances?sort=' + sorting, label='/performances')
        await self.api.call('GET', '/performances/ranking')
        chosen = performance or listings[index % len(listings)]['id']
        detail = await self.api.call('GET', '/performances/' + chosen, label='/performances/{id}')
        if mode == 'browse':
            return
        await self.api.call('POST', '/events', token=token, total=1, expected=(201,),
                            payload=dict(type='performance_view', performance_id=chosen))
        kinds = ['page_view', 'performance_view']
        reservation = None
        outcome = index % 20
        if outcome >= 16:
            reservation = await self.api.call('POST', '/reservations', token=token, total=5, expected=(201,),
                payload=dict(performance_id=chosen, performance_date=detail['available_dates'][0],
                             session_time=detail['slots'][0], seat_grade='STANDARD', quantity=1,
                             request_key=str(uuid.uuid4())))
            if reservation['status'] != 'REQUESTED' or reservation['payment_status'] != 'PENDING' or not reservation.get('is_mock'):
                raise RuntimeError('Unexpected reservation contract')
            self.state['reservations'].append(reservation['id'])
            self.persist()
            kinds += ['booking_start', 'reservation_request']
            if outcome == 19:
                reservation = await self.api.call('POST', '/reservations/' + reservation['id'] + '/complete',
                                                  token=token, total=3, label='/reservations/{id}/complete')
                if reservation['status'] != 'CONFIRMED' or reservation['payment_status'] != 'COMPLETED':
                    raise RuntimeError('Unexpected mock-payment contract')
                kinds.append('payment_complete')
            await self.api.call('GET', '/reservations', token=token)
            await self.api.call('GET', '/payments', token=token)
        events = self.events(account, detail, kinds, reservation)
        await self.api.call('POST', '/tracking/events', token=token, payload={'events': events},
                            total=len(events), tracking=len(events), expected=(202,))

    async def worker(self, index, spec, started):
        self.workers += 1
        counter = 0
        try:
            # Spread initial visits so opening a stage does not create an unintended spike.
            await asyncio.sleep(min(spec['seconds'], index / max(1, spec['vus']) * 10))
            while not self.stop.is_set() and time.monotonic() - started < spec['seconds']:
                elapsed = time.monotonic() - started
                target = spike_vus(elapsed, spec['vus']) if spec['mode'] == 'spike' else spec['vus']
                if index >= target:
                    self.active.discard(index)
                    await asyncio.sleep(.1)
                    continue
                self.active.add(index)
                visit_start = time.monotonic()
                outcome_index = 19 if spec['name'] == 'smoke' and counter == 0 else index + counter
                await self.visit(self.accounts[index], outcome_index, spec['mode'], spec.get('performance'))
                self.visits += 1
                counter += 1
                # Fixed 60-second journey cycle includes human dwell time and bounds write volume.
                delay = min(max(0, 60 - (time.monotonic() - visit_start)),
                            max(0, spec['seconds'] - (time.monotonic() - started)))
                try:
                    await asyncio.wait_for(self.stop.wait(), timeout=max(.001, delay))
                except asyncio.TimeoutError:
                    pass
        except (ApiFailure, BudgetExceeded, RuntimeError, KeyError, ValueError) as exc:
            self.halt(type(exc).__name__ + ': ' + str(exc))
        finally:
            self.active.discard(index)
            self.workers -= 1

    async def sample(self, spec, started):
        previous_visits = self.visits
        while not self.stop.is_set() and time.monotonic() - started < spec['seconds']:
            elapsed = time.monotonic() - started
            target = spike_vus(elapsed, spec['vus']) if spec['mode'] == 'spike' else spec['vus']
            self.state['samples'].append(dict(elapsed=time.monotonic() - self.api.epoch, target=target,
                    actual=len(self.active), inflight=self.api.inflight, stage=spec['name'],
                    completed_delta=self.visits-previous_visits))
            previous_visits = self.visits
            why = self.metrics.stop_reason(time.monotonic() - self.api.epoch)
            if why:
                self.halt(why)
            try:
                await asyncio.wait_for(self.stop.wait(), timeout=1)
            except asyncio.TimeoutError:
                pass

    async def resource_watch(self, spec, started):
        while not self.stop.is_set() and time.monotonic() - started < spec['seconds']:
            try:
                resources = await asyncio.wait_for(collect(self.http), timeout=MONITOR_TIMEOUT)
                with (self.directory / 'resources.jsonl').open('a', encoding='utf-8') as f:
                    f.write(json.dumps(resources) + '\n')
                why = monitoring_reason(resources, self.monitor_baseline)
                if why:
                    self.halt(why)
                self.persist()
            except (httpx.HTTPError, RuntimeError, ValueError, asyncio.TimeoutError):
                self.halt('Required monitoring became unavailable or exceeded its 10-second deadline')
            delay = min(30, max(0, spec['seconds'] - (time.monotonic() - started)))
            if delay <= 0:
                break
            try:
                await asyncio.wait_for(self.stop.wait(), timeout=delay)
            except asyncio.TimeoutError:
                pass

    async def execute(self, client):
        if self.state.get('started_at'):
            raise RuntimeError('Run was already started; reconcile database evidence before any resume')
        if self.budget.used() != (0, 0):
            raise RuntimeError('Unexpected pending write budget before execution')
        self.http = client
        self.api = Api(client, BASE, self.budget, self.metrics, self.directory / 'requests.jsonl')
        self.api.should_stop = self.stop.is_set
        self.state.update(started_at=now(), finished_at=None, phase='계정 준비 중', stop_reason=None)
        self.persist()
        try:
            await self.authenticate()
            await self.consistency()
            for spec in stage_plan():
                if self.stop.is_set():
                    break
                self.state['phase'], self.api.stage = spec['name'], spec['name']
                self.persist()
                print(f'STAGE {spec["name"]}: {spec["vus"]} VUs, {spec["seconds"]} seconds', flush=True)
                start, offset = time.monotonic(), len(self.metrics.rows)
                await asyncio.gather(self.sample(spec, start), self.resource_watch(spec, start),
                                     *(self.worker(i, spec, start) for i in range(spec['vus'])))
                verdict = stage_limit(self.metrics.rows[offset:])
                verdict.update(name=spec['name'], vus=spec['vus'], elapsed=time.monotonic()-start)
                self.state['stages'].append(verdict)
                evidence = await asyncio.to_thread(self.evidence.verify, self.state['baseline'], self.state['reservations'])
                self.state['evidence'] = evidence
                if self.budget.data['pending']:
                    evidence['issues'].append('Uncertain writes remain reserved; manual database reconciliation required')
                if evidence['issues']:
                    self.halt('; '.join(evidence['issues']))
                committed, pending = self.budget.data['committed'][0], self.budget.used()[0]
                if not committed <= evidence['total'] <= pending:
                    self.halt('Database evidence differs from the shared write ledger')
                if not verdict['passed']:
                    self.halt('API-specific stage thresholds failed: ' + spec['name'])
                self.persist()
                write_report(self.state, self.metrics, self.directory)
                print(f'RESULT {spec["name"]}: passed={verdict["passed"]}, new_rows={evidence["total"]}', flush=True)
                if not self.stop.is_set():
                    await asyncio.sleep(15)
        except (ApiFailure, BudgetExceeded, RuntimeError, KeyError, ValueError, httpx.HTTPError) as exc:
            self.halt(type(exc).__name__ + ': ' + str(exc))
        except asyncio.CancelledError:
            self.halt('operator_interrupted')
            raise
        finally:
            self.state.update(finished_at=now(), phase='중단' if self.stop.is_set() else '실행 완료')
            try:
                self.state['evidence'] = await asyncio.to_thread(self.evidence.verify, self.state['baseline'], self.state['reservations'])
                if self.budget.data['pending']:
                    self.state['evidence']['issues'].append('Uncertain writes remain reserved; manual database reconciliation required')
            except Exception:
                self.state.pop('evidence', None)
                self.state['preparation_notes'].append('최종 DB 대조 실패: 신규 건수·정합성은 미확정')
            self.persist()
            write_report(self.state, self.metrics, self.directory)

    async def consistency(self):
        self.api.stage = 'consistency'
        account = self.accounts[0]
        detail = await self.api.call('GET', '/performances/city', label='/performances/{id}')
        body = dict(performance_id='city', performance_date=detail['available_dates'][0],
                    session_time=detail['slots'][0], seat_grade='STANDARD', quantity=1,
                    request_key=str(uuid.uuid4()))
        reservation = await self.api.call('POST', '/reservations', token=account['token'],
                                          payload=body, total=5, expected=(201,))
        self.state['reservations'].append(reservation['id'])
        self.persist()
        replays = await asyncio.gather(*(self.api.call('POST', '/reservations', token=account['token'],
                          payload=body, expected=(200,)) for _ in range(2)))
        if any(r['id'] != reservation['id'] for r in replays):
            raise RuntimeError('Duplicate request created a different reservation')
        await self.api.call('POST', '/reservations', token=account['token'],
                            payload=dict(body, quantity=2), expected=(409,))
        rid = reservation['id']
        await asyncio.gather(self.api.call('POST', f'/reservations/{rid}/complete', token=account['token'],
                                           total=3, expected=(200, 409), label='/reservations/{id}/complete'),
                             self.api.call('POST', f'/reservations/{rid}/cancel', token=account['token'],
                                           total=3, label='/reservations/{id}/cancel'))
        events = self.events(account, detail, ['performance_view'])
        await self.api.call('POST', '/tracking/events', token=account['token'], payload={'events': events},
                            total=1, tracking=1, expected=(202,))
        replay = await self.api.call('POST', '/tracking/events', token=account['token'], payload={'events': events},
                                     total=1, tracking=1, expected=(202,))
        if replay != dict(accepted=0, duplicates=1):
            raise RuntimeError('Tracking replay was not deduplicated')
        evidence = await asyncio.to_thread(self.evidence.verify, self.state['baseline'], self.state['reservations'])
        if evidence['issues'] or evidence['deltas']['reservations'] != 1:
            raise RuntimeError('Consistency pilot database evidence failed')
        self.state['preparation_notes'].append('동일 요청 키 동시 재전송·다른 내용 충돌·결제/취소 경합·로그 중복 제거 소규모 검사 통과')
        self.persist()


async def main(args):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', args.run_id):
        raise ValueError('Invalid run-id')
    campaign = Campaign(args.run_id)
    lock = ARTIFACTS / 'load-test.lock'
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(descriptor, json.dumps({'pid': os.getpid(), 'run_id': args.run_id}).encode())
    os.close(descriptor)
    try:
        async with httpx.AsyncClient(verify=tls_context(), timeout=15,
                limits=httpx.Limits(max_connections=350, max_keepalive_connections=100), follow_redirects=False,
                headers={'User-Agent': 'TikitLoadTest/1.0 run=' + args.run_id}) as client:
            if campaign.state.get('started_at'):
                raise RuntimeError('Inspect the prior execution before attempting to resume')
            await campaign.prepare(client)
            if args.execute:
                await campaign.execute(client)
                if campaign.stop.is_set():
                    raise SystemExit(2)
    finally:
        if campaign.evidence:
            campaign.evidence.close()
        lock.unlink()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--execute', action='store_true', help='Create accounts and send production load; omitted means preparation only')
    asyncio.run(main(parser.parse_args()))
