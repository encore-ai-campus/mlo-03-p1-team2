# 사용자 행동 생성·부하 테스트 안내

현재 사용법, 파일 역할, 과거 실행 결과를 이 문서에서 관리한다.
부하 조건·시나리오는 [부하 테스트 계획](loadTestPlan.md),
최신 실측 결과는 [부하 테스트 결과](loadTestResult.md)를 기준으로 한다.

## 현재 상태와 저장 위치

- `../syntheticData/personas.json`에는 기존 100명을 보존한 총 300명의 프로필이 있다.
- API 부하 테스트는 실제로 실행됐으며, `load-20261106-prepare` 실행은
  `mixed-200` 단계의 API별 임계값 초과로 중단됐다. 상세 수치는 결과 문서에 있다.
- 신규 행동 로그 저장 위치는 MongoDB `tikit.events`다. `event` 단수가 아니다.
- 최초 100명 및 추가 방문의 과거 행동 로그는 `tikit.simulation`에 보존한다.
  신규 저장 위치 변경은 기존 데이터의 이동·삭제를 뜻하지 않는다.
- 회원·찜·예매·모의 결제·업무 이벤트는 MariaDB에 있다.
  MongoDB 컬렉션을 지워도 회원이 지워지지는 않지만 과거 행동 분석 근거가 사라진다.

| 용도 | 저장소·기록 | 관리 원칙 |
| --- | --- | --- |
| 현재 API 부하 및 신규 브라우저 행동 로그 | MongoDB `tikit.events` | 합성 표시와 실행 ID로 실제 사용자 로그와 구분 |
| 과거 최초 100명·기간별 방문 로그 | MongoDB `tikit.simulation` | 보존. 기존 실행 검증은 저장된 컬렉션을 읽음 |
| 회원·찜·예매·모의 결제·업무 이벤트 | MariaDB | 기존 계정·거래 보존 |
| 상태·계정 매핑·입력 스냅샷·검증·집계 | `artifacts/<run-id>/` | 재개와 검증에 필요하므로 보존 |

현재 API 실행기는 backend의 `MONGODB_EVENTS_COLLECTION` 설정을 따른다.
`events`로 설정하고 대상 서버도 같은 컬렉션을 사용하는지 실행 전에 확인한다.
브라우저 전용 서버 `../syntheticData/playwright/serve.py`는 신규 쓰기를 `events`로 지정한다.
`simulationApp.py`라는 파일명과 `/simulation-check` 경로는 자동화 서버의 식별용으로
유지하며, 저장 컬렉션은 `events`다.

과거 `simulation` 실행 ID를 신규 `events` 실행에 재사용하지 않는다.
브라우저 실행기는 컬렉션이 바뀐 실행의 재개를 거절한다. 새 실행 ID를 사용하고,
기존 계정을 다시 가입시키지 않도록 최초 가입 실행과 기존 계정 추가 방문을 구분한다.
기존 데이터의 이동·삭제·신규 부하 실행은 이번 파일 정리에 포함하지 않는다.

## 파일 역할

| 파일 | 역할 |
| --- | --- |
| `../syntheticData/generatePersonas.py` | 프로필 생성·검증, 기존 프로필을 보존하는 `expand_personas()` |
| `../syntheticData/personas.json` | 300명 프로필. 프로필 존재와 실제 서비스 계정 존재는 별개 |
| `../syntheticData/testGeneratePersonas.py`, `../testExpandPersonas.py` | 이름·재현성·다양성·기존 100명 보존 검사 |
| `../syntheticData/playwright/loadTest.py` | API 부하 준비·단계 실행·재개·결과 보고 |
| `../syntheticData/playwright/loadClient.py` | HTTPX 요청·응답 검사·측정 |
| `../syntheticData/playwright/loadControl.py` | 쓰기 예산·응답시간·오류율·상태 저장 |
| `../syntheticData/playwright/loadDatabase.py` | DB 생성 건수·예매·결제 대조 |
| `../syntheticData/playwright/loadMonitoring.py` | Prometheus 지표·저장 공간·서버 재시작 감시 |
| `../syntheticData/playwright/loadPreparation.py` | 프로필 확장·과거 실행 입력 보존 |
| `../syntheticData/playwright/run.py` | 브라우저로 최초 가입·로그인·조회·찜·예매 |
| `../syntheticData/playwright/runPeriods.py` | 기존 100명 계정으로 추가 방문 생성. 신규 가입 없음 |
| `../syntheticData/playwright/serve.py`, `simulationApp.py` | 자동화 전용 backend 8001/frontend 5174 및 접근 키 검사 |
| `../syntheticData/playwright/scenarios.py` | 기본 행동 계획·합성 표시·입력 스냅샷·재개 조건 |
| `../syntheticData/playwright/periods.py` | 가상 날짜·방문 일정·일/주/월 집계 |
| `../syntheticData/playwright/safety.py` | 실패 중단·비밀값 가림·저장·서버 식별·과거 컬렉션 선택 |
| `../syntheticData/playwright/transport.py` | 브라우저가 닫히기 전 행동 로그 전송 완료 확인 |
| `../syntheticData/playwright/verify.py`, `verifyPeriods.py` | 실제 DB와 실행 증거 대조·집계 출력 |
| `../syntheticData/playwright/audit.py`, `recover.py` | 최초 브라우저 실행의 중단 감사·복구. 예매·결제 재생성 없음 |
| `testLoad*.py` | API 부하·예산·감시·준비·재개·로컬 API 통합 검사 |
| `../syntheticData/playwright/testScenarios.py`, `testPeriods.py`, `testSafety.py`, `testTransport.py` | 브라우저 행동 규칙·기간 집계·보호 동작·전송 검사 |
| `../backend/requirements.txt` | backend·API 부하·Playwright 공통 의존성 |

사용하지 않는 수동 전용 서버 검사는 제거했다.
별도 시나리오 제안 JSON은 제거하고 [계획의 요청 흐름·단계](loadTestPlan.md)에
통합했다. 실제 부하 단계는 `../syntheticData/playwright/loadTest.py`의 `stage_plan()`이 정의한다.
시나리오와 실행 상태를 여러 파일에 중복해서 기록하지 않는다.

## API 부하 준비·실행

저장소 루트에서 backend 의존성이 설치된 Python 환경을 사용한다.
설정·접근 정보는 로컬 환경에서 제공하며 공유 파일에 기록하지 않는다.

```powershell
$loadRunId = 'load-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
python -m syntheticData.playwright.loadTest --run-id $loadRunId
```

기본 모드는 프로필·기존 계정·API·DB·지표를 확인하는 준비 모드다.
신규 가입·예매·행동 로그 쓰기는 `--execute`를 붙였을 때만 수행한다.
실행 전 계획 문서의 대상·예산·중단·재개 조건을 확인한다.
한 서비스에는 한 담당자만 실행한다.

```powershell
python -m syntheticData.playwright.loadTest --run-id $loadRunId --execute
```

계정 상태 위치가 기본 경로와 다르면 `TIKIT_ACCOUNT_STATE`를 지정한다.
기존 실행을 재개할 때는 새 실행 명령 대신 계획 문서의 재개 절차를 따른다.

## 브라우저 도구 설치·사용

최초 계정 생성·추가 방문을 재현할 때만 사용한다. Python 패키지는 backend와 같은
환경에 설치하며, 이 폴더의 별도 `requirements.txt`는 공통 파일로 통합했다.
Chromium은 브라우저 도구를 사용할 때 설치한다.

```powershell
python -m pip install -r backend/requirements.txt
python -m playwright install chromium
```

전용 서버는 backend 의존성이 설치된 Python과 frontend 의존성을 사용한다.
필요하면 `../syntheticData/playwright/serve.py`의 `--backend-python`, `--node-executable`로 런타임을 지정한다.

```powershell
python syntheticData/playwright/serve.py --run-id example-new-events-run
```

계획 확인은 서비스에 행동을 보내지 않는다. 최초 가입 도구는 기존 100명 캠페인용이다.
이미 가입된 100명을 다시 만들기 위해 실행하지 않는다.

```powershell
python syntheticData/playwright/run.py --run-id example-new-events-run --plan-only
```

`../syntheticData/playwright/runPeriods.py`는 원본 100명 실행의 계정 상태와 `profiles-input.json`을 재사용한다.
새 실행 ID와 `--source-run`을 지정하고, 계획 → `verifyPeriods.py --baseline` →
전용 서버 → `--pilot` → 검증 → 전체 실행 순서로 사용한다.
인원은 100명으로 제한되며 현재 300명 JSON으로 원본 실행 입력을 덮어쓰지 않는다.
`audit.py`·`recover.py`는 최초 실행용이다. 기간별 실행에는
`verifyPeriods.py --audit-interrupted` 등 해당 실행의 별도 복구 절차를 사용한다.

`../syntheticData/playwright/verify.py`와 `verifyPeriods.py`는 실행 상태의 `fingerprint.collection`을 읽는다.
따라서 과거 실행은 `simulation`, 신규 실행은 `events`에서 검증한다.
검증 보고서·CSV는 로컬에 저장되지만 DB 데이터를 변경하지 않는다.
과거 검증의 파일 해시 검사는 당시 소스 보존까지 검사하므로 이번 정리 뒤에는
파일 변경을 보고할 수 있다. 이를 DB 데이터 손실로 해석하거나 과거 기준선을 덮어쓰지 않는다.

## 보존할 실행 기록과 정리 가능한 폴더

| 경로 | 의미·정리 기준 |
| --- | --- |
| `../.venv` | 과거 별도 Playwright 환경. 신규 설치는 backend 공통 환경 사용 |
| `__pycache__/`, 상위 폴더의 `__pycache__/` | Python 캐시. 삭제해도 실행 시 재생성 |
| `../syntheticData/playwright/artifacts/persona-20261106` | 최초 100명 가입·행동·계정 매핑·검증 |
| `../syntheticData/playwright/artifacts/persona-periods-20261106` | 기존 100명 추가 방문·가상 기간·집계·검증 |
| `../syntheticData/playwright/artifacts/load-20261106-preflight` | API 부하 사전 점검 기록 |
| `../syntheticData/playwright/artifacts/load-20261106-prepare` | 실제 API 부하 상태·공유 예산·중단·재개·측정 기록 |
| `../syntheticData/playwright/artifacts/baseline.json`, `documentation_consolidation.json` | 기존 파일 보존 기준·문서 통합 기록 |

`artifacts`는 통째로 삭제하지 않는다. `state.json`에는 계정 ID와 테스트 비밀번호,
`server.json`에는 접근 키가 있으므로 Git 커밋·공유 대상에서 제외한다.
`profiles-input.json`은 실행 당시 프로필, `plan.json`은 행동 계획,
`events.jsonl`·`attempts.jsonl`은 전송 증거다.
`period-baseline.json`은 기존 데이터·파일 보존 기준이고,
감사·복구 기록은 중단 시 실제로 남은 데이터와 체크포인트를 연결한다.
검증 JSON·집계 CSV·실행 로그도 실행 ID별로 보존한다.

## 과거 브라우저 실행 결과

아래는 `simulation`을 사용하던 2026-11-06 실행의 기록이다.
신규 `events` 부하 결과와 합쳐서 한 번의 실행처럼 해석하지 않는다.

| 항목 | 최초 `persona-20261106` | 추가 `persona-periods-20261106` |
| --- | ---: | ---: |
| 계정 | 최초 100명 | 같은 100명, 신규 가입 0명 |
| 완료 방문 | 202회 | 1,000회, 사용자별 2~23회 |
| 검증된 공연 조회 | 399건 | 2,018건 |
| MariaDB 찜 증가 | 140건 | 642건 |
| 예매 | 57건 | 297건 |
| 모의 결제 완료 | 49건 | 242건 |
| 결제 대기/이탈 | 8건 | 55건 |
| MongoDB 행동 로그 | 2,404건 | 9,709건 |
| 해당 실행의 `events` 유입 | 0건 | 0건 |

최초 실행은 전송 수정 전 가입 로그 1건·찜 추가 로그 1건이 누락된 이력을 보존했다.
실제 가입 100명에 `sign_up` 99건, 찜 140건에 `favorite_add` 139건이다.
중단·재시도 때문에 MariaDB 조회는 405건으로, 완료 방문의 MongoDB 조회 399건과 다르다.
예매·결제를 재생성하거나 과거 로그를 소급 생성해 건수를 맞추지 않았다.

추가 방문은 2026-11-06 17:17:49 KST에 최종 DB 대조를 통과했다.
중단 당시 MariaDB에만 남은 찜 1건·조회 1건을 보존했으므로
찜 추가 로그는 641건, MariaDB 조회 증가 2,019건이다.
복구 로그인 포함 로그인은 1,001건이며 고유 방문은 1,000회다.
기존 57건의 예매·결제와 원본 계정 상태를 보존하고, 새 결제 금액·로그를 대조했다.

추가 방문의 가상 분석 기간은 2026-10-08~2026-11-06의 30일이다.
`occurred_at`·`received_at`은 실제 시각이고, `props.simulation_at`,
`simulation_at_kst`, `simulation_date`, `simulation_time_is_fictional`은 가상 시간 필드다.
이 필드명의 `simulation`은 컬렉션 이름과 별개이며 변경하지 않는다.
월별 CSV는 30일 창의 부분 월 집계이므로 완전한 두 달 비교에 쓰지 않는다.
`daily.csv`, `weekly.csv`, `monthly.csv`, `analytics.json`, `daily-query.json`,
`verification-periods.json`은 해당 실행 폴더에서 확인한다.

## 로컬 검증

실제 서비스 부하를 보내지 않는 테스트다. 브라우저 전송 검사에는 설치된 Chromium,
API 통합 검사에는 backend 의존성이 필요하다. `../backend/requirements.txt`로 설치한
공통 환경에서 실행한다. 테스트 파일은 camelCase(`testLoadClient.py` 등)이므로
unittest 탐색 패턴은 `test*.py`를 사용한다.

```powershell
python -m unittest discover -s syntheticData -p "test*.py"
python -m unittest discover -s syntheticData/playwright -p "test*.py"
```

프로필 생성기·스키마 설명은 [프로필 설계](personaDataDesign.md),
행동 이벤트 정의는 [이벤트 추적](eventTracking.md)을 참고한다.
