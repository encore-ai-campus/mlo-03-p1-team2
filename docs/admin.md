# 관리자 공연 관리

기존 Vue 3·Pinia·FastAPI·SQLAlchemy 구조에 공연 관리 기능을 추가합니다.
관리자는 `/admin/performances`에서 공연 조회·등록·수정·삭제를 할 수 있습니다.
공통 헤더·푸터, 보라색 강조색, 폰트, 입력 폼, `BaseModal`, `PosterArt`를 재사용합니다.

## 관리자 계정 준비

웹에서 가입한 기존 회원에게 서버 명령으로 권한을 부여합니다.
SSH 계정이나 DB 접속 계정과는 별개이며 기본 관리자 비밀번호는 만들지 않습니다.
일반 회원가입·프로필 수정 API에서는 관리자 권한을 설정할 수 없습니다.

먼저 백엔드의 `DATABASE_URL`이 올바른 DB를 가리키는지 확인합니다.
공유 DB에 적용할 때는 팀과 적용 시점을 맞추고, 백엔드 재시작 전에 마이그레이션합니다.

```bash
cd backend
# 기존 백엔드 가상환경 활성화 후 실행
python -m alembic upgrade head
python -m app.db.grant_admin admin@example.com
```

`admin@example.com`은 실제 가입된 회원 이메일로 바꿉니다. 계정이 없으면 마이그레이션 후
백엔드를 실행하고 웹에서 먼저 가입합니다. 권한 부여 후 로그아웃·로그인하면 상단에 **공연 관리** 메뉴가 나타납니다.
`/admin`으로 접속해도 `/admin/performances`로 이동합니다.

마이그레이션 `0004`는 `users.is_admin` Boolean 컬럼 하나를 추가합니다.
기존 회원과 신규 가입 회원은 기본적으로 일반 회원(`false`)입니다.
공연·예매·결제 테이블의 구조는 바꾸지 않습니다.
이 구현 작업에서 실제 서버 DB 마이그레이션이나 계정 승격은 실행하지 않았습니다.

## 권한 처리

- 로그인·내 정보 응답의 `is_admin`으로 메뉴와 라우터 접근을 제어합니다.
- 모든 관리자 API는 DB의 현재 사용자 권한을 다시 확인합니다. 프론트엔드 상태나 JWT에 임의의 역할을 넣어도 권한이 생기지 않습니다.
- 미로그인은 401, 일반 회원은 403입니다. 로그인 후 관리자 권한이 회수된 경우에도 API는 403을 반환하고 화면은 홈으로 이동합니다.
- 일반 회원 로그인과 기존 공연 조회·랭킹·예매 API는 그대로 사용합니다.

## API

기본 경로는 `/api/v1`이며 모든 요청에 관리자 JWT Bearer 인증이 필요합니다.

| 요청 | 설명 | 성공 |
|---|---|---|
| `GET /admin/performances` | 관리자 공연 목록 | 200 |
| `GET /admin/performances/{id}` | 공연 상세 | 200 |
| `POST /admin/performances` | 공연 등록. ID는 서버에서 UUID로 생성 | 201 |
| `PUT /admin/performances/{id}` | 공연 정보 전체 수정. ID 유지 | 200 |
| `DELETE /admin/performances/{id}` | 예매 이력이 없는 공연 삭제 | 204 |

목록 쿼리는 `q`(공연명·공연장, 최대 100자), `category`, `sort`(`date`·`title`·`price`),
`page`(기본 1, 최대 1,000,000), `page_size`(기본 10, 1~100)를 사용합니다.
응답은 `items`, `total`, `page`, `page_size`입니다. `total`은 검색 조건을 적용한 전체 건수입니다.
동일한 정렬 값은 ID로 순서를 정해 페이지 간 순서를 유지합니다.
각 항목은 기존 공연 응답과 같은 필드에 `end_date`를 추가합니다.

등록·수정 요청의 필수 필드는 다음과 같습니다.

| 필드 | 규칙 |
|---|---|
| `title` | 공연명, 공백 제외 1~200자 |
| `category` | 콘서트·뮤지컬·스포츠·전시·클래식·연극 |
| `venue` | 공연장, 공백 제외 1~200자 |
| `start_date`, `end_date` | ISO 날짜. 종료일이 시작일 이상, 기간은 최대 366일 |
| `price` | 0~536,840,911원의 정수. 프리미엄 추가금과 최대 4매의 결제 금액도 DB INT 범위 이내 |
| `slots` | 중복 없는 `HH:MM` 회차 1~24개. 서버에서 시간순 정렬 |
| `image` | `https://images.unsplash.com/photo-…` 주소 또는 기존 `photo-…` ID |

선택 필드는 `english`(포스터 제목), `sub`(부제), `style`, `badge`, `tag`입니다.
`english`가 비어 있으면 공연명을 사용합니다. `style`은 기존 포스터 스타일인
`city`, `opera`, `art`, `jazz`, `sport`, `classic`, `theater`, `dance` 중 하나입니다.
제목·부제는 최대 200자, 배지·태그는 최대 100자입니다.
이미지 주소는 기존 이미지 ID로 변환해 저장하므로 기존 `PosterArt`와 호환됩니다.

공연 기간의 `days`와 화면의 `date_label`은 서버가 시작일·종료일로 계산합니다.
기간 안의 모든 날짜에 같은 회차가 적용됩니다. 임의의 공연 ID나 추가 필드를 요청으로 덮어쓸 수 없습니다.
기존 시연 데이터에는 화면 표시 기간이 실제 예매 가능 기간보다 긴 항목이 있습니다.
관리 폼은 실제 예매 가능 기간을 보여 주며, 날짜를 그대로 두고 다른 정보만 수정하면 기존 `date_label`을 보존합니다.
날짜를 변경한 경우에는 새 기간에 맞춰 표시 문구도 다시 계산합니다.

## 수정·삭제 정책

- 공연 수정은 이후 조회와 신규 예매에 반영됩니다. 기존 예매·결제에 저장한 공연명·분류·장소·금액 스냅샷은 바꾸지 않습니다.
- 기존 `orders` 또는 `reservations`에 연결된 공연은 취소 여부와 관계없이 삭제를 막고 409를 반환합니다.
- 예매 이력이 없는 공연은 연결된 찜·조회 이벤트를 지운 뒤 공연을 삭제합니다. 확인 창에서 함께 삭제되는 기록을 안내합니다.
- 삭제와 연결 기록 정리는 같은 트랜잭션입니다. 동시 예매 등으로 외래 키 충돌이 생기면 롤백하고 409를 반환합니다.
- 없는 공연은 404, 입력 형식·기간·가격·회차 오류는 422입니다.

## 코드 위치와 확인 범위

- `backend/app/api/routes/admin.py`: 관리자 공연 CRUD
- `backend/app/schemas/admin.py`: 입력 검증과 관리자 응답
- `backend/app/api/deps.py`: 관리자 권한 의존성
- `backend/app/db/grant_admin.py`: 기존 회원 권한 부여
- `frontend/src/views/AdminPerformancesView.vue`: 목록·검색·분류·정렬·페이지 이동·삭제 확인
- `frontend/src/components/admin/PerformanceForm.vue`: 등록·수정과 카드 미리보기
- `frontend/src/composables/useAdminApi.js`: 관리자 권한 회수 처리

사용자 요청에 따라 화면 실행, 기능 테스트, 빌드, 실제 DB 반영은 생략했습니다.
정적 코드 리뷰와 Python 10개 파일·Vue 3개 컴포넌트·JavaScript 5개 모듈의 문법 검사는 수행했습니다.
관리자 권한 경계, 입력 검증, 삭제 시 예매 이력 보호, 기존 회원·예매 기능의 회귀 여부는
DB 마이그레이션 후 별도로 확인해야 합니다.
