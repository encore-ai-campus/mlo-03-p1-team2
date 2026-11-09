# 부하 테스트 실행기

`docs/loadTestPlan.md`의 조건을 실제 서비스에 적용하기 위한 도구다. 결과 보고서 예시는
`docs/loadTestResult_claude.md`에 있다.

## 파일

| 파일 | 역할 |
| --- | --- |
| `extend_personas.py` | `personas.json`의 기존 사용자를 보존하고 신규 사용자만 추가한다. 원본 100명은 `personas.v100.json`으로 보존 |
| `run_load.py` | `init` 실행 상태 생성 → `accounts` 없는 계정만 가입 → `run` 단계별 부하 |
| `budget.py` | 전체·행동 로그 쓰기 예산. 모든 VU와 단계가 하나의 예산을 공유 |
| `infra.py` | DB 신규 건수 집계, Prometheus 수집, 경로·자격 증명 로딩 |
| `verify_load.py` | 실행 후 MariaDB·MongoDB 정합성 검증(읽기 전용) |
| `report.py` | 분 단위·API별·서버 지표 표 생성 |
| `precheck.postman_collection.json` | Postman CLI 읽기 전용 사전 기능 확인 |

## 실행

저장소 루트에서 실행한다. DB 접속 정보는 `backend/.env` 또는 같은 이름의 환경 변수
(`DATABASE_URL`, `MONGODB_URL`, `MONGODB_DB`)에서 읽으며 출력하거나 저장하지 않는다.

```powershell
python -m venv syntheticData/loadtest/.venv
syntheticData/loadtest/.venv/Scripts/python.exe -m pip install -r syntheticData/loadtest/requirements.txt
$PY = "syntheticData/loadtest/.venv/Scripts/python.exe"

postman collection run syntheticData/loadtest/precheck.postman_collection.json
& $PY syntheticData/loadtest/run_load.py init     --run-id <실행 ID>
& $PY syntheticData/loadtest/run_load.py accounts --run-id <실행 ID>
& $PY syntheticData/loadtest/run_load.py run      --run-id <실행 ID>
& $PY syntheticData/loadtest/verify_load.py       --run-id <실행 ID>
& $PY syntheticData/loadtest/report.py            --run-id <실행 ID>
```

- 실행 기록은 Git에서 제외된 `syntheticData/playwright/artifacts/<실행 ID>/`에 저장된다.
  `state.json`에는 테스트 비밀번호가 있으므로 공유하거나 커밋하지 않는다.
- 같은 실행 ID로 `run`을 다시 실행하면 끝난 단계는 건너뛰고 저장된 예산에서 이어간다.
  중단 시점에 진행 중이던 쓰기 요청은 저장 여부를 알 수 없으므로 예약된 상태로 유지되고,
  다음 실행 시작 시 DB 건수와 대조해 확정한다.
- 실행 중 즉시 멈추려면 실행 디렉터리에 `STOP` 파일을 만든다. 진행 중인 요청이 끝난 뒤 종료된다.
- `postman performance run`은 클라우드 컬렉션 ID가 필요하고 전역 쓰기 예산, 구간별 자동 중단,
  VU별 계정 분리를 지원하지 않아서 본 부하에는 사용하지 않는다.

## 부하 모델

- 닫힌 모델(closed model)이다. VU마다 계정과 HTTP 연결을 따로 쓰고 방문을 반복한다.
- 조회(read): 목록·랭킹·검색·카테고리·상세. 요청 사이 0.2~0.6초, 방문 사이 0.5~1.5초. 쓰기 없음
- 혼합(mixed): 방문 기준 조회 80%, 예매 15%, 예매+모의 결제 5%. 요청 사이 1~2초, 방문 사이 5~10초.
  상세 조회 시 `POST /events`, 방문 끝에 행동 로그 배치(최대 10건) 전송
- 집중(focus): `city` 또는 `baseball` 한 공연에 상세 → 40% 예매 → 그중 50% 결제. 5 VU 기본에서
  90초 후 20초 동안 최대 VU로 증가, 40초 동안 감소
- 지속(sustained): 통과한 최대 VU에서 30분. 남은 예산 안에서 끝나도록 방문 간 대기를 계산한다.

- 스트레스(stress): 조회 VU와 혼합 VU를 50:50으로 섞어 1 → 200 VU를 15분 동안 늘리고, 3분 유지한 뒤 2분 동안 줄인다.
  곡선은 `run_load.py`의 `STRESS`에서 바꾼다. 결과 예시는 `docs/loadTestResult_claude_stress.md`에 있다.

```powershell
& $PY syntheticData/loadtest/run_load.py init --run-id <실행 ID> --reuse-accounts-from <계정을 만든 실행 ID>  # 가입 없음
& $PY syntheticData/loadtest/run_load.py run  --run-id <실행 ID> --phases stress
& $PY syntheticData/loadtest/stress_report.py --run-id <실행 ID>   # 기준별 최초 이탈 VU, 30초 구간 표
```

곡선과 시나리오는 옵션으로도 바꿀 수 있다: `--stress 최대VU,증가초,유지초,감소초`, `--stress-mix blend|mixed|read`.
실행 중에는 MariaDB `SHOW GLOBAL STATUS`를 10초마다 직접 조회해 `db_status.jsonl`에 남긴다(exporter가 꺼져 있어도 연결 90% 중단 조건이 동작).
DB 전체의 전후 변화는 `db_snapshot.py snap --label before|after`와 `db_snapshot.py diff`로 본다(읽기 전용, `db_delta.md` 생성).
결과 예시는 `docs/loadTestResult_claude_db50.md`에 있다.

계정을 재사용하면 시작 시점에 그 계정들이 이미 가진 MariaDB 행을 기준선으로 저장하고, 신규 건수와 정합성 검증에서 제외한다.

## 판정·중단 기준

- 합격: 조회 API p95 500ms 이하, 쓰기 API p95 1초 이하, 정상 요청 실패율 1% 미만(API별·전체)
- 자동 중단: 최근 30초 실패율 5% 초과, 최근 60초 p95 3초 초과, 서버 다운·재부팅,
  MariaDB 연결이 최대 연결 수의 90% 이상, 디스크 1GB 미만, 쓰기 예산 소진, `STOP` 파일
