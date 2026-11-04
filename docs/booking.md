# TIKIT 예매(Booking) 기능 명세

공연 예매 → 모의 결제 → 예매 취소 기능의 명세입니다.
원래 별도 폴더 `booking-app/`(Python 단일 서버 + SQLite/MariaDB + Vue 단일 페이지)에 있던 기능을
`backend/`(FastAPI)와 `frontend/`(Vue 3 + Vue Router + Pinia) 구조로 옮겼습니다.
백엔드·프론트엔드 실행 방법은 [backend.md](backend.md), [frontend.md](frontend.md)를 참고하세요.

> 실제 결제·환불·티켓 발급은 발생하지 않는 **시연용 모의 결제**입니다. 좌석 번호·재고 관리와 실제 PG 연동은 포함하지 않습니다.

---

## 1. 기능 요약

| # | 기능 | 설명 | 로그인 |
|---|---|---|---|
| F1 | 공연 선택 | 공연 카드·배너·랭킹·`/?show=<공연 id>` 주소로 예매 창 열기 | 불필요 |
| F2 | 일정·좌석 선택 | 관람일, 회차, 좌석 등급(일반석/프리미엄석), 수량(1~4매) 선택, 총 금액 실시간 표시 | 불필요 |
| F3 | 로그인 후 이어서 예매 | 비로그인 상태에서 예매하면 선택값을 보관한 채 로그인 화면으로 이동 → 로그인 후 예매 확인 단계로 복귀 | - |
| F4 | 예매 요청 | 예매 내용 확인·동의 후 예매 생성. 예매는 `예매 요청`, 결제는 `결제 대기` 상태로 생성 | 필요 |
| F5 | 모의 결제 | 결제 대기 건을 결제 완료로 변경, 예매 확정. 예매 완료 창 또는 마이티킷에서 실행 | 필요 |
| F6 | 예매 취소 | 결제 대기/결제 완료 건을 취소. 예매·결제가 함께 취소되며 금액·결제 완료 시각은 보존 | 필요 |
| F7 | 마이티킷 | `/my-tickets` 화면에서 예매·결제 내역(상태, 금액, 결제 완료 일시) 확인, 결제·취소 | 필요 |
| F8 | 중복 예매 방지 | 예매 창마다 발급한 요청 키(UUID)로 재시도·더블클릭 시 같은 예매를 돌려줌 | 필요 |
| F9 | 상태 이력·분석 이벤트 | 모든 상태 변경을 이력으로 남기고, 예매 시작·요청·결제·취소 이벤트를 수집 | 필요 |
| F10 | 내 데이터 | 예매 내역을 포함한 데이터 내려받기(JSON), 계정 삭제 시 예매·결제·이력 함께 삭제 | 필요 |

---

## 2. 화면 흐름

```
공연 카드 클릭
   │
   ▼
[예매 창] 01 날짜·회차 ── 좌석 등급·수량 선택, 총 결제 금액 표시
   │ 예매하기 (비로그인 → 로그인 화면 → 로그인 후 02 단계로 복귀)
   ▼
[예매 창] 02 예매 확인 ── 예매자·관람 일시·좌석·금액 확인 + 동의 체크
   │ 예매하기 · 금액            (← 날짜·회차 다시 선택: 요청 키 새로 발급)
   ▼
[예매 창] 03 완료 ── 상태: 결제 대기
   │ 결제하기 ──▶ 상태: 결제 완료
   │ 예매 내역 확인하기 ──▶ /my-tickets
   ▼
[마이티킷 /my-tickets] 예매 카드 목록
   ├ 결제 대기: [결제하기] [예매 취소]
   ├ 결제 완료: 결제 완료 일시 표시, [예매 취소]
   └ 결제 취소: 버튼 없음 (금액·결제 완료 일시는 그대로 표시)
       예매 취소 → 확인 창 → 예매·결제 동시 취소
```

- 마이티킷은 로그인이 필요한 화면으로, 비로그인 사용자는 로그인 화면으로 이동했다가 돌아옵니다.
- 상단 `마이티킷` 메뉴와 마이페이지의 `예매 내역` 메뉴가 `/my-tickets`로 연결됩니다.
- 이전 주소 `/?open=mytikit`은 `/my-tickets`로 바뀌어 이동합니다.
- 시각은 서버에서 UTC로 내려오며 화면에서는 한국 시간(분 단위)으로 표시합니다.

---

## 3. 상태 정의

### 예매 상태 (`reservations.status`)

| 값 | 화면 표시 | 의미 |
|---|---|---|
| `REQUESTED` | 예매 요청 | 예매가 생성되고 결제를 기다리는 상태 |
| `CONFIRMED` | 예매 완료 | 결제가 완료되어 확정된 상태 |
| `CANCELLED` | 예매 취소 | 사용자가 취소한 상태 (최종) |

### 결제 상태 (`payments.status`)

| 값 | 화면 표시 | 의미 |
|---|---|---|
| `PENDING` | 결제 대기 | 예매와 함께 생성된 결제 대기 |
| `COMPLETED` | 결제 완료 | 모의 결제 완료 |
| `CANCELLED` | 결제 취소 | 예매 취소로 함께 취소됨 (최종) |

### 상태 전이

| 현재 (예매 / 결제) | 결제하기(complete) | 예매 취소(cancel) |
|---|---|---|
| REQUESTED / PENDING | → CONFIRMED / COMPLETED | → CANCELLED / CANCELLED |
| CONFIRMED / COMPLETED | 변화 없음 (200, 재시도로 처리) | → CANCELLED / CANCELLED |
| CANCELLED / CANCELLED | **409** 취소한 예매는 결제할 수 없음 | 변화 없음 (200, 재시도로 처리) |

- 같은 작업을 다시 보내면 상태·시각·이력을 바꾸지 않고 현재 예매를 그대로 돌려줍니다.
- 취소해도 금액(`amount`)과 결제 완료 시각(`completed_at`)은 보존됩니다.

---

## 4. API 명세

- 기본 주소: `/api/v1` (개발: Vite 프록시, 배포: nginx 프록시 → `127.0.0.1:8000`)
- 인증: `Authorization: Bearer <JWT>` (회원가입·로그인 응답의 `access_token`)
- 본문·응답: JSON, 필드 이름은 snake_case
- 오류: `{ "detail": "메시지" }` (입력 형식 오류는 FastAPI 422 `detail` 배열)

| 메서드 | 경로 | 설명 | 성공 |
|---|---|---|---|
| POST | `/reservations` | 예매 요청 + 결제 대기 생성 | 201 (같은 요청 키 재시도는 200) |
| GET | `/reservations` | 내 예매 목록(결제 정보 포함, 최신순) | 200 |
| GET | `/payments` | 내 결제 목록(예매 요약 포함, 최신순) | 200 |
| POST | `/reservations/{id}/complete` | 모의 결제 완료 → 예매 확정 | 200 |
| POST | `/reservations/{id}/cancel` | 예매·결제 동시 취소 | 200 |
| POST | `/events` | 탐색 이벤트 기록 (`performance_view`, `booking_started`) | 201 |

### 4.1 POST `/reservations`

요청

```json
{
  "performance_id": "opera",
  "performance_date": "2026-11-12",
  "session_time": "19:30",
  "seat_grade": "PREMIUM",
  "quantity": 2,
  "request_key": "6f1c1c43-2a8e-4d3a-9b5e-6c4a8d3e2f10"
}
```

| 필드 | 규칙 |
|---|---|
| `performance_id` | 존재하는 공연 (없으면 404) |
| `performance_date` | 공연의 관람 가능일(`start_date`부터 `days`일) 중 하나 (아니면 422) |
| `session_time` | 공연의 회차(`slots`) 중 하나 (아니면 422) |
| `seat_grade` | `STANDARD` 또는 `PREMIUM` |
| `quantity` | 1 ~ 4 |
| `request_key` | UUID. 예매 창의 확인 단계마다 화면에서 새로 발급 |

- 가격·금액·상태·사용자·시각은 **서버가 결정**합니다. 요청에 `amount`, `user_id`, `status` 등을 넣어도 무시됩니다.
  - 단가 = 공연 가격 + (프리미엄석이면 30,000원), 금액 = 단가 × 수량 (원, KRW 정수)
- 같은 사용자가 같은 `request_key`로
  - 같은 내용(공연·날짜·회차·좌석·수량)을 다시 보내면 → 기존 예매를 **200**으로 반환
  - 다른 내용을 보내면 → **409** `이미 사용한 예매 요청 키입니다. 예매 창을 다시 열어 주세요.`

응답 (`ReservationOut`)

```json
{
  "id": "0991a910-46b8-44db-8820-2fe98cc772e6",
  "user_id": "…", "mbti": "INFP",
  "performance_id": "opera", "performance_title": "뮤지컬 〈오페라의 유령〉",
  "category": "뮤지컬", "venue": "샤롯데씨어터",
  "performance_date": "2026-11-12", "session_time": "19:30",
  "seat_grade": "PREMIUM", "quantity": 2,
  "unit_price": 110000, "amount": 220000, "currency": "KRW",
  "status": "REQUESTED",
  "created_at": "2026-11-04T07:44:35.023702Z", "updated_at": "…", "cancelled_at": null,
  "payment_id": "…", "payment_status": "PENDING",
  "requested_at": "2026-11-04T07:44:35.023702Z", "completed_at": null, "payment_cancelled_at": null,
  "is_mock": true
}
```

### 4.2 GET `/payments` 응답 (`PaymentOut`)

`id`(결제 id), `reservation_id`, `performance_id`, `performance_title`, `performance_date`, `session_time`,
`quantity`, `amount`, `currency`, `status`, `requested_at`, `completed_at`, `cancelled_at`, `is_mock`

### 4.3 상태 코드

| 코드 | 경우 |
|---|---|
| 200 / 201 | 성공 |
| 401 | 로그인하지 않았거나 토큰 만료 (화면은 로그인 화면으로 이동) |
| 404 | 없는 공연, 없는 예매 또는 **다른 사용자의 예매** (존재 여부를 노출하지 않음) |
| 409 | 같은 요청 키로 다른 내용 예매, 취소한 예매 결제 |
| 422 | 관람일·회차·좌석·수량·요청 키 형식 오류, 지원하지 않는 작업(`/refund` 등) |

---

## 5. 데이터 모델

마이그레이션: `backend/alembic/versions/0002_reservations.py`

### `reservations` — 예매

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | VARCHAR(36) PK | UUID |
| user_id | FK users.id (CASCADE) | 예매자 |
| performance_id | FK performances.id | 공연 |
| performance_title, category, venue, mbti | | 예매 당시 공연 정보·MBTI 스냅샷 |
| performance_date | DATE | 관람일 |
| session_time | VARCHAR(5) | 회차 (`HH:MM`) |
| seat_grade | VARCHAR(10) | `STANDARD` / `PREMIUM` |
| quantity | INT | 1~4 |
| unit_price, amount | INT | 단가, 총액 (원) |
| status | VARCHAR(10) | `REQUESTED` / `CONFIRMED` / `CANCELLED` |
| request_key | VARCHAR(36) | 중복 방지 키, **(user_id, request_key) UNIQUE** |
| created_at, updated_at, cancelled_at | DATETIME | UTC |

### `payments` — 모의 결제 (예매와 1:1)

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | VARCHAR(36) PK | UUID |
| reservation_id | FK reservations.id, UNIQUE | 예매 |
| amount, currency | INT, CHAR(3) | 금액, `KRW` |
| status | VARCHAR(10) | `PENDING` / `COMPLETED` / `CANCELLED` |
| requested_at | DATETIME | 결제 요청 시각 (항상 존재) |
| completed_at, cancelled_at | DATETIME NULL | 처리된 경우에만 존재 |
| updated_at | DATETIME | |

### `status_history` — 상태 변경 이력

`id`, `reservation_id`, `user_id`, `entity`(`reservation`/`payment`), `from_status`(생성 시 NULL), `to_status`, `created_at`
→ 예매 1건을 요청·결제·취소하면 이력 6건(예매 3 + 결제 3)이 남습니다.

### `events` — 분석 이벤트 (기존 테이블에 `reservation_id` 컬럼 추가)

| type | 기록 주체 | 시점 |
|---|---|---|
| `performance_view` | 화면 | 예매 창 열기 (비로그인 포함) |
| `booking_started` | 화면 | 01 → 02 단계 이동 (로그인 사용자) |
| `reservation_requested` | 서버 | 예매 생성 |
| `payment_completed` | 서버 | 결제 완료 |
| `reservation_cancelled` | 서버 | 예매 취소 |

- 서버 기록 이벤트는 수집에 동의한(`consent`) 사용자만 남기며, 화면에서 보낼 수는 없습니다(422).
- 인기순 정렬과 랭킹의 `purchases`는 `mock_purchase`(기존 즉시 결제) + `payment_completed` 건수로 계산합니다.

### 저장 규칙

- 예매·결제 생성/변경, 상태 이력, 이벤트는 **하나의 트랜잭션**으로 저장합니다.
- 결제·취소는 예매 행을 `SELECT … FOR UPDATE`로 잠가 동시에 들어와도 한 번만 상태가 바뀝니다.
- 같은 요청 키의 동시 요청은 UNIQUE 제약으로 하나만 저장되고, 나머지는 저장된 예매를 돌려받습니다.
- 회원 탈퇴 시 결제 → 상태 이력·이벤트 → 예매 순서로 삭제합니다.

### 분석 쿼리 예시 (MySQL)

```sql
-- 공연별 예매 요청 수, 결제 완료 경험 수, 취소 수
SELECT p.id, p.title, COUNT(r.id) AS requested,
       SUM(pay.completed_at IS NOT NULL) AS ever_completed,
       SUM(r.status = 'CANCELLED') AS cancelled
FROM performances p
LEFT JOIN reservations r ON r.performance_id = p.id
LEFT JOIN payments pay ON pay.reservation_id = r.id
GROUP BY p.id, p.title;

-- 예매 후 취소까지 걸린 시간(시간 단위)
SELECT performance_id, mbti, TIMESTAMPDIFF(MINUTE, created_at, cancelled_at) / 60 AS hours_to_cancel
FROM reservations WHERE cancelled_at IS NOT NULL;

-- 조회 → 예매 시작 → 요청 → 결제 전환 (이벤트 수와 사용자 수를 구분)
SELECT performance_id, type, COUNT(*) AS events, COUNT(DISTINCT user_id) AS users
FROM events GROUP BY performance_id, type;
```

---

## 6. 코드 위치

### backend/

| 파일 | 역할 |
|---|---|
| `app/models/reservation.py` | `Reservation`, `Payment`, `StatusHistory` 모델 |
| `app/schemas/reservation.py` | `ReservationIn`, `ReservationOut`, `PaymentOut` (DB의 시간대 없는 시각을 UTC로 응답) |
| `app/api/routes/reservations.py` | 예매·결제·취소 API |
| `app/api/routes/events.py`, `app/schemas/event.py` | `booking_started` 이벤트 허용, `reservation_id` 추가 |
| `app/api/routes/performances.py` | 인기순·랭킹에 `payment_completed` 반영 |
| `app/api/routes/users.py` | 내보내기에 `reservations` 포함, 탈퇴 시 예매 데이터 삭제 |
| `app/core/config.py` | 상태값·집계 이벤트 상수 |
| `alembic/versions/0002_reservations.py` | 테이블 3개 생성 + `events.reservation_id` 추가 |
| `tests/test_reservations.py` | 예매 흐름 테스트 8건 |

### frontend/src/

| 파일 | 역할 |
|---|---|
| `composables/useReservations.js` | 예매 API 호출 (`list`, `create`, `complete`, `cancel`), 401 시 로그인 화면 이동 |
| `components/BookingModal.vue` | 예매 창 3단계 (날짜·회차 → 예매 확인 → 완료/결제하기) |
| `components/TicketCard.vue` | 마이티킷 예매 카드 (포스터·정보·금액·상태·버튼) |
| `views/MyTicketsView.vue` | `/my-tickets` 화면 (예매 목록, 취소 확인, 이전 모의 예매, 찜, 내 데이터) |
| `router/index.js` | `/my-tickets` 경로 (로그인 필요) |
| `views/HomeView.vue` | `?show=`, `?resume=booking` 처리, 마이티킷 이동 |
| `components/AppHeader.vue`, `views/MyPageView.vue` | 마이티킷·예매 내역 메뉴 연결 |
| `utils/index.js` | 상태 라벨, 좌석 라벨, 한국 시간 표시, 요청 키(UUID) 발급 |
| `assets/styles.css` | 마이티킷·결제 상태 스타일 (하단 블록) |

기존 `MyTicketModal.vue`(팝업)는 `/my-tickets` 화면으로 대체되어 삭제했습니다.

---

## 7. booking-app 에서 바뀐 점

| 항목 | booking-app | 현재 |
|---|---|---|
| 서버 | `server.py` (표준 라이브러리 HTTP 서버) | FastAPI 라우터 (`/api/v1`) |
| DB | SQLite 또는 MariaDB, `schema.sql` | MySQL + SQLAlchemy, Alembic 마이그레이션 |
| 공연 데이터 | `performances.json` | 기존 `performances` 테이블 (`app/db/seed.py`) |
| 인증 | HttpOnly 세션 쿠키 + 동일 출처 검사 | JWT Bearer 토큰 (기존 회원 기능 그대로) |
| 필드 이름 | camelCase (`performanceId`, `paymentStatus`) | snake_case (`performance_id`, `payment_status`) |
| 오류 형식 | `{ "error": "…" }`, 입력 오류 400 | `{ "detail": "…" }`, 입력 오류 422 |
| 동시성 | 전역 잠금 행으로 모든 쓰기 직렬화 | 예매 행 잠금 + UNIQUE 제약 |
| 화면 | 단일 `App.vue` + 해시 주소(`#my-tickets`) | Vue Router 화면(`/my-tickets`) + 컴포넌트·컴포저블 분리 |
| 찜 | 브라우저 localStorage | 서버 API(`/favorites`) |

기존 `/orders`(결제 방법을 고르면 바로 `MOCK_PAID`로 저장하는 이전 방식) API는 호환을 위해 남겨 두었으며,
그 내역은 마이티킷의 `이전 모의 예매`에 표시됩니다. 새 예매는 모두 `/reservations`를 사용합니다.

---

## 8. 실행과 검증

```powershell
# 백엔드: 새 테이블 반영
cd backend
python -m alembic upgrade head
python -m uvicorn app.main:app --port 8000

# 프론트엔드
cd frontend
npm run dev        # http://localhost:5173
```

```powershell
cd backend
python -m pytest -q          # 29건 (예매 흐름 8건 포함)
cd ../frontend
npm run build
```

`tests/test_reservations.py`가 확인하는 내용

- 요청 → 결제 → 취소 상태 전이, 결제 완료 시각·금액 보존, 상태 이력 6건, 이벤트 3건
- 결제 대기 상태에서 바로 취소
- 같은 요청 키 재시도 시 같은 예매(200), 내용이 다르면 409
- 비로그인 401, 다른 사용자의 예매 접근 404, 목록 격리
- 관람일·회차·수량·좌석·요청 키 검증
- 결제 목록, 결제 완료가 랭킹에 반영
- `booking_started` 이벤트 허용, 서버 전용 이벤트 차단
- 데이터 내보내기에 예매 포함, 탈퇴 시 예매·결제·이력 삭제
