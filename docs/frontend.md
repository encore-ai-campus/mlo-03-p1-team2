# TIKIT 프론트엔드 (Vue 3)

`backend/`의 FastAPI API에 연결한 티켓 예매 화면입니다. **Vue 3 + Vite + Vue Router + Pinia**로 만들었고, 빌드 결과(`dist/`)를 nginx에서 제공합니다.
디자인은 `sample/dist`의 스타일(`styles.css`)을 그대로 사용합니다.

## 1. 폴더 구성

```
frontend/
├─ index.html                 Vite 진입점 (#app)
├─ package.json, vite.config.js   의존성·빌드 설정 (개발 서버의 /api 프록시 포함)
├─ src/
│  ├─ main.js                 앱 생성, router·pinia 등록, styles.css 불러오기
│  ├─ App.vue                 공통 헤더 + 화면(RouterView) + 푸터 + 토스트
│  ├─ assets/styles.css       sample 스타일 + 로그인·회원가입·마이페이지 스타일
│  ├─ router/index.js         주소 ↔ 화면 연결, 로그인 필요 화면 보호, 예전 .html 주소 호환
│  ├─ stores/auth.js          로그인 상태(Pinia): 가입·로그인·로그아웃·상태 복원, 토큰 보관
│  ├─ api/client.js           fetch 공통 처리, 서버 오류 → 한국어 메시지 변환
│  ├─ composables/
│  │  ├─ useToast.js          화면 하단 알림
│  │  └─ useAuthedApi.js      로그인이 필요한 API 호출 (401이면 로그인 화면으로)
│  ├─ utils/index.js          카테고리·MBTI 목록, 금액·날짜 표시, safeNext, sessionStorage 도우미
│  ├─ views/                  화면 단위 컴포넌트
│  │  ├─ HomeView.vue         메인: 배너, 카테고리, 공연 목록, 랭킹, 모달 열기
│  │  ├─ LoginView.vue, SignupView.vue
│  │  └─ MyPageView.vue       마이페이지 (메뉴 설정 MENU)
│  └─ components/             재사용 컴포넌트
│     ├─ AppHeader.vue, AppFooter.vue
│     ├─ HeroSlider.vue, PerformanceCard.vue, PosterArt.vue, RankingList.vue, CategoryIcon.vue
│     ├─ BaseModal.vue        <dialog> 공통 틀 (제목·닫기·배경 클릭·Esc)
│     ├─ BookingModal.vue     예매: 날짜·회차 → 모의 결제 → 완료
│     ├─ MyTicketModal.vue    마이티킷: 예매 내역·찜·데이터 내려받기·계정 삭제
│     ├─ TasteModal.vue       MBTI 취향 찾기
│     ├─ PasswordField.vue    비밀번호 입력 + 보기/숨기기
│     └─ mypage/              ProfileForm, PasswordForm, ComingSoon, PanelHead
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
| `/?open=mytikit`, `/?open=taste` | 메인 + 마이티킷/취향 창 | 한 번 열고 주소에서 지움. 로그인 필요 시 로그인 후 다시 열림 |
| `/login.html`, `/mypage.html#password` 등 | 예전 주소 | 새 주소로 자동 이동 |

### 공통 헤더
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
| 나의 티켓 | 예매 내역, 취소·환불 내역, 찜한 공연 | 준비 중 |
| 나의 취향 | MBTI 취향 리포트 | 준비 중 |
| 설정 | 알림 설정, 회원 탈퇴 | 준비 중 |

- 회원 정보 수정: 닉네임·이메일·MBTI. 이메일 칸을 바꿀 때만 "현재 비밀번호" 칸이 나타납니다.
- **준비 중 메뉴에 기능을 붙이는 방법:** `src/components/mypage/`에 화면 컴포넌트를 만들고, `src/views/MyPageView.vue`의 `MENU`에서 해당 항목의 `soon`을 지우고 `component`에 연결합니다.

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

- 마이페이지 준비 중 메뉴: 예매 내역, 취소·환불 내역, 찜한 공연, MBTI 취향 리포트, 알림 설정, 회원 탈퇴
  (예매 내역·찜·탈퇴는 지금은 메인의 마이티킷 창에서 이용할 수 있습니다)
- 비밀번호 찾기, 이메일 인증, 로그인 유지 기간 연장(refresh token)
