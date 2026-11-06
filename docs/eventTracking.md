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
| `session_id` | 탭 단위 UUID (`sessionStorage`). 시간 제한으로 자동 교체하지 않으며 새로고침해도 유지됩니다. |
| `anonymous_id` | 브라우저 단위 UUID (`localStorage`). 로그인과 무관하게 유지 |
| `page.path` / `page.referrer` | 이벤트가 일어난 화면 주소, 직전 화면 주소 |
| `props` | type 별 추가 정보. 한 단계 값(문자열·숫자·불리언·null)만, 최대 20개, 문자열 500자 |

서버가 저장할 때 추가하는 필드: `user_id`(JWT 토큰에서만 추출, 비회원·만료 토큰이면 `null`), `user_agent`, `received_at`.

요청 본문은 `{"events": [...]}`이며 한 번에 1~10건을 받습니다. 이벤트의
`event_id`, `type`, `occurred_at`, `session_id`, `anonymous_id`, `page`,
`schema_version`은 필수이며 `props`는 생략하면 빈 객체가 됩니다.
`page.path`는 필수, `page.referrer`는 기본 빈 문자열이고 각각 최대 500자입니다.
`props` 키는 1~40자이며 값은 문자열·숫자·불리언·null만 허용합니다.
현재 프론트엔드가 보내는 `schema_version`은 정수 `1`이며 서버의 허용 범위는 1~100입니다.
이벤트와 `page`에는 정의되지 않은 필드를 추가할 수 없습니다.
타입별 주요 props는 아래의 화면 기록 관례이며, 서버가 타입별 필수 props나
공연·예매의 존재 및 행동 순서까지 검증하는 것은 아닙니다.

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

## MySQL 이벤트와의 구분

MongoDB 행동 로그와 MySQL 업무 이벤트는 목적과 이름이 다릅니다.

| 행동 | MongoDB `/api/v1/tracking/events` | MySQL 업무 이벤트 |
|---|---|---|
| 공연 상세 조회 | `performance_view` | `performance_view` |
| 예매 시작 | `booking_start` | `booking_started` |
| 예매 요청 성공 | `reservation_request` | `reservation_requested` |
| 모의 결제 완료 | `payment_complete` | `payment_completed` (기존 orders 경로는 `mock_purchase`) |
| 예매 취소 | `reservation_cancel` | `reservation_cancelled` |

MySQL의 `/api/v1/events` 요청으로 보낼 수 있는 type은 `performance_view`와
`booking_started`입니다. 예매 요청·결제·취소에 대한 MySQL 이벤트는 해당 업무
API가 기록합니다. MongoDB 수집 API에 `payment_complete`를 보내는 것만으로
실제 예매·결제 상태나 MySQL 이벤트가 만들어지지는 않습니다.
예매 API의 MySQL 업무 이벤트는 수집에 동의한 사용자에 대해서만 기록합니다.

## 페르소나 기반 합성 로그

[`syntheticData/personas.json`](../syntheticData/personas.json)은 가상 사용자
프로필이며 회원 계정이나 행동 로그가 아닙니다. 생성기와 활용 절차는
[페르소나 데이터 설계](personaDataDesign.md)에 정리되어 있습니다.
현재 저장소의 페르소나 생성기는 이벤트 생성·API 전송·DB 적재를 하지 않습니다.

후속 생성기에서는 사용자별 방문 세션을 만들고, `category_weights`로 관심
카테고리를 선택한 뒤 조회 → 찜·예매 → 결제·이탈 흐름을 시간순으로 만들 수 있습니다.
관람 빈도와 사이트 방문 빈도는 구분하고 전환 확률은 별도 설정으로 기록합니다.
MBTI를 근거로 취향이나 구매율을 고정하지 않습니다.

### 식별자와 프로필 연결

- `event_id`: 행동마다 새 UUID를 사용합니다. 동일 이벤트를 재전송할 때는 유지합니다.
- `session_id`: 같은 가상 방문 안에서는 유지합니다. 실제 화면의 탭 단위 식별자와
  다른 세션 정의를 쓴다면 생성 설정에 명시합니다.
- `anonymous_id`: 같은 가상 브라우저에서는 방문·로그인 여부와 무관하게 유지합니다.
  회원 ID나 세션 ID와는 별개의 식별자입니다.
- 파일 기반 분석에서는 `synthetic_user_id`와 `event`를 담은 별도 외부 객체로
  프로필의 `users[].id`와 연결할 수 있습니다. 이 외부 객체는 API로 보낼 수 없습니다.
- 기존 API는 이벤트 최상위 `user_id`, `synthetic_user_id`, `mbti` 등을 받지 않습니다.
  `user_id`는 검증된 JWT에서만 추출합니다. 프로필 ID를 넣는 것만으로 회원 연결이
  되지 않으며, 테스트 회원을 사용할 경우 별도 가입·인증·ID 매핑이 필요합니다.

### 저장과 검증

합성 로그는 별도 파일 또는 테스트용 DB·컬렉션에 저장합니다. 테스트 수집 서버의
`MONGODB_DB`, `MONGODB_EVENTS_COLLECTION` 설정으로 대상을 분리할 수 있습니다.
현재 API에는 요청별로 저장 컬렉션을 선택하는 기능이 없습니다.
생성 실행 정보에는 합성 여부, 실행 ID, 생성기 버전·시드, 기간, 전환 규칙,
사용한 공연 데이터 버전을 남깁니다. 프로필 스키마 버전과 이벤트 스키마 버전은 별개입니다.

생성 결과에서는 다음을 별도로 확인합니다. 현재 수집 API가 모두 보장하는 검증은 아닙니다.

- 사용자별 프로필 연결과 브라우저·세션 식별자의 일관성
- 이벤트 ID의 고유성, 세션 내 발생 시각 순서와 시간대(예: UTC `Z`)
- 허용된 type, 실제 공연 데이터와 일치하는 ID·카테고리·가격·예매 일정
- 예매 요청 뒤 결제, 생성된 예매에 대한 취소 등 행동 순서와 `reservation_id`의 일관성
- 조회 후 이탈·찜 후 이탈 등 여러 경로 및 생성 설정에 맞는 분포

합성 결제 로그는 실제 결제가 이루어졌다는 증거가 아닙니다. 또한 프로필의 취향을
규칙으로 넣어 만든 로그는 실제 사용자 취향이나 추천 성능을 입증하지 않습니다.

## 전송 규칙

- 로그인·로그아웃 직전에 큐를 먼저 비워, 로그인 전 이벤트는 비회원으로, 로그아웃 전 이벤트는 그 회원으로 남깁니다.
- 네트워크 오류·서버 오류(5xx)·429 는 큐에 되돌려 다음 주기에 다시 보냅니다. 큐는 10개를 넘지 않게 오래된 것부터 버립니다.
- 형식 오류(4xx)는 다시 보내도 실패하므로 버립니다.
- MongoDB 에 연결할 수 없으면 서버는 503 을 돌려줍니다 (연결 대기 최대 약 2초).

수집 성공 시 HTTP `202`와 `{"accepted": 2, "duplicates": 0}`처럼 저장·중복
건수를 반환합니다. `accepted`는 새로 저장된 건수입니다. 이미 저장한
`event_id`를 다시 보내면 `duplicates`에 집계됩니다. 빈 배치, 10건 초과,
미허용 type 등 형식 오류는 `422`입니다. 중복 외 저장 오류는 `503`이며 일부가
이미 저장됐을 수 있으므로 재시도할 때 기존 `event_id`를 유지합니다.

## 설정 (`backend/.env`)

```
MONGODB_URL=mongodb://<user>:<password>@192.168.0.174:27017/?authSource=admin
MONGODB_DB=tikit
MONGODB_EVENTS_COLLECTION=events
```

인덱스(`type+occurred_at`, `user_id+occurred_at`, `session_id+occurred_at`)는 첫 요청 때 자동으로 만듭니다.
