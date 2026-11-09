# 조회 부하 테스트 — events 복합 인덱스 적용 후 (rankindex)

- 실행 ID: `loadtest-20261108-claude-read`
- 일시: 2026-11-08 10:36 – 11:03 KST
- 단계: precheck 1 VU, read 10 / 25 / 50 / 100 VU (각 5분)
- 계정: `loadtest-20261106-claude`의 100개 계정을 재사용했고, 새 계정은 만들지 않았습니다.
- 변경 내용
  - 마이그레이션 `0005_events_type_performance_index`: `events(type, performance_id)` 복합 인덱스를 추가하고 `ix_events_type`을 삭제합니다.
  - 배경: 랭킹 쿼리가 `events` 테이블을 처음부터 끝까지 읽고 있었습니다.
- 비교 대상: `loadtest-20261107-claude-full3`의 read 단계(인덱스 적용 전, events 약 9만~10만 건)

## 1. 요약

| 항목 | 결과 |
| --- | --- |
| 판정 | precheck와 read 10 / 25 / 50 / 100 VU 모두 통과 |
| 랭킹 API (100 VU) | p50 69 → **38ms**, p95 121 → **70ms** |
| 공연 목록 API (100 VU, 인기순) | p50 55 → 47ms, p95 121 → 104ms |
| MariaDB CPU 최대 (100 VU) | 42% → **16%** |
| 처리량 (100 VU) | 163.6 → 166.4 RPS. 부하 발생기 쪽 한계로, 비슷한 수준입니다. |
| 오류 | 502 3건 (read-10vu). 테스트 중 서버 재시작 때문입니다(3절). |
| 정합성 검증 | 통과 |

`events`는 오늘 13만 3천 건으로, 비교 대상 실행 때보다 데이터가 더 많습니다. 그런데도 랭킹 응답 시간은 거의 절반이 되었습니다.

## 2. 단계별 비교 (p50 / p95, ms)

| VU | ranking 전 | ranking 후 | list 전 | list 후 | detail 전 | detail 후 | MariaDB CPU 전 → 후 |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 10 | 61 / 81 | 41 / 63 | 51 / 83 | 48 / 82 | 18 / 38 | 19 / 38 | 5 → 4% |
| 25 | 57 / 78 | 35 / 55 | 44 / 79 | 40 / 75 | 15 / 33 | 14 / 33 | 10 → 6% |
| 50 | 56 / 83 | 33 / 55 | 42 / 83 | 38 / 75 | 14 / 34 | 14 / 33 | 21 → 11% |
| 100 | 69 / 121 | 38 / 70 | 55 / 121 | 47 / 104 | 19 / 51 | 18 / 48 | 42 → 16% |

- 랭킹은 모든 단계에서 p50이 20–30ms 줄었습니다. 그만큼 DB 쿼리 시간이 줄어든 것입니다.
  - DB에서 쿼리만 직접 재 보면 55ms에서 16ms로 줄었습니다.
  - 실행 계획도 바뀌었습니다. 전에는 테이블을 처음부터 끝까지 읽었고, 지금은 인덱스만 읽고 끝납니다(`Using index`).
- 공연 목록(인기순 정렬)도 같은 구매 수 서브쿼리를 쓰므로 조금 빨라졌습니다.
  - 목록은 공연 680건을 전부 직렬화하는 비용이 커서 개선 폭이 랭킹보다 작습니다.
- 상세 조회는 이벤트를 세지 않는 API라 변화가 없습니다. 비교 기준으로서 두 실행의 환경이 같았다는 근거가 됩니다.
- 100 VU에서 MariaDB CPU가 42%에서 16%로 떨어졌습니다. 조회 부하에서 DB가 가장 먼저 한계에 닿을 위험이 크게 줄었습니다.
- FastAPI CPU는 48% / 44%로 그대로입니다. 이제 조회 부하의 병목은 DB가 아니라 FastAPI(직렬화)입니다.

## 3. 502 3건 — 테스트 중 서버 재시작

| 시각 (KST) | API | 원인 |
| --- | --- | --- |
| 10:39:19 | ranking | 176 `tikit-api` 재시작 (systemd Stopping → Started, 01:39:19 UTC) |
| 10:39:50 | search, detail | 175 `tikit-api` 재시작 (01:39:50 UTC) |

- 두 서버 모두 `systemctl`로 서비스를 다시 시작한 기록이 있습니다. 비정상 종료나 자동 재시작이 아니며, NRestarts=0입니다.
- 비슷한 시각에 category, list, search에서 최대 1초 남짓 걸린 응답도 같은 원인입니다.
  - 서버 한 대가 재시작하는 동안 Nginx가 요청을 다른 서버로 넘기면서 생긴 지연입니다.
- 인덱스는 DB에 이미 적용된 상태였으므로, 재시작은 측정 결과에 영향을 주지 않습니다.
  - 재시작 이후의 read-25 / 50 / 100 VU 단계는 오류 0건입니다.
- 참고: 서비스를 재시작하면 처리 중이던 요청이 502로 끊깁니다. 무중단으로 배포하려면 서버를 한 대씩 HAProxy/Nginx에서 빼고 재시작하는 절차가 필요합니다.

## 4. 배포 상태 확인 — alembic_version 불일치

- DB 인덱스: `ix_events_type_performance_id(type, performance_id)`가 있고, `ix_events_type`은 지워져 있습니다. 마이그레이션 0005와 같은 상태입니다.
- 그런데 `alembic_version`은 아직 **`0004`**입니다. 인덱스를 SQL로 직접 만든 것으로 보입니다.
- 이대로 다음에 `alembic upgrade head`를 실행하면, 0005가 이미 있는 인덱스를 다시 만들려다 실패합니다.
- 조치: DB 관리자가 `alembic stamp 0005`를 한 번 실행하면 됩니다. 이 명령은 버전 기록만 바꾸고 스키마는 건드리지 않습니다.
- **해결 (2026-11-08):** `alembic stamp 0005`를 실행한 뒤 다시 확인했습니다. `alembic_version`은 `0005` 한 행이고, `events` 인덱스는 0005 마이그레이션 결과와 같습니다(`ix_events_type_performance_id(type, performance_id)` 있음, `ix_events_type` 없음).

## 5. 산출물

`syntheticData/playwright/artifacts/loadtest-20261108-claude-read/`

- `report_tables.md`
- `verification.json`
- `db_delta.md`
- `requests.csv`
- `runner.out`
