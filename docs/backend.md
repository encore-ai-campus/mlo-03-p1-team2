# TIKIT 백엔드 API

`sample/dist` 시연 프론트엔드가 브라우저(localStorage/sessionStorage)에 저장하던 계정·로그인·예매·찜·조회 기록을 서버에서 처리하는 백엔드입니다. `frontend/` 화면이 이 API를 사용합니다.

- 프레임워크: FastAPI
- DB: MySQL 8 (SQLAlchemy 2.0 + PyMySQL), 마이그레이션은 Alembic
- 인증: JWT Bearer 토큰 (PyJWT), 비밀번호 해시는 Argon2 (pwdlib)
- 검증: Pydantic v2
- 테스트: pytest + FastAPI TestClient (인메모리 SQLite)

---

## 1. 폴더 구성

```
backend/
├─ requirements.txt          의존성 목록
├─ .env.example              환경 변수 예시 (.env로 복사해서 사용, .env는 git 제외)
├─ alembic.ini               Alembic 설정
├─ alembic/
│  ├─ env.py                 DATABASE_URL을 앱 설정에서 읽어 마이그레이션 실행
│  ├─ script.py.mako         마이그레이션 파일 템플릿
│  └─ versions/0001_initial.py   최초 스키마 (5개 테이블)
│     └─ 0002_reservations.py    예매·결제·상태 이력 테이블 (docs/booking.md)
├─ app/
│  ├─ main.py                FastAPI 앱, CORS, 라우터 등록, /health
│  ├─ core/
│  │  ├─ config.py           환경 설정 + 예매 규칙 상수
│  │  └─ security.py         비밀번호 해시/검증, JWT 발급/해독
│  ├─ db/
│  │  ├─ base.py             SQLAlchemy DeclarativeBase
│  │  ├─ session.py          DB 엔진, 세션, get_db 의존성
│  │  ├─ seed.py             공연 시연 데이터 680건 입력 스크립트
│  │  └─ seed_bulk.py        카테고리별 대량 샘플 공연 생성기 (시드 고정)
│  ├─ models/                user, performance, order, event, favorite, reservation(예매·결제·이력)
│  ├─ schemas/               요청/응답 Pydantic 모델 (user, performance, order, event, export)
│  └─ api/
│     ├─ deps.py             DB 세션·현재 사용자 의존성
│     ├─ router.py           /api/v1 하위 라우터 묶음
│     └─ routes/             auth, users, performances, orders, reservations, favorites, events
└─ tests/
   ├─ conftest.py            테스트용 SQLite DB, 클라이언트, 로그인 픽스처
   ├─ test_auth.py           회원가입·로그인·인증 테스트
   ├─ test_profile.py        회원 정보 수정·비밀번호 변경 테스트
   ├─ test_booking.py        공연·예매·찜·이벤트·내보내기·탈퇴 테스트
   └─ test_reservations.py   예매 → 결제 → 취소 흐름 테스트
```

---

## 2. 데이터 모델

[sample.md](sample.md)에 정리된 localStorage 필드를 테이블로 옮겼습니다.

| 테이블 | 기존 저장 위치 | 주요 컬럼 |
|---|---|---|
| `users` | `tikit.accounts` | id(UUID), name(닉네임), email(고유, 소문자), password_hash, mbti, consent, consented_at, created_at |
| `performances` | `app.js`의 `shows` 배열 | id(`city` 등), category, title, english, sub, image, style, venue, date_label, start_date, days, price, badge, tag, slots(JSON) |
| `orders` | `tikit.orders` | id, user_id, performance_id, performance_date, session_time, seat_grade, quantity, unit_price, amount, currency, payment_method, status, is_mock, created_at + 당시 공연명·분류·장소·MBTI 스냅샷 |
| `events` | `tikit.events` | id, user_id(비로그인 시 NULL), mbti, type(`performance_view`/`mock_purchase`), performance_id, category, created_at |
| `favorites` | `tikit.favorites` | (user_id, performance_id) 복합 기본키, created_at |

- `orders`, `events`, `favorites`의 `user_id`는 `ON DELETE CASCADE`로 연결되어 회원 탈퇴 시 함께 삭제됩니다.
- 주문에 공연명·장소 등을 복사해 두어, 공연 정보가 바뀌어도 예매 당시 내역이 보존됩니다.
- 공연 날짜 목록은 `start_date`부터 `days`일 동안으로 계산합니다(`Performance.available_dates`).

---

## 3. API 목록 (`/api/v1`)

| 메서드 | 경로 | 로그인 | 설명 |
|---|---|---|---|
| POST | `/auth/signup` | – | 회원가입 후 토큰 발급 |
| POST | `/auth/login` | – | 로그인 후 토큰 발급 |
| GET | `/users/me` | 필요 | 내 정보 (비밀번호 해시 제외) |
| PATCH | `/users/me` | 필요 | 회원 정보 수정 (닉네임·이메일·MBTI, 보낸 항목만 변경) |
| PUT | `/users/me/password` | 필요 | 비밀번호 변경 |
| GET | `/users/me/export` | 필요 | 내 정보·예매·조회 기록·찜 JSON 내보내기 |
| DELETE | `/users/me` | 필요 | 회원 탈퇴 및 연결 데이터 삭제 |
| GET | `/performances` | – | 공연 목록. `category`, `q`(검색어), `sort`(`popular`/`date`/`price`) |
| GET | `/performances/ranking` | – | 예매 수 → 조회 수 순 랭킹 (`limit` 기본 5) |
| GET | `/performances/{id}` | – | 공연 상세 + 예매 가능 날짜 목록 |
| POST | `/orders` | 필요 | 모의 예매 생성 |
| GET | `/orders` | 필요 | 내 예매 내역 (최신순) |
| GET | `/favorites` | 필요 | 찜 목록 (공연 ID 배열) |
| PUT | `/favorites/{id}` | 필요 | 찜 추가 (중복 요청해도 안전) |
| DELETE | `/favorites/{id}` | 필요 | 찜 해제 |
| POST | `/events` | 선택 | 공연 조회 기록. 비로그인도 가능 |
| GET | `/health` | – | 서버 상태 확인 (`/api/v1` 밖) |

로그인이 필요한 요청은 헤더에 `Authorization: Bearer <access_token>`을 넣습니다. 서버 실행 후 http://localhost:8000/docs 에서 직접 호출해 볼 수 있습니다.

관리자 전용 공연 CRUD는 `/api/v1/admin/performances`에서 제공합니다.
적용 전에 `0004` 마이그레이션이 필요하며 관리자 지정과 상세 API는 [관리자 공연 관리](admin.md)를 참고하세요.

---

## 4. 주요 로직

### 4-1. 회원가입 (`app/schemas/user.py`, `app/api/routes/auth.py`)
- 닉네임: 앞뒤 공백 제거 후 1~30자
- 이메일: 형식 검사 후 소문자로 저장 → `User@Example.com`과 `user@example.com`은 같은 계정
- 비밀번호: 8~128자, `password_confirm`과 일치해야 함
- MBTI: 16개 유형 중 하나, 수집 동의(`consent`)는 반드시 `true`
- 이메일 중복이면 `409` (동시 가입으로 DB 고유 제약에 걸리는 경우도 `409`)
- 성공 시 바로 토큰을 발급하므로 가입 후 별도 로그인이 필요 없습니다.

### 4-2. 로그인과 인증 (`app/core/security.py`, `app/api/deps.py`)
- 비밀번호는 Argon2 해시로만 저장하고 원문은 보관하지 않습니다.
- 이메일이 없거나 비밀번호가 틀려도 같은 메시지와 `401`을 반환합니다. 없는 이메일일 때도 더미 해시를 검증해, 응답 시간으로 가입 여부를 알 수 없게 했습니다.
- JWT의 `sub`에 사용자 ID를 담고, 기본 만료 시간은 60분입니다(`JWT_EXPIRE_MINUTES`).
- `get_current_user`: 토큰이 없거나 잘못되었거나 탈퇴한 사용자면 `401`
- `get_optional_user`: 토큰이 없으면 비로그인으로 처리 (조회 이벤트용)

### 4-3. 회원 정보 수정·비밀번호 변경 (`app/api/routes/users.py`)
- `PATCH /users/me`는 보낸 항목만 바꿉니다. 닉네임·MBTI 검증 규칙은 회원가입과 같습니다.
- **이메일을 바꿀 때만 `current_password`가 필요합니다.** 로그인 아이디가 바뀌는 민감한 변경이기 때문입니다. 틀리면 `403`, 다른 회원이 쓰는 이메일이면 `409`
- `PUT /users/me/password`는 현재 비밀번호 확인(틀리면 `403`), 새 비밀번호 8~128자·확인 일치(`422`), 현재와 같은 비밀번호 거절(`400`)
- 비밀번호를 바꿔도 이미 발급된 토큰은 만료 시간까지 유효합니다. 즉시 다른 기기를 로그아웃시키려면 토큰 무효화 기능이 추가로 필요합니다.

### 4-4. 예매 (`app/api/routes/orders.py`)
- 클라이언트는 공연 ID, 날짜, 회차, 좌석 등급, 수량, 결제 방법만 보냅니다.
- **금액은 서버가 계산합니다.** `단가 = DB의 공연 가격 + (프리미엄석이면 30,000원)`, `총액 = 단가 × 수량`
- 없는 공연 `404`, 공연 기간 밖 날짜·없는 회차·수량 1~4 밖·잘못된 등급/결제 방법 `422`
- 저장 시 `status=MOCK_PAID`, `is_mock=true`로 기록하고, 같은 트랜잭션에서 `mock_purchase` 이벤트도 남깁니다.
- 좌석 재고와 좌석 번호는 관리하지 않습니다(등급만 선택).
- 수치 규칙(프리미엄 추가금, 최대 수량, 결제 방법, MBTI 목록, 분류)은 `app/core/config.py`에 모아 두었습니다.

### 4-5. 공연 목록·랭킹 (`app/api/routes/performances.py`)
- `category`: `전체`이거나 없으면 전체 목록 / `q`: 공연명·장소·분류 부분 일치 검색
- `sort`: `date` 시작일 순, `price` 가격 낮은 순, `popular`(기본) 모의 예매 수 많은 순
- 랭킹: 예매 수 → 조회 수 → ID 순, 각 공연의 `purchases`, `views` 함께 반환

### 4-6. 찜·이벤트·내보내기·탈퇴
- 찜 추가는 이미 있으면 그대로 두고 `204`를 반환해 여러 번 눌러도 안전합니다.
- 조회 이벤트는 비로그인도 기록되며, 이때 `user_id`와 `mbti`는 비어 있습니다.
- 내보내기 JSON에는 비밀번호 해시가 포함되지 않습니다.
- 탈퇴 시 DB CASCADE와 별개로 코드에서도 예매·이벤트·찜을 직접 삭제합니다(외래키가 강제되지 않는 SQLite 대비).

### 4-7. 검증 오류 응답 (`app/main.py`)
422 응답에서 FastAPI가 기본으로 돌려주는 요청 원문(`input`)과 `ctx`를 제거합니다. 그대로 두면 비밀번호 불일치 같은 오류 응답에 입력한 비밀번호가 담겨 돌아옵니다.

### 4-8. CORS
nginx가 `/api/` 요청을 같은 주소로 전달하므로 평소에는 CORS가 필요 없습니다. 프록시 없이 프론트 개발 서버(`http://localhost:5173`)에서 직접 호출할 때만 쓰이며, `.env`의 `CORS_ORIGINS`로 변경할 수 있습니다.

---

## 5. 실행 방법

`backend/` 폴더에서 실행합니다.

```powershell
# 1) 가상환경과 의존성 설치 (처음 한 번)
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

# 2) 환경 변수 파일 준비 후 DATABASE_URL, JWT_SECRET 수정
copy .env.example .env

# 3) MySQL에 데이터베이스 생성 (처음 한 번, MySQL 클라이언트에서 실행)
#    CREATE DATABASE tikit CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 4) 테이블 생성 및 공연 데이터 입력
.venv\Scripts\python -m alembic upgrade head
.venv\Scripts\python -m app.db.seed

# 5) 서버 실행 후 http://localhost:8000/docs 에서 API 확인
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

> **`alembic.exe` 대신 `python -m alembic`을 사용하세요.** `.venv\Scripts\alembic upgrade head`로 실행하면 현재 폴더가 import 경로에 들어가지 않아 `app` 모듈을 찾지 못하고, 메시지 없이 실패합니다.

### PyCharm에서 실행
Run → Edit Configurations → `+` → Python
- 인터프리터: `backend\.venv\Scripts\python.exe`
- Module name(모듈 모드): `uvicorn`
- Parameters: `app.main:app --reload --host 127.0.0.1 --port 8000`
- Working directory: `backend` 폴더 (`.env`를 상대 경로로 읽기 때문에 반드시 `backend`로 지정)

작업 디렉터리가 프로젝트 루트(`tikit`)이면 `ModuleNotFoundError: No module named 'app'`이 발생합니다.

### 환경 변수 (`.env`)
| 이름 | 기본값 | 설명 |
|---|---|---|
| `DATABASE_URL` | `mysql+pymysql://tikit:tikit@localhost:3306/tikit?charset=utf8mb4` | DB 접속 주소 |
| `JWT_SECRET` | `dev-secret-change-me` | 토큰 서명 키. **운영 시 반드시 긴 임의 문자열로 변경** |
| `JWT_EXPIRE_MINUTES` | `60` | 토큰 유효 시간(분) |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | 프록시 없이 직접 호출할 때 허용할 프론트 주소 |

`.env`에는 실제 DB 비밀번호가 들어가므로 커밋하지 않습니다(`.gitignore`에 포함).

---

## 6. 테스트

```powershell
.venv\Scripts\python -m pytest -q
```

MySQL 없이 인메모리 SQLite에서 실행되며, 현재 21개 모두 통과합니다.
- 회원가입: 성공·이메일 소문자 정규화, 중복 이메일 `409`, 비밀번호 불일치·동의 누락·잘못된 MBTI·짧은 비밀번호 `422`, 오류 응답에 비밀번호 미포함
- 로그인: 성공, 틀린 비밀번호·없는 이메일 `401`(같은 메시지), 토큰 없음·잘못된 토큰 `401`
- 회원 정보 수정: 닉네임·MBTI 변경, 이메일 변경 시 현재 비밀번호 확인, 중복 이메일 `409`, 비밀번호 변경 후 새 비밀번호로만 로그인
- 예매: 공연 필터·검색·정렬, 조작된 금액 무시, 잘못된 날짜·회차·수량·등급·결제 방법 `422`
- 찜·조회 이벤트·랭킹, 내보내기에 해시 미포함, 탈퇴 후 연결 데이터 삭제

---

## 7. 남은 작업

- 이메일 인증, 비밀번호 재설정(찾기), 토큰 갱신(refresh token)
- 비밀번호 변경·로그아웃 시 기존 토큰 즉시 무효화
- 좌석 재고·좌석 번호 관리, 예매 취소·환불 API
- 공연 일정과 가격은 시연 데이터입니다.
