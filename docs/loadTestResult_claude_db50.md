# DB 변화 관찰 부하 테스트 결과 (Claude 실행, 50 VU · 5분)

작성일: 2026-11-07

상태: **완료.** 혼합 시나리오 50 VU로 5분 동안 부하를 주면서, 그동안 MariaDB와 MongoDB가 어떻게 바뀌는지 기록했다.
실패 요청은 0건이고 정합성 검증도 통과했다.

## 1. 요약

| 항목 | 결과 |
| --- | --- |
| 실행 ID | `loadtest-20261107-claude-db50` |
| 실행 시각 (KST) | 2026-11-07 09:06:07 ~ 09:11:15 |
| 부하 곡선 | 0~30초 VU 1 → 50, 30초~4분 30초 50 유지, 마지막 30초 50 → 0 |
| 시나리오 | 혼합만 사용(방문 기준 조회 80% / 예매 15% / 예매+결제 5%). 계정은 전날 만든 100개 중 50개를 재사용, 가입 없음 |
| 요청 / 실패 | 7,203건 / **0건**, 방문 1,163회(둘러보기 933 · 예매 181 · 결제 49) |
| 처리량 · 응답 | 약 26 RPS, 전체 p95 63ms / p99 88ms |
| 신규 레코드 | **6,653건** (MariaDB 3,130 + MongoDB 3,523) |
| 정합성 | 통과. 예매 230건이 모두 결제와 짝이 맞음(대기 181 · 확정 49). 행동 로그 누락·중복 0건 |
| DB 부담 | MariaDB 연결 최대 8/151, 실행 스레드 최대 2, 잠금 대기·데드락·느린 쿼리 0, buffer pool 디스크 읽기 0 |

## 2. 테이블별 변화 (테스트 전후 스냅샷, 간격 371초)

DB 전체를 센 값이다. 측정 계정만 센 것이 아니라 다른 사용자의 행도 포함한다. 이 시간 동안 늘어난 행은 모두 이번 실행 계정의 것과 일치했다.

| 저장소 | 테이블·컬렉션 | 전 | 후 | 증가 |
| --- | --- | ---: | ---: | ---: |
| MariaDB | `events` (조회·예매 시작·예매·결제 이벤트) | 28,511 | 30,623 | **+2,112** |
| MariaDB | `reservations` | 3,340 | 3,570 | +230 |
| MariaDB | `payments` | 3,340 | 3,570 | +230 |
| MariaDB | `status_history` | 9,232 | 9,790 | +558 |
| MariaDB | `users`, `favorites`, `performances`, `orders`, `notification_settings` | | | 0 |
| MongoDB | `tikit.events` (행동 로그) | 48,894 | 52,417 | **+3,523** (크기 33.5MB → 36.0MB) |
| MongoDB | `tikit.simulation` | 12,127 | 12,127 | 0 |

- 50 VU 5분 기준으로 **분당 약 1,300건**이 쌓인다(MariaDB 약 630 + MongoDB 약 700).
- MariaDB 테이블 크기는 `information_schema` 통계가 바로 갱신되지 않아 거의 그대로 보인다. 실제 증가량은 행 수로 판단해야 한다.

## 3. MariaDB 서버 상태 변화

| 항목 | 증가량 | 초당 | 의미 |
| --- | ---: | ---: | --- |
| `Questions` (전체 쿼리) | 7,252 | 19.5 | |
| `Com_insert` | 2,851 | 7.7 | 예매·결제·이력·이벤트 INSERT |
| `Com_select` | 2,699 | 7.3 | |
| `Com_update` | 98 | 0.3 | 결제 완료 시 예매·결제 상태 변경 |
| `Com_commit` / `Com_rollback` | 622 / 3,014 | | rollback은 SQLAlchemy가 연결을 풀에 돌려줄 때 하는 초기화로 보인다(읽기 요청 수와 비슷함). 오류가 아님 |
| **`Handler_read_rnd_next`** (전체 스캔으로 읽은 행) | **6,849,662** | **18,464** | SELECT 1건당 약 2,500행. 아래 4장 참고 |
| `Handler_read_key` (인덱스로 읽은 행) | 5,373,561 | 14,485 | |
| `Select_scan` (전체 스캔 SELECT) | 897 | 2.4 | 목록 요청 1,163건과 비슷한 수준 |
| **`Created_tmp_disk_tables`** | **612** | 1.6 | 디스크에 만든 임시 테이블. 메모리 임시 테이블은 2,257개 |
| `Innodb_buffer_pool_reads` (디스크 읽기) | 0 | 0 | buffer pool 128MB 안에서 모두 처리 |
| `Innodb_os_log_written` (redo 로그) | 2.4MB | 6.6KB/s | |
| `Innodb_row_lock_waits`, `Innodb_deadlocks`, `Slow_queries` | 0 | 0 | |
| `Connections` (새 연결) | 6 | | 연결 풀이 재사용됨. `Threads_connected`는 10초 간격 36회 측정에서 내내 4~8 |
| `Aborted_clients` | 5 | | 끊긴 클라이언트 연결. 원인 미확인(4장 참고) |

50 VU 유지 구간의 10초 간격 추이(30초 묶음):

| 목표 VU | INSERT/s | SELECT/s | 쿼리/s | 연결 수 |
| ---: | ---: | ---: | ---: | ---: |
| 50 | 6.6 | 7.0 | 19.7 | 8 |
| 50 | 10.3 | 10.3 | 28.0 | 8 |
| 50 | 10.5 | 9.6 | 26.1 | 8 |
| 50 | 9.6 | 9.0 | 24.4 | 8 |
| 50 | 9.9 | 8.8 | 23.8 | 8 |
| 50 | 10.2 | 9.3 | 25.4 | 8 |
| 50 | 10.3 | 8.7 | 23.6 | 8 |
| 50 | 10.6 | 9.5 | 25.7 | 8 |
| 40 | 10.2 | 9.6 | 26.2 | 8 |
| 0 | 5.0 | 3.9 | 10.7 | 8 |

MongoDB는 insert 3,523건(초당 9.5)이 늘었고, 연결이 21개에서 34개로 늘었다.

## 4. 관찰한 점

- **DB 자체는 여유가 매우 크다.** 50 VU에서 MariaDB 연결은 151개 중 8개였다. 잠금 경합이 없고, 모든 읽기가 메모리(buffer pool)에서 처리됐다.
- **SELECT 1건당 읽는 행이 많다.** 쓰기가 많은 이 시나리오에서도 전체 스캔으로 초당 1.8만 행을 읽었다. 인기순 목록 요청 수만큼 전체 스캔(`Select_scan`)이 생겼다.
  디스크 임시 테이블도 612개 만들어졌다. 인기순 정렬을 위해 `events`를 요청마다 집계하는 쿼리로 보인다(전날 결과 7.1장과 같은 지점).
  **`events` 테이블은 이 시나리오에서 분당 약 420행씩 늘어나므로, 데이터가 쌓일수록 목록 API 비용도 함께 커진다.**
  쿼리를 직접 `EXPLAIN`으로 확인하지는 않았다. 근거는 카운터 증가량과 요청 수의 비례다.
- `Aborted_clients`가 5 늘었다. 앱 연결 풀이 연결을 정리하지 않고 끊은 경우로 보이지만, 확인하지 않았다.
- `Innodb_data_written`은 전후 모두 0으로 나왔다. 이 MariaDB 버전에서 해당 카운터가 집계되지 않는 것으로 보이며, 쓰기량은 redo 로그(`Innodb_os_log_written`)로 판단했다.

## 5. 측정 방법과 한계

- Prometheus의 MariaDB exporter가 여전히 `mysql_up = 0`이다. 그래서 실행기가 `SHOW GLOBAL STATUS`를 10초마다 직접 조회했다(`db_status.jsonl`).
  "DB 연결 90% 이상이면 중단" 조건도 이 값으로 동작했다.
- 테스트 전후 스냅샷(`db_before.json`, `db_after.json`)은 `db_snapshot.py`로 찍었다. 테이블별 정확한 `COUNT(*)`, MariaDB 전역 상태, MongoDB 컬렉션 통계와 `serverStatus`가 들어 있다.
- 스냅샷 간격(371초)에는 부하 전후의 대기 시간이 포함된다. 같은 시간에 다른 사용자의 요청이 있었다면 카운터에 섞인다. 행 증가량은 실행 계정 기준 집계와 정확히 일치했다.

## 6. 다시 실행하는 방법

```powershell
$PY = "syntheticData/loadtest/.venv/Scripts/python.exe"
$R  = "<새 실행 ID>"
& $PY syntheticData/loadtest/run_load.py init --run-id $R --reuse-accounts-from loadtest-20261106-claude
& $PY syntheticData/loadtest/db_snapshot.py snap --run-id $R --label before
& $PY syntheticData/loadtest/run_load.py run --run-id $R --phases stress --stress 50,30,240,30 --stress-mix mixed
& $PY syntheticData/loadtest/db_snapshot.py snap --run-id $R --label after
& $PY syntheticData/loadtest/db_snapshot.py diff --run-id $R
& $PY syntheticData/loadtest/verify_load.py --run-id $R
```

`--stress`는 `최대VU,증가초,유지초,감소초`이고, `--stress-mix`는 `blend`(조회·혼합 50:50), `mixed`, `read` 중 하나다.
실행 기록은 `syntheticData/playwright/artifacts/loadtest-20261107-claude-db50/`에 있다.
`db_delta.md`, `db_status.jsonl`, `stress_report.md`, `verification.json`이 들어 있다.
