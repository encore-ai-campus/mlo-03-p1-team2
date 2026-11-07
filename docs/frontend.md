# TIKIT 프론트엔드 (Vue 3)

`backend/`의 FastAPI API에 연결한 티켓 예매 화면입니다. **Vue 3 + Vite + Vue Router + Pinia**로 만들었고, 빌드 결과(`dist/`)를 nginx에서 제공합니다.
공통 스타일은 `frontend/src/assets/styles.css`, 홈 디자인의 기존 기준값은
[homeDesign.md](homeDesign.md)에서 관리합니다. 예매 상세는 [booking.md](booking.md),
마이페이지 API·집계 규칙은 [mypageApi.md](mypageApi.md)를 참고하세요.

## 1. 폴더 구성

```
frontend/
├─ index.html                 Vite 진입점 (#app)
├─ package.json, vite.config.js   의존성·빌드 설정 (개발 서버의 /api 프록시 포함)
├─ src/
│  ├─ main.js                 앱 생성, router·pinia 등록, styles.css 불러오기
│  ├─ App.vue                 공통 헤더 + 화면(RouterView) + 푸터 + 토스트
│  ├─ assets/styles.css       홈·로그인·회원가입·마이페이지 공통 스타일
│  ├─ router/index.js         주소 ↔ 화면 연결, 로그인 필요 화면 보호, 예전 .html 주소 호환
│  ├─ stores/auth.js          로그인 상태(Pinia): 가입·로그인·로그아웃·상태 복원, 토큰 보관
│  ├─ stores/favorites.js     홈과 마이페이지가 공유하는 서버 찜 상태
│  ├─ api/client.js           fetch 공통 처리, 서버 오류 → 한국어 메시지 변환
│  ├─ composables/
│  │  ├─ useToast.js          화면 하단 알림
│  │  ├─ useReservations.js   예매·결제·취소 API
│  │  ├─ useAdminApi.js       관리자 API와 권한 오류 처리
│  │  └─ useAuthedApi.js      로그인이 필요한 API 호출 (401이면 로그인 화면으로)
│  ├─ utils/index.js          카테고리·MBTI 목록, 금액·날짜 표시, safeNext, sessionStorage 도우미
│  ├─ views/                  화면 단위 컴포넌트
│  │  ├─ HomeView.vue         메인: 배너, 카테고리, 공연 목록, 랭킹, 모달 열기
│  │  ├─ LoginView.vue, SignupView.vue
│  │  ├─ MyPageView.vue       마이페이지 (메뉴 설정 MENU)
│  │  └─ AdminPerformancesView.vue   관리자 공연 관리
│  └─ components/             재사용 컴포넌트
│     ├─ AppHeader.vue, AppFooter.vue
│     ├─ HeroSlider.vue, PerformanceCard.vue, PosterArt.vue, RankingList.vue, CategoryIcon.vue
│     ├─ BaseModal.vue        <dialog> 공통 틀 (제목·닫기·배경 클릭·Esc)
│     ├─ BookingModal.vue     예매: 날짜·회차 → 모의 결제 → 완료
│     ├─ TasteModal.vue       MBTI 취향 찾기
│     ├─ PasswordField.vue    비밀번호 입력 + 보기/숨기기
│     └─ mypage/              계정·예매·찜·리포트·알림·탈퇴 패널
├─ public/                    그대로 복사되는 정적 파일
├─ nginx/templates/default.conf.template   Docker용 nginx 설정
└─ Dockerfile                 Node로 빌드 → nginx 이미지에 dist 복사 (2단계)
```

## 2. 화면과 주소

| 주소 | 화면 | 비고 |
|---|---|---|
| `/` | 메인 | `?category=뮤지컬`, `?q=재즈`, `?sort=price` 로 목록 상태를 표현 |
| `/login`, `/signup` | 로그인·회원가입 | `?next=` 로 로그인 후 돌아갈 주소 전달. 이미 로그인했으면 바로 next로 이동 |
| `/mypage/:메뉴` | 마이페이지 | 예: `/mypage/password`. 로그인하지 않았으면 로그인 화면으로 이동 후 복귀 |
| `/mypage/orders`, `/my-tickets` | 예매 내역 | `/my-tickets`는 `/mypage/orders`로 이동하는 호환 주소 |
| `/admin/performances` | 관리자 공연 관리 | 관리자만 조회·등록·수정·삭제 가능. `/admin`도 이 주소로 이동 |
| `/?open=mytikit`, `/?open=taste` | 이전 마이티킷 주소 / 취향 창 | `mytikit`은 `/mypage/orders`로 이동. `taste`는 취향 창 표시 |
| `/login.html`, `/mypage.html#password` 등 | 예전 주소 | 새 주소로 자동 이동 |

### 공통 헤더
- 관리자 계정에는 **공연 관리** 메뉴가 추가됩니다. 계정 준비·화면·API는 [관리자 공연 관리](admin.md)를 참고하세요.
- 맨 위 검색창, 그 아래 카테고리 메뉴(홈·콘서트·뮤지컬·스포츠·전시·클래식·연극). 어느 화면에서 눌러도 메인의 해당 결과로 이동합니다.
- 로그인 전: `로그인` | `회원가입` | `마이티킷` / 로그인 후: `○○님` | `마이페이지` | `로그아웃` | `마이티킷`
- 화면 이동은 새로고침 없이 이루어지고(SPA), 로그인 상태는 모든 화면이 Pinia 스토어 하나를 공유합니다.

### 메인
- 추천 배너(3장), 카테고리 바로가기, 공연 카드 목록(인기순·공연일순·낮은 가격순, 더보기), MBTI 배너, 인기 랭킹
- 검색·카테고리·정렬은 서버(`GET /performances`)에서 처리하고, 상태는 주소에 남깁니다. 그래서 로그인하고 돌아와도 보던 화면이 유지됩니다.
- 공연 카드 → 예매 창: 날짜·회차·좌석 등급·수량 → 모의 결제 → 완료
- 로그인하지 않은 상태에서 결제를 누르면, 고른 값을 sessionStorage(`tikit.pendingBooking`)에 잠시 저장하고 로그인 화면으로 이동합니다. 로그인(또는 가입) 후 결제 단계가 바로 다시 열립니다.

### 마이페이지
| 메뉴 그룹 | 항목 | 상태 |
|---|---|---|
| 나의 계정 | 회원 정보 수정, 비밀번호 변경 | 동작 |
| 나의 티켓 | 예매 내역, 찜한 공연 | `OrdersPanel`, `FavoritesPanel` 연결 |
| 나의 취향 | MBTI 취향 리포트 | `TasteReportPanel` 연결 |
| 설정 | 알림 설정, 회원 탈퇴 | `NotificationsPanel`, `WithdrawPanel` 연결 |

- 회원 정보 수정: 닉네임·이메일·MBTI. 이메일 칸을 바꿀 때만 "현재 비밀번호" 칸이 나타납니다.
- 예매 내역은 결제·취소와 이전 모의 예매를 표시합니다. 찜은 독립 패널에서 홈과 같은 상태를 사용합니다.
- 리포트·알림 조건·탈퇴와 DB 적용은 [mypageApi.md](mypageApi.md), 예매 상태 전이는 [booking.md](booking.md)를 따릅니다.

## 3. 인증 처리 방식

- 가입·로그인 응답의 JWT를 **sessionStorage**(`tikit.token`)에 저장합니다. 새로고침해도 로그인이 유지되고, 탭을 닫으면 로그아웃됩니다.
- 앱이 시작될 때 저장된 토큰으로 `/users/me`를 호출해 로그인 상태를 복원합니다(`auth.restore()`). 만료·무효 토큰이면 지웁니다.
- 로그인이 필요한 요청이 `401`을 받으면 토큰을 지우고 로그인 화면으로 보냅니다(`useAuthedApi`).
- 로그인 후 이동할 `next`는 같은 사이트 안의 주소만 허용합니다(`safeNext`, 외부 사이트로 이동시키는 링크 차단).
- 화면 출력은 모두 Vue 템플릿 바인딩(`{{ }}`)이라 자동으로 이스케이프됩니다. `v-html`은 사용하지 않습니다(HTML 삽입·XSS 방지).

## 4. 오류 메시지 처리 (`src/api/client.js`)

| 서버 응답 | 화면 메시지 |
|---|---|
| `detail`이 문자열 (409 중복, 401 로그인 실패 등) | 서버 메시지 그대로 |
| 422 검증 오류 중 서버의 한국어 메시지 | `Value error, ` 접두어를 떼고 표시 |
| 422 검증 오류 (형식·길이) | 항목별 한국어 문장 (예: email → "올바른 이메일 주소를 입력해 주세요.") |
| 5xx | "서버에 문제가 발생했습니다. 잠시 후 다시 시도해 주세요." |
| 네트워크 오류 | "서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요." |

## 5. 실행 방법

먼저 백엔드를 실행합니다 ([backend.md](backend.md) 참고, 기본 `127.0.0.1:8000`). Node.js 18 이상이 필요합니다.

### 개발 (코드 수정하며 확인)
```powershell
cd frontend
npm install        # 처음 한 번
npm run dev        # http://localhost:5173
```
- `/api` 요청은 Vite 개발 서버가 `http://127.0.0.1:8000`으로 전달합니다(`vite.config.js`). 백엔드 CORS 설정은 필요 없습니다.
- 백엔드 주소가 다르면 `$env:BACKEND_URL="http://주소:포트"; npm run dev`
- 파일을 저장하면 화면이 바로 갱신됩니다.

### Windows에 설치한 nginx로 실행

아래는 로컬 개발용 구성입니다. 팀 서버의 HAProxy·nginx·TLS 배포 순서는
[FrontToBackSetting.md](FrontToBackSetting.md)를 따릅니다.
1. `npm run build` → `frontend/dist/`에 `index.html`과 `assets/`가 만들어집니다.
2. nginx `html` 폴더의 기존 파일을 지우고 `dist/` **안의 내용**을 복사합니다.
   (예전 `login.html` 등이 남아 있으면 새 주소 대신 옛 화면이 열립니다.)
3. `conf/nginx.conf`는 아래 두 가지만 있으면 됩니다. 이미 설정했다면 바꿀 필요 없습니다.
   - `/api/` → `proxy_pass http://127.0.0.1:8000;`
   - `location / { try_files $uri $uri/ /index.html; }` ← `/mypage/password`에서 새로고침해도 404가 나지 않게 함
4. `nginx -s reload` (처음이면 `start nginx`) 후 http://localhost 접속

자주 나는 오류:
| 오류 | 원인 |
|---|---|
| `"server" directive is not allowed here` | `server { }`가 `http { }` 밖에 있음 |
| `unknown "BACKEND_UPSTREAM" variable` | template의 변수를 실제 주소로 바꾸지 않음 |
| 화면은 나오는데 API가 502 | 백엔드(8000번)가 꺼져 있음 |
| `/login` 등에서 새로고침하면 404 | `try_files ... /index.html` 설정 누락 |
| 빈 화면 + 콘솔에 MIME type 오류 | `include mime.types;` 누락 |

### Docker로 실행
```powershell
cd frontend
docker build -t tikit-frontend .
docker run --rm -p 8080:80 tikit-frontend
# 백엔드 주소가 다르면: docker run --rm -p 8080:80 -e BACKEND_UPSTREAM=backend:8000 tikit-frontend
```
이미지 안에서 `npm ci && npm run build`를 실행하므로 PC에 Node가 없어도 됩니다.

### 프록시 없이 백엔드에 직접 연결할 때
`frontend/.env.local`에 `VITE_API_BASE=http://localhost:8000/api/v1`을 적고 다시 빌드합니다. 백엔드 CORS 기본값이 `http://localhost:5173`을 허용합니다.

## 6. nginx 보안·캐시 설정

- `Content-Security-Policy`: 자체 스크립트만 허용(인라인 스크립트 금지), 외부는 Google Fonts·Unsplash 이미지만 허용. Vue 템플릿은 빌드 때 미리 변환되므로 이 정책에서 그대로 동작합니다.
- `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`
- `/assets/`: 파일명에 내용 해시가 붙으므로 1년 캐시. `index.html`: `no-cache`로 새 배포가 바로 반영됩니다.

## 7. 남은 작업

- 비밀번호 찾기, 이메일 인증, 로그인 유지 기간 연장(refresh token)
- 좌석 재고·실제 결제·환불 및 외부 메일·문자·푸시 연동은 현재 범위에 포함하지 않습니다.
