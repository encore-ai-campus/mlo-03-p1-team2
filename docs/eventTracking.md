# 사용자 행동 이벤트 수집 (MongoDB)

사용자가 서비스에서 한 행동을 이벤트로 모아 MongoDB에 저장합니다.
기존 MySQL `events` 테이블(인기순·랭킹 집계용)은 그대로 두고, 분석용 행동 로그를 별도로 쌓습니다.

## 흐름

```
화면 행동 → track(type, props) → 프론트엔드 큐(최대 10개)
                                   ├─ 10개가 차면 즉시 전송
                                   ├─ 3초마다 쌓인 이벤트가 있으면 전송
                                   └─ 탭 숨김·페이지 이탈 시 keepalive 로 전송
            → POST /api/v1/tracking/events { "events": [...] }  (최대 10건)
            → MongoDB  tikit.events
```

| 위치 | 역할 |
|---|---|
| `frontend/src/utils/tracker.js` | 큐·주기 전송·재시도. `track()`, `installTracking()` |
| `frontend/src/main.js` | 토큰 연결, 화면 이동(`page_view`) 기록, 3초 타이머 시작 |
| `backend/app/api/routes/tracking.py` | 배치 수신, 서버 필드 추가, MongoDB 저장 |
| `backend/app/schemas/tracking.py` | 이벤트 형식 검증 |
| `backend/app/db/mongo.py` | MongoDB 연결과 인덱스 |
| `backend/app/core/config.py` | `TRACKING_EVENT_TYPES` (허용하는 type 목록) |

## 이벤트 형식

```json
{
  "event_id": "040a2e68-e35a-45db-91e0-60b3f02bcd23",
  "type": "performance_view",
  "occurred_at": "2026-11-04T05:29:44.172Z",
  "session_id": "1891079c-3842-4559-a60f-0ba5d92eae8c",
  "anonymous_id": "30b1f137-cecb-4113-b349-783bc3760b87",
  "page": { "path": "/", "referrer": "" },
  "props": { "performance_id": "opera", "category": "뮤지컬", "price_krw": 80000, "source": "list" },
  "schema_version": 1
}
```

| 필드 | 설명 |
|---|---|
| `event_id` | 이벤트마다 새 UUID. MongoDB `_id` 로도 써서 재전송돼도 중복 저장되지 않습니다. |
| `session_id` | 탭 단위 UUID (`sessionStorage`) |
| `anonymous_id` | 브라우저 단위 UUID (`localStorage`). 로그인과 무관하게 유지 |
| `page.path` / `page.referrer` | 이벤트가 일어난 화면 주소, 직전 화면 주소 |
| `props` | type 별 추가 정보. 한 단계 값(문자열·숫자·불리언·null)만, 최대 20개, 문자열 500자 |

서버가 저장할 때 추가하는 필드: `user_id`(JWT 토큰에서만 추출, 비회원·만료 토큰이면 `null`), `user_agent`, `received_at`.

## 이벤트 type

| type | 언제 | 주요 props |
|---|---|---|
| `page_view` | 화면 경로가 바뀔 때 (쿼리만 바뀌면 제외) | `route` |
| `search` | 검색어 제출 | `query` |
| `category_select` | 카테고리 칩 / 취향 모달에서 카테고리 선택 | `category`, `source`(list·taste) |
| `sort_change` | 정렬 변경 | `sort` |
| `list_expand` | 공연 목록 더보기·접기 | `expanded`, `category` |
| `performance_view` | 공연 상세(예매 모달) 열기 | `performance_id`, `category`, `price_krw`, `source`(hero·list·ranking·link) |
| `taste_view` | MBTI 취향 모달·리포트 보기 | `source`(home·mypage) |
| `favorite_add` / `favorite_remove` | 찜 추가·해제 | `performance_id` |
| `booking_start` | 날짜·회차 선택 후 예매하기 | `performance_id`, `category`, `performance_date`, `session_time`, `seat_grade`, `quantity`, `amount_krw` |
| `reservation_request` | 예매 요청 성공 | `reservation_id`, `performance_id`, `category`, `seat_grade`, `quantity`, `amount_krw` |
| `payment_complete` | 모의 결제 완료 | 위와 같음 |
| `reservation_cancel` | 예매 취소 | 위와 같음 |
| `sign_up` | 회원가입 완료 | `mbti` |
| `login` / `logout` | 로그인 / 로그아웃 버튼 | — |
| `profile_update` | 회원 정보 수정 | `fields` (바뀐 항목 이름, 쉼표 구분) |
| `password_change` | 비밀번호 변경 | — |
| `notification_settings_update` | 알림 설정 저장 | `booking_reminders`, `favorite_updates` |
| `account_withdraw` | 회원 탈퇴 | — |

새 type 을 추가할 때는 `frontend/src/utils/tracker.js` 의 `EVENT_TYPES` 와 `backend/app/core/config.py` 의 `TRACKING_EVENT_TYPES` 를 함께 고칩니다. 목록에 없는 type 은 프론트엔드가 보내지 않고, 서버도 422 로 거절합니다.
이메일·비밀번호 같은 개인정보는 props 에 넣지 않습니다.

## 전송 규칙

- 로그인·로그아웃 직전에 큐를 먼저 비워, 로그인 전 이벤트는 비회원으로, 로그아웃 전 이벤트는 그 회원으로 남깁니다.
- 네트워크 오류·서버 오류(5xx)·429 는 큐에 되돌려 다음 주기에 다시 보냅니다. 큐는 10개를 넘지 않게 오래된 것부터 버립니다.
- 형식 오류(4xx)는 다시 보내도 실패하므로 버립니다.
- MongoDB 에 연결할 수 없으면 서버는 503 을 돌려줍니다 (연결 대기 최대 약 2초).

## 설정 (`backend/.env`)

```
MONGODB_URL=mongodb://<user>:<password>@192.168.0.174:27017/?authSource=admin
MONGODB_DB=tikit
MONGODB_EVENTS_COLLECTION=events
```

인덱스(`type+occurred_at`, `user_id+occurred_at`, `session_id+occurred_at`)는 첫 요청 때 자동으로 만듭니다.
