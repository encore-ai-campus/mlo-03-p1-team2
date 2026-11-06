# Playwright 페르소나 자동화 안내

이 폴더는 `../personas.json`의 가상 사용자가 실제 서비스 화면에서 로그인·조회·
찜·예매·모의 결제를 하도록 Playwright로 자동화하는 도구다.
기존의 README·설계·계획·결과·기간 분석 문서는 이 파일 하나로 통합했다.

## 현재 진행 상태

- 최초 페르소나 100명 가입·행동 실행은 완료했다. MongoDB 로그 2,404건을 검증했다.
- 추가 데이터도 **동일한 100명**을 사용하며 신규 회원가입을 하지 않는다.
- 추가 방문은 처음에 모두 10회로 설정했으나, 사용자 요청에 따라
  **개인별 2~23회 무작위 방문, 전체 1,000회**로 변경했다.
- 횟수는 관람 빈도를 참고한 무작위 분포다. 먼저 생성된 기록은 보존했으므로
  모든 사용자가 처음부터 완전히 같은 조건으로 재추출된 데이터는 아니다.
- 추가 방문 203회에서 일시 중단했고, 중단된 4개 방문은 DB 대조 후 복구했다.
  확정한 무작위 일정으로 총 1,000회를 완료하고 DB 검증을 통과했다.
- 콘서트·야구 예매 집중 부하 테스트는 후속 시나리오만 준비했고 실행하지 않았다.

## 어떤 파일을 보면 되나

처음에는 **이 안내 문서**, 실제 동작은 **`run_periods.py`**, 결과는
**`artifacts/<실행 ID>/`**를 보면 된다. 다른 파일은 실행기가 사용하는 보조 코드다.

### 실행 코드

| 파일 | 역할 | 직접 실행 여부 |
| --- | --- | --- |
| `run.py` | 최초 페르소나 계정 가입·로그인 및 기본 행동 실행 | 최초 계정 준비용 |
| `run_periods.py` | 기존 계정의 추가 방문과 가상 기간별 데이터 생성 | 현재 추가 생성용 |
| `serve.py` | 자동화 전용 backend 8001/frontend 5174 실행·종료 | 서버 시작용 |
| `simulation_app.py` | 기존 backend를 전용 프로세스에서 감싸 컬렉션·접근 키를 보호 | `serve.py`가 불러옴 |

### 동작 규칙과 보조 코드

| 파일 | 역할 |
| --- | --- |
| `scenarios.py` | 기본 페르소나별 카테고리·방문·전환·수량 규칙과 합성 표시 |
| `periods.py` | 기간별 방문 일정, 실제 시간과 분리된 가상 시간, 일·주·월 집계 |
| `safety.py` | 실패 시 새 사용자 작업 중단, 비밀번호 가림, 상태 저장·증거 대조 |
| `transport.py` | 브라우저가 로그 전송을 끝내기 전에 닫히지 않도록 fetch 완료 관찰 |

### 검증·복구 코드

| 파일 | 역할 |
| --- | --- |
| `verify.py` | 최초 실행의 MariaDB 계정·찜·예매·결제와 MongoDB 로그 대조 |
| `verify_periods.py` | 추가 방문의 기존 데이터 보존, 로그·거래 금액, 가상 기간 집계 검증 및 CSV 출력 |
| `audit.py` | 최초 실행 중단 시 DB와 상태 파일을 읽어 복구 가능 여부 확인 |
| `recover.py` | 감사 결과에 따라 초기 실행의 로그인·조회 등 복구. 예매·결제를 재생성하지 않음 |
| `guard.postman.js` | Postman CLI에서 전용 서버·컬렉션 확인용 검사 |

`audit.py`·`recover.py`는 최초 실행의 상태 구조를 기준으로 한다.
기간별 실행을 중단한 경우 그대로 적용하지 말고, 그 실행의 기준 스냅샷까지 대조해야 한다.

### 테스트·설치·후속 시나리오

| 파일 | 역할 |
| --- | --- |
| `test_scenarios.py` | 기본 계획·가중치·이메일 구분·재개 규칙 테스트 |
| `test_safety.py` | 실패 중단·비밀값 가림·임시 파일 잠금·데이터 대조 테스트 |
| `test_transport.py` | 실제 서비스에 접속하지 않는 브라우저 전송 완료 테스트 |
| `test_periods.py` | 가상 날짜·한국 시간·기간 집계·거래 금액 대조 테스트 |
| `requirements.txt` | Playwright 의존성 버전 |
| `load_scenarios.json` | 나중에 실행할 콘서트·야구 예매 집중 부하 테스트 제안 |
| 프로젝트 루트의 `.gitignore` | 가상환경·비밀값이 있는 실행 기록·임시 파일을 Git에서 제외. 이 폴더의 중첩 설정은 루트로 통합함 |

### 자동 생성 폴더

| 폴더 | 내용 | 관리 방법 |
| --- | --- | --- |
| `.venv/` | 이 도구 전용 Python·Playwright 설치 환경 | 소스가 아니며 Git에 올리지 않음 |
| `__pycache__/` | Python이 자동 생성한 실행 캐시 | 직접 편집할 필요 없음 |
| `artifacts/` | 실행 상태·비밀번호·계정 매핑·로그·검증·CSV 등 | 실행 재개에 필요. 폴더 전체를 지우지 않음 |

## 실제 데이터는 어디에 저장되나

| 위치 | 저장 데이터 |
| --- | --- |
| MariaDB | 실제 테스트 회원, 찜, 예매, 모의 결제, 업무 이벤트 |
| MongoDB `tikit.simulation` | Playwright가 실제 화면에서 발생시킨 합성 사용자 행동 로그 |
| `artifacts/<run-id>/` | 실행 증거와 분석 결과 파일 |

합성 사용자는 실제 고객이 아닌 테스트용 페르소나다. 이름·MBTI는 원본 그대로 사용하고,
이메일은 `persona0001+synthetic@example.com`처럼 표시한다.
MongoDB 로그의 `props.synthetic`, `synthetic_run_id`, `synthetic_persona_id`로 구분한다.
인기순 등 서비스 집계에도 영향을 주므로 분석할 때 실제 고객 데이터와 구분한다.

## artifacts 안의 파일은 무엇인가

현재 `persona-20261106/`은 최초 실행, `persona-periods-20261106/`은 추가 방문 실행이다.
다음 파일은 실행 단계에 따라 생성되므로 모든 폴더에 전부 있는 것은 아니다.

| 파일 | 의미 |
| --- | --- |
| `state.json` | 계정 ID 매핑·진행 상태·테스트 비밀번호. 공유/커밋 금지 |
| `server.json` | 전용 서버의 실행 ID·접근 키. 공유/커밋 금지 |
| `plan.json` | 실행할 사용자별 방문·행동 계획 |
| `random-visit-allocation.json` | 사용자별 무작위 방문 수와 총량 |
| `previous-fixed-plan.json` | 무작위 분포 변경 전 고정 방문 계획 보존본 |
| `stopped-audit.json`, `period-recovery-history.jsonl` | 기간별 실행 중단 시 DB 감사와 복구 기록 |
| `attempts.jsonl` | 로그 전송 시도 기록 |
| `events.jsonl` | 서버가 저장 또는 중복 확인한 이벤트 기록 |
| `summary*.json`, `period-summary*.json` | 실행 건수 요약 |
| `verification*.json` | 실제 DB와 대조한 검증 결과 |
| `period-baseline.json` | 추가 실행 전 회원·찜·기존 예매·파일의 보존 기준 |
| `recovery-*.json`, `recovery-history.jsonl` | 중단·복구 검사와 이전 상태 보존 기록 |
| `daily.csv`, `weekly.csv`, `monthly.csv` | 일·주·월별 사용자·방문·조회·찜·예매·모의 매출 |
| `analytics.json`, `daily-query.json` | 집계 원본과 MongoDB 조회 파이프라인 |
| `progress.log`, `backend.log`, `frontend.log`, `chromium.log` | 실행·서버·브라우저 진단 기록 |
| `*.png` | 시험 실행 또는 오류 발생 시 화면 캡처 |

## 날짜와 한국 시간

| 필드 | 의미 |
| --- | --- |
| `occurred_at` / `received_at` | 실제 동작·수신 시각. UTC Date이며 변경하지 않음 |
| `props.simulation_at` | 분석용 가상 시각, UTC 문자열 |
| `props.simulation_at_kst` | 같은 가상 시각의 한국 시간 문자열 |
| `props.simulation_date` | 한국 시간 기준 가상 분석 일자 |
| `props.simulation_time_is_fictional` | 가상 시간축임을 나타내는 `true` 표시 |
| `props.synthetic_visit_id` | 가상 분석 기간에서 한 방문을 식별하는 ID |

추가 방문의 기간 분석은 가상 30일을 사용한다. 실제로 30일 동안 관측했다는 뜻이 아니다.
MariaDB 거래는 실제 현재 시각에 생성한다. 가상 일별 매출은 MongoDB의 날짜와 실제
예매 ID·금액을 연결해 검증한다. `new_in_period_users`는 기간 내 첫 등장 사용자이지 신규 가입자가 아니다.

Compass의 Documents Filter에서 이번 추가 방문만 보려면 다음을 사용한다.

```json
{"props.synthetic_run_id":"persona-periods-20261106"}
```

하루를 조회하려면 `"props.simulation_date":"2026-10-08"` 조건을 추가한다.

## 나중에 사용자를 늘리는 방법

**기본 입력은 `syntheticData/personas.json`이 맞다. 기존 사용자를 보존하고 새 사용자만
추가하는 방식으로 확장해야 한다.** 하지만 현재는 파일에 추가만 하면 자동으로 모두 실행되지는 않는다.

1. 현재 100명에 대한 실행과 검증을 먼저 끝내고 원본 프로필·계정 매핑·입력 해시를 보관한다.
2. 기존 `users`의 ID·이름·이메일·MBTI·취향은 그대로 유지하고 새 사용자만 추가한다.
3. 새 사용자의 ID·이메일·이름 중복을 검사하고 `metadata.count`를 전체 인원으로 맞춘다.
4. 새 사용자에 대해서만 테스트 계정을 가입시키고 원본 ID ↔ 실제 회원 ID를 저장한다.
5. 실행기의 인원 제한과 프로필 버전 검증을 확장한 뒤 기존 계정+신규 계정으로 다음 실행을 시작한다.

### 주의할 점

- 기존 `generatePersonas.py --count 200` 결과로 `personas.json`을 덮어쓰면 안 된다.
  인원 수를 바꾸면 기존 100명의 이름·MBTI·취향 배정이 유지된다는 보장이 없다.
- 생성기를 다른 시드로 돌려도 이메일은 `persona0001@example.com`부터 다시 쓰므로
  두 실행 결과를 그대로 붙이면 이메일이 겹친다. 신규 사용자 추가용 생성 절차가 필요하다.
- 현재 `run.py`는 CLI에서 최대 100명을 받고, `run_periods.py`도 기존 100명으로 제한한다.
  파일을 200명으로 늘리는 것과 실행기를 200명으로 확장하는 것은 별도 작업이다.
- 실행 중 `personas.json`을 바꾸면 입력 해시 검증 때문에 재개가 거절된다.
  과거 실행을 재현하려면 당시 입력 버전도 함께 보존해야 한다.
- 신규 사용자 추가 기능은 아직 구현하지 않았다. 이번 작업에서는 100명을 유지한다.

## 설치·실행의 기본 흐름

프로젝트 루트에서 설치한다.

```powershell
python -m venv syntheticData/playwright/.venv
syntheticData/playwright/.venv/Scripts/python.exe -m pip install -r syntheticData/playwright/requirements.txt
syntheticData/playwright/.venv/Scripts/python.exe -m playwright install chromium
```

실행 순서는 **계획 준비 → DB 기준 스냅샷 → 전용 서버 실행 → 소규모 실행·검증 → 확대 → 최종 검증**이다.
`serve.py`는 기존 backend 의존성이 있는 Python과 Node를 사용한다.
`verify*.py`도 기존 backend 의존성이 설치된 Python에서 실행해야 한다.

전용 서버는 `serve.py --run-id <실행 ID>`로 시작하고 Ctrl+C로 종료한다.
자동화용 5174/8001은 기존 개발 서버 5173/8000과 구분한다.
아래 원문 기록에 최초/기간별 실행 명령이 있으며 현재 안내를 우선한다.
`run_periods.py`의 `--visits 10`은 현재 **평균 목표(100명 기준 총 1,000회)**다.
새 실행도 무작위 횟수를 기본으로 사용하며, 같은 실행의 계획은 고정해 재개 시 유지한다.
이번 실행을 이어갈 때는 다음을 사용한다. 완료 방문은 재실행하지 않는다.

```powershell
syntheticData/playwright/.venv/Scripts/python.exe syntheticData/playwright/run_periods.py --run-id persona-periods-20261106 --start 2026-10-08 --visits 10 --workers 4
python syntheticData/playwright/verify_periods.py --run-id persona-periods-20261106
```

다시 중단됐을 때는 `verify_periods.py --audit-interrupted`로 먼저 대조한다.
`run_periods.py --resume-interrupted`는 기록되지 않은 예매가 없고 해당 미완료 방문의
예매가 아직 생성되지 않은 경우에만 남은 행동을 이어간다. 예매가 이미 생성됐다면
자동으로 반복하지 않고 중단한다.

## 부하 테스트는 별도인가

사용자 수, 누적 방문 횟수, 동시 접속 수는 다르다.
이번 추가 방문은 일반 행동 데이터를 만드는 작업이며 대규모 부하 테스트가 아니다.
`load_scenarios.json`에는 콘서트·야구 단일 공연에 요청이 몰리는 시나리오와
동일 요청 키의 중복 예매 방지 검사 등을 준비했다. 실제 부하는 나중에 대상·동시 사용자 수·
시간·쓰기 범위를 정한 뒤 실행한다. 현재는 개별 좌석 재고/홀드 모델이 없으므로
실제 좌석 선점·초과 판매 방지를 검증했다고 해석하면 안 된다.

## 최초 실행 결과와 한계

최초 100명 실행은 방문 202회, 찜 140건, 예매 57건, 모의 결제 완료 49건,
결제 대기 8건, MongoDB 로그 2,404건으로 DB 대조를 마쳤다.
초기 전송 문제로 가입 이벤트 1건과 찜 추가 이벤트 1건은 누락된 이력을 남겼고 소급 생성하지 않았다.
추가 방문 결과는 이 수치에 더해지며, 최종 검증 전에는 완료로 보지 않는다.

## 추가 방문 최종 결과

실행 ID는 `persona-periods-20261106`이며, **2026-11-06 17:17:49 한국 시간**에
최종 DB 대조를 통과했다. 기존 계정 100명을 재사용했고 신규 회원은 0명이다.

| 항목 | 추가 생성 결과 |
| --- | ---: |
| 무작위 방문 | 1,000회 (사용자별 2~23회) |
| 검증된 공연 조회 | 2,018건 |
| MariaDB 찜 증가 | 642건 |
| 예매 | 297건 |
| 모의 결제 완료 | 242건 |
| 결제 대기/이탈 | 55건 |
| MongoDB 추가 행동 로그 | 9,709건 |
| 가상 분석 날짜 | 2026-10-08 ~ 2026-11-06, 30일 |
| 기존 MongoDB `events`로 유입 | 0건 |

실제 이벤트와 회원·방문·예매·결제 ID, 전체 요청 내용, 금액을 대조했다.
기존 57건의 예매·결제 전체 컬럼과 원본 계정 상태 파일도 보존했다.
가상 일별 모의 매출 합계는 실제 새 모의 결제 금액 합계와 일치한다.
최종 테스트는 단위/오프라인 브라우저 26개가 통과했다.

분석 파일은 `artifacts/persona-periods-20261106/`의 `daily.csv`(30일),
`weekly.csv`(주별), `monthly.csv`(월별), `analytics.json`에 있다.
`verification-periods.json`에는 실제 DB 대조 결과, `daily-query.json`에는
Compass Aggregations용 조회 파이프라인이 있다. 월별 집계는 30일 창에 포함된
부분 기간의 값이므로 완전한 두 달을 비교하는 데이터로 해석하지 않는다.

### 중단 이력의 해석

방문 분포 변경을 위해 실행을 멈춘 순간에 MariaDB에만 남은 찜 1건과 조회 1건이 있다.
따라서 추가 `favorite_add` 로그는 641건, MariaDB 찜 증가는 642건이며,
MariaDB 조회 업무 이벤트 증가분은 2,019건, 완료 방문의 MongoDB 조회는 2,018건이다.
중단 전후의 실제 데이터를 삭제하거나 빠진 과거 로그를 소급 생성하지 않았다.
복구 재로그인 등으로 로그인 수는 1,001건이며, 분석 방문 수는 고유 방문 ID 기준 1,000회다.
이 차이는 명시적으로 보존한 중단 이력이며, 완료 방문의 예매·결제 연결 검증은 통과했다.

프로젝트 루트 `.gitignore`와 이 안내 문서의 이동·통합은 사용자 요청으로 변경했다.
실행 중 사용자가 커밋한 루트 README와 `docs/FrontToBackSetting.md` 변경도 보존했다.
부하 테스트는 시나리오 준비 단계이며 아직 실행하지 않았다.

커밋 시 `artifacts/`, `.venv/`, 캐시는 제외된다. 루트 `.gitignore`와
`syntheticData/playwright/`의 소스·안내·테스트 파일을 함께 포함하면 된다.

추천 커밋 메시지: `[feat] 페르소나 행동 자동화 및 기간별 분석 추가`

## 이전 설계·작업·실행 기록

아래는 통합 전 문서 원문이다. 작성 당시의 명령·횟수·상태를 보존한 기록이며,
특히 "모두 10회"는 변경 전 설정이다. 현재 정책은 이 문서 앞부분과 최신 실행 결과를 우선한다.



<a id="history-readme"></a>

<details>
<summary>README.md - original record</summary>

# 페르소나 브라우저 자동화

`../personas.json`을 읽어 **실제 화면**에서 테스트 계정 생성·로그인·조회·찜·
예매·모의 결제를 실행한다. 기존 소스·설정·입력 파일과 DB 스키마는 수정하지 않는다.
회원·찜·예매·모의 결제 데이터는 실제 서비스 DB에 추가된다.

## 데이터가 저장되는 곳

- **MariaDB:** 기존 `users`, `favorites`, `reservations`, `payments`, `events` 등.
  이메일은 `persona0001+synthetic@example.com`처럼 테스트용 별칭을 사용한다.
  이름·MBTI는 원본을 유지한다. `state.json`에 원본 페르소나 ID ↔ 회원 ID를 기록한다.
- **MongoDB:** 자동화 전용 backend가 `tikit.simulation`에 저장한다.
  첫 이벤트 저장 시 컬렉션이 생긴다. 100명이 끝나기 전에도 새 문서를 볼 수 있다.
- **합성 표시:** 실제 화면이 만든 tracking 요청의 `props`에 `synthetic: true`,
  `synthetic_run_id`, `synthetic_persona_id`, `synthetic_scenario`를 추가한다.
  API 계약 범위 안에서만 태그를 추가하고 응답은 실제 서버 응답을 그대로 사용한다.
- `artifacts/<run-id>/events.jsonl`에는 서버가 저장/중복 확인한 이벤트만 남긴다.
  `attempts.jsonl`은 전송 시도 기록이다. `verification-<count>.json`은 DB 직접 대조 결과다.

기존 `events` 컬렉션과 다른 곳에 저장하려면 **전용 backend 환경 변수**를 지정해야 한다.
실행 중인 원래 backend 설정을 바꾸거나 `.env`를 수정하지 않는다.
브라우저는 자동화 서버 `5174`를 사용하며 일반 개발 서버 `5173`과 구분한다.

## 설치

프로젝트 루트에서 새 폴더의 별도 가상환경에 설치한다.

```powershell
python -m venv syntheticData/playwright/.venv
syntheticData/playwright/.venv/Scripts/python.exe -m pip install -r syntheticData/playwright/requirements.txt
syntheticData/playwright/.venv/Scripts/python.exe -m playwright install chromium
```

Python 3.14 / Playwright 1.64.1에서 실행했다. MariaDB·MongoDB 직접 검증에는
기존 backend 의존성이 설치된 Python 환경을 사용한다.

## 전용 서버 시작

프로젝트 루트에서 관리용 launcher를 실행한다. 기본 backend Python은 루트의
`.venv/Scripts/python.exe`, Node는 PATH에서 찾는다. 다른 환경이면
`--backend-python`, `--node-executable`에 해당 머신의 실행 파일을 지정한다.
개인 실행 파일 경로를 공유 파일에 기록하지 않는다.

```powershell
python syntheticData/playwright/serve.py --run-id example-run
```

launcher는 기존 `backend/.env` 연결 설정을 사용하면서 전용 프로세스에만
컬렉션 `simulation`을 지정한다. backend 8001/frontend 5174를 함께 실행하며
Ctrl+C로 둘 다 종료한다. 기존 `.env`·소스·`vite.config.js`를 수정하지 않는다.

전용 backend는 실행별 키와 읽기 전용 확인 경로로 구분한다. 브라우저 실행기는
UI 조작 전에 실제 연결된 backend의 실행 ID·인스턴스 ID·컬렉션을 확인하고,
다른 서버이면 거절한다. 이 전용 포트는 자동화 브라우저용이며 일반 브라우저에서
API를 호출하면 403이다. 일반 수동 사용은 기존 5173 서버를 사용한다.
원래 서버 8000/5173이 실행 중이어도 다른 포트이므로 함께 사용할 수 있다.
`server.json`의 실행 키도 git에서 제외되므로 공유하지 않는다.

## 실행: 3명 검증 후 총 100명

아래 명령은 **프로젝트 루트**에서 실행한다. `verify.py`의 `python`은 backend
의존성이 설치된 인터프리터여야 한다. `run-id`는 두 단계에서 동일하게 사용한다.
아래 ID는 최초 실행 예시이며 새 데이터셋에는 새로운 ID를 사용한다.

```powershell
# DB 연결과 실제 제품/버전 확인 (읽기 전용)
python syntheticData/playwright/verify.py --preflight

# 테스트용 행동 계획을 파일로만 확인 (서비스 API 호출 없음)
syntheticData/playwright/.venv/Scripts/python.exe syntheticData/playwright/run.py --run-id example-run --plan-only

# 3명: 조회만 / 예매 확인에서 이탈 / 결제 완료 경로
syntheticData/playwright/.venv/Scripts/python.exe syntheticData/playwright/run.py --run-id example-run --count 3
python syntheticData/playwright/verify.py --run-id example-run --count 3

# 검증이 통과한 뒤 나머지 97명. 처음 3명의 완료한 방문은 건너뛴다.
syntheticData/playwright/.venv/Scripts/python.exe syntheticData/playwright/run.py --run-id example-run --count 100 --workers 3
python syntheticData/playwright/verify.py --run-id example-run --count 100
```

검증 성공 파일이 없으면 4명 이상 실행을 거절한다. `--headed`를 붙이면
브라우저 창을 보며 실행할 수 있다. 동시에 여러 터미널에서 같은 run-id를 실행하지 않는다.
실행 중 다른 프로세스가 같은 테스트 계정을 변경하지 않아야 한다.

## 행동 규칙

| 페르소나 설정 | 반영 방식 (가상의 테스트 규칙) |
| --- | --- |
| 카테고리 가중치 | 방문별 카테고리를 가중 추출한다. 상위 2개만 강제하지 않는다. |
| 관람 빈도 | occasional 1회, monthly 2회, frequent 3회 방문. 결제 완료 비중도 다르게 둔다. |
| 탐색 성향 | 이전에 조회한 작품 재방문 확률: familiar 80%, mixed 40%, adventurous 0%. 같은 카테고리에 조회 이력이 있을 때 적용한다. |
| 동반 유형 | solo 1매, partner 2매, friends/family 2~4매. |
| MBTI | 계정 정보와 분석 기준으로만 사용하며 취향·전환율을 고정하지 않는다. |

방문마다 상세 1~3개를 조회한다. 조회만, 찜 후 이탈, 예매 확인 단계 이탈,
예매 후 결제 전 이탈, 결제 완료 경로를 섞는다. 첫 3명은 경로 검증을 위해
각각 조회만/예매 확인 이탈/결제 완료로 고정하며 해당 사용자의 모든 방문에 적용한다.
이 예외도 실행 계획에 기록한다. 사용자별 컨텍스트를 격리하고 방문마다 새 탭을 연다.
같은 사용자 브라우저 ID는 유지하고, 탭의 세션 ID는 새로 생성된다.

**모든 행동은 실행 시점에 발생한다.** 1~3회 방문은 속성에 따른 테스트 횟수이며,
실제 한 달이나 몇 달이 경과했다는 뜻이 아니다. 과거 시각을 만들어 넣지 않는다.
계획은 시드로 재현되지만 인기순 목록·공연 데이터·실행 시각이 바뀌면 실제 작품과
UUID·결과는 달라질 수 있다. 원본 입력 파일의 해시로 재개 시 변경을 감지한다.

## 재실행과 비밀값

- 비밀번호는 run-id별 난수를 사용하며 git에서 제외한 `artifacts/<run-id>/state.json`에만 보관한다.
  동일 실행 재개 시 이 값을 재사용한다. 이 파일을 공유하거나 커밋하지 않는다.
- 토큰과 비밀번호를 이벤트·요약에 출력하지 않는다. trace/HAR도 저장하지 않는다.
- 동일 이메일이 이미 존재하면 동일 자격 증명으로 로그인을 시도하고 이름·MBTI·동의를
  확인한다. 비밀번호가 다르면 중단하며 기존 계정을 변경하거나 삭제하지 않는다.
  새로운 run-id는 새 비밀번호를 만들기 때문에 기존 별칭 계정과 충돌할 수 있다.
  기존 캠페인을 이어갈 때는 원래 run-id·state를 사용한다.
- 완료한 방문은 건너뛴다. 예매 응답 ID는 결제 전에 체크포인트에 저장한다.
- 중간 실패/프로세스 종료로 상태가 `failed` 또는 `in_progress`이면 자동으로 재실행하지 않는다.
  실제 DB와 전송 기록을 확인한 뒤 복구해야 한다. 상태 파일을 지우고 무작정 재시도하지 않는다.
- 한 사용자가 실패하면 대기 중 사용자는 시작하지 않고 이미 진행 중인 사용자만 마무리한다.
  타이머가 이미 큐에서 꺼낸 로그도 브라우저 fetch 완료까지 기다린 뒤 탭을 닫는다.
- 모의 결제이므로 실제 청구는 없지만 테스트 계정 활동도 서비스 인기순 집계에 영향을 준다.
  분석 시 `+synthetic@example.com` 회원과 MongoDB 합성 태그를 기준으로 구분한다.
- 이 도구는 기존 데이터를 삭제하지 않는다.

## 검증과 결과

```powershell
syntheticData/playwright/.venv/Scripts/python.exe -m unittest discover -s syntheticData/playwright -p "test_*.py"
```

단위 테스트는 계획의 재현성·가중치·스타일·태그 제약·재개 거절, 실패 시 작업 중단,
비밀번호 가림, 임시 파일 잠금 재시도를 검사한다. 오프라인 브라우저 테스트는
로그 큐가 이미 비워진 상황에서도 전송 중인 fetch를 기다리는지 검사한다.
`verify.py`는 MariaDB 실제 계정/찜/예매/결제와 MongoDB 실제 이벤트 ID·사용자 연결·태그를
대조하며 기존 `events`에 실행 ID가 섞이지 않았는지 확인한다.
최초 작업 시 기록한 기존 파일 해시가 있으면 그 보존 여부도 검사한다.
최종 수치는 [RESULTS.md](#history-results)에 기록한다.

## 중단 이후 복구

실행기를 멈춘 상태에서만 다음을 수행한다. DB를 읽어 상태 파일의 예매 ID·결제
상태와 대조한 뒤 복구 계획을 만든다. 알 수 없는 예매·결제 변경이 있으면 중단한다.

```powershell
python syntheticData/playwright/audit.py --run-id example-run
syntheticData/playwright/.venv/Scripts/python.exe syntheticData/playwright/recover.py --run-id example-run
```

복구는 완전히 끝난 방문의 상태만 확정하거나, 실제 로그인·로그아웃, 예매를
생성하지 않는 조회/예매 확인 단계 이탈만 다시 수행한다. 예매·결제 생성은
재실행하지 않는다. 기존 방문과 전송 기록은 `recovery-history.jsonl`에 보존한다.
실제로 다시 실행한 행동은 새로운 현재 시각으로 저장한다. 로그아웃 보완 시
기존 세션 ID를 복원하므로 같은 세션에 추가 로그인·로그아웃이 생길 수 있다.
데이터를 삭제하거나 과거 시각으로 로그를 삽입하지 않는다.

Playwright 요청 관찰·변경 방법은 [공식 문서](https://playwright.dev/python/docs/network)를 따른다.


</details>


<a id="history-design"></a>

<details>
<summary>DESIGN.md - original record</summary>

# 페르소나 브라우저 자동화

기존 파일을 수정하지 않고 이 폴더에만 파일을 추가한다. 입력은
`../personas.json`이며 Playwright Python으로 실제 회원가입·로그인·조회·찜·
예매·모의 결제를 실행한다. 사용자가 요청한 순서는 3명 검증 후 총 100명이다.
컬렉션 이름은 사용자 최종 지정인 `simulation`을 사용한다.

## 방식과 범위

- 파일로 가상 이벤트만 생성하는 방식과 API 직접 호출 방식 대신, 사용자가 선택한
  실제 UI 조작 방식을 사용한다. DB는 검증 시 읽기만 하며 쓰기는 서비스 API가 한다.
- 별도 프로세스 환경 변수로 자동화 서버(backend 8001/frontend 5174)를 실행한다.
  기존 `.env`·소스·기존 서버를 수정하지 않고 MongoDB 컬렉션만 `simulation`으로 분리한다.
- 가입 이름·MBTI는 원본 그대로, 이메일은 `+synthetic` 별칭으로 구분한다.
  원본 ID·이메일 ↔ 실제 회원 ID·이메일 매핑을 실행 기록에 남긴다.
- 비밀번호는 실행별 난수를 만들어 git에서 제외한 로컬 상태에만 보관한다.
  토큰·비밀번호를 로그, 결과 보고서, 스크린샷에 기록하지 않는다.
- 회원별 독립 브라우저 컨텍스트와 브라우저 UUID를 사용한다. 관람 빈도는
  1/2/3회 방문이라는 테스트 규칙에 반영한다. 실제 관측 분포라고 주장하지 않는다.
- 카테고리는 원본 가중치로 추출하고, 작품 탐색 성향은 이전 조회 작품 재방문
  확률에 반영한다. 동반 유형은 1~4매 범위의 수량 분포에 반영한다.
- 조회만, 찜, 예매 확인 단계 이탈, 결제 전 이탈, 결제 완료 경로를 포함한다.
  첫 3명은 조회만/예매 확인 이탈/결제 완료 경로로 고정해 커버리지를 확보한다.
- 실제 tracker가 만든 요청에만 합성 여부·실행 ID·페르소나 ID·시나리오를
  props로 추가한다. 이벤트를 날조하거나 앱 코드를 바꾸지 않는다.
- 계정·세션별 체크포인트를 저장한다. 중단된 세션은 자동 재실행하지 않고
  보고해 예매 중복 생성을 피한다. 완료한 세션은 재실행하지 않는다.
- 3명 실행 후 MariaDB 계정·찜·예매·결제와 MongoDB 원본 이벤트 ID를 대조한다.
  검증이 통과한 경우에만 나머지 97명을 진행한다. 실패 시 즉시 중단한다.
- 실시간으로 실행하며 과거 날짜의 활동을 조작하지 않는다. 합성 계정 활동은
  기존 인기순 집계에도 영향을 주므로 분석 시 테스트 계정을 제외해야 한다.

## 실행 안전성

실행 전 backend read-only preflight로 DB 버전·대상 컬렉션을 확인한다.
`events`에는 쓰지 않고 `simulation`을 명시한 전용 backend만 사용한다.
입력 파일 SHA-256과 실행 설정을 보관하고 재개 시 일치를 확인한다.
산출물은 `artifacts/`에 두며 신규 코드만 버전 관리 대상으로 둔다.

Context7 도구가 현재 세션에 없어 Playwright 공식 Python 문서를 사용했다.
https://playwright.dev/python/docs/network
https://playwright.dev/python/docs/api/class-route


</details>


<a id="history-plan"></a>

<details>
<summary>PLAN.md - original record</summary>

# Persona Browser Automation Implementation Plan

> **For agentic workers:** Use executing-plans to implement this plan task-by-task.

**Goal:** 기존 파일 변경 없이 100명 페르소나의 실제 UI 행동과 DB 저장을 검증한다.
**Architecture:** 결정적 행동 계획 → 격리된 브라우저 UI 실행 → 읽기 전용 DB 대조.
**Tech Stack:** Python 표준 라이브러리, Playwright 1.64.1, 기존 backend DB 드라이버.
**Spec:** `DESIGN.md`

## Global Constraints

모든 신규 파일은 이 폴더 안에 둔다. MongoDB 컬렉션은 `simulation`이다.
기존 파일·DB 스키마 수정, 수동 이벤트 삽입, 커밋·푸시는 하지 않는다.
실제 서비스 동작 실행은 사용자 요청으로 승인되었다. 현 작업 디렉터리에서
실행하고 별도 worktree를 만들지 않는다. 먼저 3명 검증, 이후 동일 실행을 100명으로 확대한다.

## Review Focus

계정 충돌, 부분 실패 후 중복 예매, tracker 전송 실패, 원본/계정 ID 혼동,
잘못된 컬렉션 저장을 확인한다. 상태의 계정/세션 기록은 토큰을 포함하지 않는다.

### Task 1: 결정적 계획과 데이터 구분

- [x] `test_scenarios.py`에 이메일 구분·카테고리 가중치·스타일 반영·시드 재현성·
  3명 커버리지·100명 확대 안정성·props 제약·재개 검증 테스트 작성 후 실패 확인.
- [x] `scenarios.py` 구현 후 테스트 통과 (8 tests, RED→GREEN).
- Interfaces: `build_plan(users, seed)`, `tag_events(events, tags)`, `check_resume(state, fingerprint)`.

### Task 2: 실제 UI 자동화와 재개 기록

- [x] `run.py`에 가입/로그인, 격리 컨텍스트, 실제 UI 탐색과 전환, tracker 확인,
  세션 체크포인트, 계정 매핑, 실패 캡처 구현.
- [x] 새 폴더의 독립 venv에 requirements 설치. 실제 서버 8001/5174 실행.
- [x] 3명 실행 시 요청 상태·로그 accepted 응답을 검증.
- Interfaces: `artifacts/<run-id>/state.json`, `events.jsonl`, `summary.json`.

### Task 3: DB 검증과 100명 확대

- [x] `verify.py`가 기존 backend 설정으로 DB를 읽고 회원·찜·예매·결제와
  MongoDB 이벤트 ID·합성 태그·user_id·컬렉션을 대조하도록 구현.
- [x] 3명 검증 통과 후 검증 결과를 gate로 사용해 count 100 실행 (진행 중).
- [x] 최종 DB 검증·기존 파일 해시 대조·독립 코드 리뷰.
- [x] `README.md`와 비밀값 없는 `RESULTS.md`에 실행 방법·실제 결과 기록.

## Ledger

- 사용자가 Playwright, 폴더 위치, 3명→100명 실행, DB 쓰기, 컬렉션 이름을 지정했다.
- Ruling: 기존 파일 보존을 위해 실행용 환경·산출물·계획도 이 폴더에만 둔다.
- Ruling: 실제 고객과 구분하기 위해 원본 이메일에 `+synthetic` 별칭을 사용한다.
- Ruling: mocks는 실제 DB 저장 검증 목적에 맞지 않아 live 환경을 사용한다.
- Task 1 complete: 8 unit tests passed after observed RED; original profile file not modified.
- Task 2 complete: live pilot 3 users/5 sessions, 7 views/3 reservations/3 payments, Mongo 62 events.
- Task 3 pilot gate: direct DB verification passed, original events leakage 0, existing 213 file hashes match.
- User pause: generation and dedicated servers stopped; 76 mapped accounts, 142 complete visits,
  1 failed checkpoint (temporary Windows lock), 2 interrupted visits. Existing data preserved.
- Final review identified queued work continuing after failure, password text in exceptions,
  insufficient event payload checks, and no browser-backend identity guard. All are included in
  the fix pass with offline tests; transport completion race was reproduced and covered by an offline browser test.
- Fix pass: 16 tests green, including failed work scheduling, secret redaction, atomic save retry,
  payload/visit validation, server identity, and the automatic-flush transport race.
- Ruling: recovery audits all reservation IDs/payment statuses before touching state. Missing logout
  is completed through UI; two lost browse visits replay only non-purchase actions; original evidence
  retained. Interrupted visits with no DB side effects can be reset. No reservation/payment is replayed.
- Recovery complete: 29 actions (24 auth finish, 2 browse replay, 1 checkpoint reconcile, 2 unstarted reset),
  read-only audit had zero blocked/unknown reservation side effects.
- Final: replay kept a previous favorite in MariaDB but initially dropped it from checkpoint evidence.
  Added retained-favorites regression (RED→GREEN), reconciled from preserved recovery history with no DB writes.
- Final verification passed: 100 users / 202 visits / 140 favorites / 57 reservations /
  49 completed + 8 pending payments / 2404 Mongo events / 0 original-collection leakage.
- Final suite: 17 passed; Postman guarded-server tests: 2 passed, exit 0.
- Ruling: initial missing signup/favorite log (one each) is documented, not backdated or fabricated.
  SQL contains 405 actual view events including interruptions/retries; verified visit Mongo views are 399.


</details>


<a id="history-results"></a>

<details>
<summary>RESULTS.md - original record</summary>

# 실행 결과

실행 ID: `persona-20261106` / 입력 시드: `42`

2026-11-06에 실제 Playwright 브라우저로 실행했다. 최초 3명의 DB 검증 통과 후
100명으로 확대했고, 사용자 요청으로 중단했다가 기존 상태를 대조한 후 재개했다.
최종 DB 검증 시각은 **2026-11-06 15:19:55 한국 시간**
(`2026-11-06T06:19:55Z`)이다. 시간대 표시를 바꾸기 위해 저장값을 수정하지 않았다.

## 실제 저장 결과

| 항목 | 결과 |
| --- | ---: |
| 원본 페르소나와 연결된 테스트 계정 | 100명 |
| 계획된 방문 완료 | 202회 |
| 완료 방문의 공연 조회 | 399건 |
| MariaDB에 남은 찜 | 140건 |
| MariaDB 예매 | 57건 |
| 모의 결제 완료 | 49건 |
| 결제 대기 (예매 후 이탈) | 8건 |
| MongoDB `tikit.simulation` 이벤트 | 2,404건 |
| 기존 MongoDB `events`에 저장된 이 실행의 로그 | 0건 |

MariaDB는 `10.11.14-MariaDB`이다. 이름·MBTI는 원본 프로필과 일치하며
이메일만 `persona0001+synthetic@example.com` 형태로 구분했다.

| 방문 결과 | 횟수 |
| --- | ---: |
| 조회 후 이탈 | 58 |
| 찜 후 이탈 | 43 |
| 예매 확인 단계에서 이탈 | 44 |
| 예매 후 결제 전에 이탈 | 8 |
| 모의 결제 완료 | 49 |

최초 3명 검증은 5회 방문, 조회 7건, 찜 3건, 모의 결제 3건,
MongoDB 이벤트 62건으로 통과했다. 첫 3명은 경로 검증용으로 결과를 고정했고
나머지는 취향·관람 스타일에 따른 결정적 난수 규칙을 적용했다.

## 확인한 내용

- 사용자 100명의 원본 이름·MBTI·동의·실제 회원 ID 연결
- 계정별 찜 및 예매 ID, 수량, 예매 상태와 결제 상태·금액
- 완료 방문의 조회 작품·카테고리·조회 수와 행동 이벤트 내용의 일치
- 예매 요청·결제 이벤트의 실제 예매 ID 연결
- 전송한 이벤트와 MongoDB 문서의 ID·발생 시각·페이지·props·스키마 버전 일치
- 사용자별 브라우저 ID, 방문별 세션 ID, 합성 태그와 회원 ID의 일치
- 기존 MongoDB `events`로 이 실행의 로그가 유입되지 않았음
- 기존 추적 파일 213개의 SHA-256이 작업 전과 일치함. 새 파일은 이 폴더에만 추가함
- 최종 단위/오프라인 브라우저 테스트 17개 통과
- Postman CLI로 전용 서버 식별·컬렉션 확인 테스트 2개 통과 (exit 0)
- 실행별 키 없이 전용 API에 접근하면 backend/frontend 양쪽 모두 403

세부 증거는 git에서 제외한 `artifacts/persona-20261106/`의
`verification-100.json`, `summary-100.json`, `events.jsonl`, `postman-guard.log`에 있다.
`state.json`과 `server.json`에는 테스트 자격 증명이 있으므로 공유하지 않는다.

## 중단·복구 이력과 해석상의 한계

초기 확대 실행에서 빠른 탭 종료가 전송 완료보다 먼저 일어나는 문제를 발견했다.
브라우저 fetch를 직접 관찰해 전송 완료까지 기다리도록 수정했고 오프라인
브라우저 회귀 테스트로 검증했다. Windows 임시 파일 잠금도 재시도하도록 보완했다.

중단 당시 76명의 계정, 완료 처리 142회, 체크포인트 실패 1회, 진행 중 2회였다.
실제 예매 ID·결제 상태를 대조하고 다음 29건을 복구했다.

- 로그아웃 누락 24회는 기존 세션을 복원해 실제 로그인·로그아웃으로 보완
- 조회 로그 누락 2회는 예매 생성 없는 탐색/예매 확인 이탈 행동만 재실행
- 완료 증거가 있는 체크포인트 실패 1회는 상태만 확정
- 예약 부작용이 없는 미완료 방문 2회는 원래 계획으로 재개

예매·결제는 복구 과정에서 재실행하거나 삭제하지 않았다. 복구 전에 남아 있던
찜은 그대로 보존했고 이력에 근거해 상태 기록에도 합산했다.

**초기 전송 수정 전의 가입 이벤트 1건, 찜 추가 이벤트 1건은 누락된 채로 남았다.**
실제 계정은 100개지만 `sign_up` 이벤트는 99건, 실제 찜은 140건이지만
`favorite_add` 이벤트는 139건이다. 과거 행동 로그를 날조하거나 계정을 삭제·재가입해
건수를 맞추지 않았다. 복구 때 재로그인 등이 추가돼 로그인·페이지 조회 이벤트는
계획 방문 수보다 많다. MariaDB의 `performance_view`는 중단·재시도 중 실제 발생한
조회도 포함해 405건이며, 검증된 202회 방문의 MongoDB 조회 로그는 399건이다.

따라서 이 실행은 202회 완료 방문의 취향·전환 흐름과 저장 경로를 검증하는 데이터이며,
최초 중단 전까지의 모든 원시 행동을 빠짐없이 보존한 이력이라고 해석해서는 안 된다.
실제 사용자 취향·추천 정확도·장기간 방문 빈도를 입증하는 데이터도 아니다.

코드 리뷰에서 지적된 실패 후 대기 작업 실행, 예외의 비밀번호 노출 가능성,
로그 내용 검증 부족, 저장 대상 식별 부족은 테스트와 함께 수정했다.


</details>


<a id="history-periods"></a>

<details>
<summary>PERIODS.md - original record</summary>

# 추가 방문과 기간별 분석

## 실행 범위

사용자가 지정한 기존 100명에게 **각 10회, 총 1,000회 추가 방문**을 생성한다.
신규 회원가입은 하지 않는다. 원본 페르소나의 이름·MBTI와 기존 회원 ID·비밀번호를
기존 로컬 실행 기록에서 재사용한다. 기존 파일·원본 로그·MariaDB 날짜를 수정하지 않는다.

현재 시점에서 과거 30일에 해당하는 가상 분석 기간을 기본으로 사용한다.
이는 실제 30일 동안 관측한 데이터가 아니라 테스트용 시간축이다.

| 필드 | 의미 |
| --- | --- |
| `occurred_at`, `received_at` | 실제 브라우저 동작·서버 수신 시각. 변경하지 않는다. |
| `props.simulation_at` | 해당 행동의 분석용 가상 시각, UTC ISO 문자열 |
| `props.simulation_at_kst` | 같은 가상 시각의 한국 시간 문자열 |
| `props.simulation_date` | 한국 시간 기준 가상 분석 일자 `YYYY-MM-DD` |
| `props.synthetic_visit_id` | 기간별 방문을 식별하는 고유 ID |

이 필드는 실제 tracker가 만든 요청에만 추가하며 MongoDB `tikit.simulation`에 저장한다.
MariaDB 거래는 실제 현재 시각에 생성한다. 기간별 매출·전환 분석은 MongoDB의
가상 날짜와 실제 예매 ID를 연결해 수행하고, MariaDB `created_at`과 혼동하지 않는다.

## 행동 규칙

100명 모두 방문 수는 10회로 맞춘다. 이는 방문별 비교를 위한 테스트 횟수이며
실제 관람 빈도의 통계가 아니다. 개인의 카테고리 가중치·탐색 성향·동반 유형은
기존 브라우저 동작에 반영하고, 관람 빈도 설정은 경로 전환 가중치에 사용한다.
방문 날짜는 사용자별로 30일 중 10일을 시드로 추출하고 시간순으로 실행한다.
조회만·찜·예매 확인 이탈·결제 전 이탈·모의 결제 경로를 포함한다.

## 구현/검증 계획

1. `periods.py`의 재현 가능한 방문 일정·가상 시각 태그·기간 집계를 테스트 먼저 작성한다.
2. `run_periods.py`에서 기존 UI 실행기를 확장한다. 기존 소스 파일은 수정하지 않는다.
3. 기존 계정·찜·예매를 읽기 전용으로 스냅샷하고 3명×1회 시험 실행을 검증한다.
4. 검증 통과 후 같은 실행 ID로 100명×10회를 마무리한다. 완료 방문은 건너뛴다.
5. 모든 이벤트와 실제 회원·예매·결제를 대조하고 일별·주별·월별 CSV를 저장한다.
6. 1,000회 완료, 신규 회원 0명, 기존 `events` 유입 0건, 기존 파일 보존을 확인한다.

실행 산출물과 자격 증명은 git에서 제외한 `artifacts/<run-id>/`에 둔다.
같은 실행을 여러 프로세스에서 동시에 실행하지 않는다. 중간 실패한 방문은
기존 실행기와 동일하게 자동 재시도하지 않고 실제 DB부터 대조한다.

## 나중에 할 부하 테스트

지금은 브라우저 4개 이하로 일반 데이터를 생성한다. 대규모 동시 접속은 실행하지 않는다.
`load_scenarios.json`에는 콘서트·야구 단일 공연에 트래픽을 집중하는 후속 시나리오를 둔다.
실행 전에 대상 서버, 동시 사용자 수, 지속 시간, 쓰기 범위를 정한다.
측정 항목은 p95/p99 지연, 오류율, RPS, DB 연결·CPU, 로그 유실·중복, 중복 예매 요청 처리다.
현 모델은 좌석 등급과 수량을 관리하지만 개별 좌석 재고/홀드 모델은 없으므로
현재 코드만으로 실제 좌석 선점·초과 판매 방지 성능을 검증했다고 주장하지 않는다.

## 작업 기록

- 사용자 지정: 기존 100명만 사용, 각 추가 방문 10회. 사용자 증가는 후속 작업.
- 구현 선택: 실제 시각은 보존하고 분석용 시간축을 별도 props로 제공.
- 구현 선택: 기존 계정/예매와 원본 파일을 보존하기 위해 기존 실행기를 상속하는 새 파일만 추가.
- 3명×1회 시험 통과: 신규 회원 0명, 조회 6건, 예매/모의 결제 1건, MongoDB 이벤트 30건.
- 리뷰 보완: 기존 예매·결제의 전체 컬럼 스냅샷, MongoDB 금액과 MariaDB 대조,
  기간별 매출 합계 대조, 원본 계정 상태 파일 SHA-256 보존 검사.
- 최초 시험 이후 기존 57건 거래의 알려진 금액/회원/결제 상태가 그대로임을 확인하고
  전체 컬럼 스냅샷으로 증거를 보강했다. 기존 거래를 수정한 DB 요청은 없다.
- 실행 중 README의 WBS/ERD 변경은 사용자 Git 커밋으로 확인했다. 해당 문서는
  사용자의 최신 커밋과 같은 경우 보존된 외부 변경으로 기록하며 덮어쓰지 않는다.

## 실행 방법

프로젝트 루트 기준이다. DB 검증에는 기존 backend 의존성이 있는 Python을 사용한다.
`run_periods.py`는 새 폴더의 Playwright 가상환경에서 실행한다.
한 캠페인은 같은 `run-id`, `start`, `days`, `visits`, `seed`로 재개해야 한다.

```powershell
# 기존 계정 기록을 읽고 새 일정만 준비 (회원가입/행동 없음)
syntheticData/playwright/.venv/Scripts/python.exe syntheticData/playwright/run_periods.py --run-id persona-periods-20261106 --source-run persona-20261106 --start 2026-10-08 --days 30 --visits 10 --plan-only

# 최초 한 번, DB와 기존 파일 보존 기준 스냅샷
python syntheticData/playwright/verify_periods.py --run-id persona-periods-20261106 --baseline

# 별도 터미널에서 전용 서버 유지. 설치 환경에 따라 Node/Python 실행 파일 옵션 지정 가능
python syntheticData/playwright/serve.py --run-id persona-periods-20261106

# 기존 계정 3명 × 첫 방문 1회
syntheticData/playwright/.venv/Scripts/python.exe syntheticData/playwright/run_periods.py --run-id persona-periods-20261106 --start 2026-10-08 --pilot --workers 1
python syntheticData/playwright/verify_periods.py --run-id persona-periods-20261106 --pilot

# 시험 방문을 재실행하지 않고 총 100명 × 10회까지 확대
syntheticData/playwright/.venv/Scripts/python.exe syntheticData/playwright/run_periods.py --run-id persona-periods-20261106 --start 2026-10-08 --workers 4
python syntheticData/playwright/verify_periods.py --run-id persona-periods-20261106
```

위 ID는 이번 실행 기록이다. 이미 완료한 캠페인을 재실행하면 추가 예매 없이
완료 방문을 건너뛴다. 다른 실행 ID를 사용하면 같은 계정에 새 방문을 더 만드는
별도 캠페인이 된다. 방문이 실패/중단된 경우 먼저 DB와 상태를 대조해야 한다.

## 분석 결과 파일과 조회

최종 검증 시 `artifacts/<run-id>/`에 다음을 생성한다.

- `daily.csv`: 한국 시간 가상 일별 방문·사용자·재방문자·조회·찜·예매·결제·매출
- `weekly.csv`, `monthly.csv`: 주별/월별 집계. 사용자와 방문은 각 구간 내 고유 수
- `analytics.json`: 세 집계의 원본 데이터
- `daily-query.json`: MongoDB Compass Aggregations에 붙여 넣을 수 있는 파이프라인
- `verification-periods.json`: 실제 계정·DB 거래·로그·분석 금액 대조 결과

Documents의 Filter에서 이번 추가 방문만 조회하려면:

```json
{"props.synthetic_run_id":"persona-periods-20261106"}
```

가상 분석 날짜 한 날만 조회하려면:

```json
{
  "props.synthetic_run_id":"persona-periods-20261106",
  "props.simulation_date":"2026-10-08"
}
```

`props.simulation_at_kst`를 펼치면 해당 새 문서에서 가상 한국 시간을 볼 수 있다.
과거의 기존 문서에는 새 필드를 추가하지 않는다. 실제 저장 시각과 가상 분석
시각을 비교할 때는 이름을 구분해야 한다. `new_in_period_users`는 이번 가상 기간에
처음 등장한 사용자이며, 실제 신규 가입자 수가 아니다. 모의 매출은 실제 매출이 아니다.


</details>
