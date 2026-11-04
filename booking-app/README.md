# TIKIT 예매 · 결제 DB 버전

## Vue 프론트엔드

화면 소스는 `frontend/`의 Vue 3 프로젝트입니다. Python 서버가 Vue 빌드 결과인
`frontend/dist/`와 API를 함께 제공하므로 빌드 후에는 터미널 하나로 실행합니다.
화면 개발 방법과 폴더 구조는 [frontend/README.md](frontend/README.md)를 참고하세요.

Python 3.10 이상과 빌드용 Node.js 22.12 이상이 필요합니다. Python 추가 패키지는 필요하지 않습니다.
최초 실행 및 Vue 소스 변경 후에는 빌드를 먼저 진행하세요.

```powershell
cd tikit/booking-app
cd frontend
npm ci
npm run build
cd ..
python server.py
```

http://127.0.0.1:8000 에서 회원가입 후 공연을 선택하세요. 예매하기 → 결제 대기 → 결제하기 또는 예매 취소 순서입니다. 상단 마이티킷을 누르면 팝업 대신 통합 내역 페이지(`/#my-tickets`)로 이동합니다. 공연별 카드에서 예매 정보와 결제 금액·상태를 함께 확인하고 결제·취소할 수 있습니다. 페이지 새로고침과 뒤로 가기를 지원합니다. 실제 결제나 환불, 티켓 발급은 발생하지 않습니다. DB는 최초 실행 시 `data/tikit.sqlite3`에 생성됩니다. 기존 sample의 브라우저 계정과 예매를 자동으로 가져오지 않습니다.

화면에는 결제 상태만 11px의 형광펜 스타일로 표시하고 결제 완료 일시는 한국 시간으로 분 단위까지 표시합니다. 상세 요청·취소 시각과 예매 상태는 DB/API에 유지합니다.

## 파일과 저장 위치

- `frontend/src/`: Vue 화면 컴포넌트, 스타일, API 연결 코드
- `frontend/package.json`, `frontend/package-lock.json`: 빌드 명령과 의존성 정보
- `frontend/dist/`: `npm run build`로 생성되는 화면과 JS·CSS. 서버가 이 폴더를 제공합니다.
- `server.py`: 화면 제공 및 SQLite API 서버
- `performances.json`: 새 DB를 만들 때 사용하는 초기 공연 정보
- `data/tikit.sqlite3`: 회원·예매·결제·상태 이력을 저장하는 실제 DB. 삭제하면 저장된 내역이 사라집니다.
- `tests/artifacts/`: 브라우저 테스트가 생성하는 화면 캡처. 실행에 필요하지 않으며 언제든 삭제할 수 있습니다.

`frontend/`의 소스·설정·잠금 파일, `server.py`, `performances.json`, 테스트와 문서는 커밋에 포함하세요.
`static/`, `frontend/node_modules/`, `frontend/dist/`, `data/`, `tests/artifacts/`, Python 캐시는
`.gitignore`로 제외합니다. 저장소를 새로 받은 환경에서는 위 명령으로 빌드한 뒤 실행하세요.
`static/`은 더 이상 사용하지 않습니다. 화면과 API는 http://127.0.0.1:8000 에서 함께 제공됩니다.

## API 계약

모든 본문과 응답은 JSON입니다. 오류는 `{ "error": "메시지" }`입니다. 가입/로그인 응답은 사용자 프로필이며 HttpOnly, SameSite=Strict 쿠키로 7일 동안 인증합니다. `/api/me`는 비로그인 시 null을 반환합니다. 상태를 변경하는 요청은 동일 출처만 허용합니다. 사용자 ID, 가격, 상태, 시각은 클라이언트가 지정할 수 없습니다.

| 메서드 | 경로 | 입력 / 결과 |
| --- | --- | --- |
| POST | /api/auth/signup | name, email, password(8~128자), mbti, consent:true → 프로필(201) |
| POST | /api/auth/login | email, password → 프로필 |
| POST | /api/auth/logout | 현재 세션 종료 |
| GET | /api/me | 현재 프로필 또는 null |
| GET | /api/performances | 서버 기준 공연 목록 |
| POST | /api/events | 인증 필수, type:performance_view 또는 booking_started, performanceId → 수집 동의한 사용자의 탐색 기록(201) |
| POST | /api/reservations | 인증 필수, performanceId, performanceDate, sessionTime, seatGrade:STANDARD/PREMIUM, quantity:1~4, requestKey(UUID) → 예매+결제 대기 생성(201) |
| GET | /api/reservations | 본인의 예매 배열(금액·결제 상태 포함) |
| GET | /api/payments | 본인의 결제 배열(예매 정보, 금액, 요청/완료/취소 시각 포함) |
| POST | /api/reservations/{id}/complete | 본인의 대기 건 → 모의 결제 완료, 예매 확정 |
| POST | /api/reservations/{id}/cancel | 본인의 대기/완료 건 → 예매·결제 동시 취소 |

상태 코드: 잘못된 입력 400, 비로그인 401, 다른 출처 403, 없는/다른 사용자 소유 리소스 404, 중복 이메일·같은 요청 키로 다른 예매·취소 후 결제 409. 같은 사용자와 requestKey의 동일 예매 요청은 기존 건을 반환(200)하므로 재시도해도 중복 생성되지 않습니다. 완료와 취소도 동일 작업 재시도 시 이력을 중복 생성하지 않습니다.

예매 상태는 REQUESTED(예매 요청), CONFIRMED(예매 완료), CANCELLED(예매 취소), 결제 상태는 PENDING(결제 대기), COMPLETED(결제 완료), CANCELLED(결제 취소)입니다. 금액은 정수 원(KRW), 시각은 UTC ISO 8601이며 화면에서는 한국 시간으로 표시합니다. 결제 요청 시각은 항상 존재하고 완료/취소 시각은 해당 처리 후에만 존재합니다. 취소해도 원금과 과거 완료 시각은 보존됩니다.

## 데이터와 분석

`users`, `sessions`, `performances`, `reservations`, `payments`, `events`, `status_history` 테이블을 사용합니다. 예매·결제 생성/완료/취소 및 이력은 단일 DB 트랜잭션으로 처리합니다. 서버에서 공연/날짜/회차/수량/가격을 검증합니다. 비밀번호는 PBKDF2-SHA256과 사용자별 랜덤 salt로 해시하고, 세션 토큰도 해시로 저장합니다. DB 파일은 웹에서 제공하지 않습니다.

공연 조회·예매 시작·예매 요청·결제 완료·예매 취소 이벤트에 사용자, MBTI, 공연, 예매 ID와 시각을 저장하고, 상태 이력에 변경 전후 상태를 남깁니다. 상세 분석 화면은 포함하지 않았으며 다음 쿼리를 DB에서 실행할 수 있습니다.

```sql
-- 공연별 요청 수, 한 번이라도 결제 완료한 수, 취소 수
SELECT p.id, p.title, COUNT(r.id) AS requested,
       SUM(CASE WHEN pay.completed_at IS NOT NULL THEN 1 ELSE 0 END) AS ever_completed,
       SUM(CASE WHEN r.status='CANCELLED' THEN 1 ELSE 0 END) AS cancelled
FROM performances p LEFT JOIN reservations r ON r.performance_id=p.id
LEFT JOIN payments pay ON pay.reservation_id=r.id GROUP BY p.id;

-- 예매 후 취소까지 소요 시간(시간 단위)
SELECT performance_id, mbti, (julianday(cancelled_at)-julianday(created_at))*24 AS hours_to_cancel
FROM reservations WHERE cancelled_at IS NOT NULL;

-- 조회/시작/요청/완료 전환: 이벤트 건수와 사용자 수를 구분해서 해석
SELECT performance_id, type, COUNT(*) AS events, COUNT(DISTINCT user_id) AS users
FROM events GROUP BY performance_id, type;
```

공연은 초기 데이터의 예시 일정·가격을 사용하며 좌석 재고/좌석 번호, 실제 PG, 운영용 배포는 포함하지 않습니다. 이 서버는 localhost에서 개발·실습하는 용도입니다. 외부 배포에는 HTTPS, 로그인 시도 제한과 운영 서버 구성이 필요합니다.

## 검증

```powershell
python -m unittest discover -s tests -v
npm --prefix frontend run build
```

HTTP + SQLite 테스트는 상태 전환, 동시 요청, 중복 방지, 사용자별 접근 제한, 입력 검증,
재로그인/서버 재시작 후 보존과 Vue 빌드 파일 제공, GET·HEAD 경로 보호, 빌드 누락 안내를 검사합니다.
테스트는 임시 DB와 화면 파일을 사용하므로 실제 DB와 프론트엔드 빌드 없이 실행할 수 있습니다.
브라우저 검증은 빌드 후 테스트 서버에서 가입 → 예매 → 결제 → 취소 → 새로고침과 모바일 배치를 확인합니다.

선택적으로 Playwright가 설치된 환경에서 실행 중인 **테스트 서버**를 대상으로 `node tests/browser-smoke.cjs`를 실행할 수 있습니다. `BASE_URL`로 주소를 바꿀 수 있으며, 테스트 계정과 예매를 생성하므로 운영 DB에는 실행하지 마세요.
