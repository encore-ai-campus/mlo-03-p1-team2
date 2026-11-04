# TIKIT 프론트엔드

`backend/`의 FastAPI API에 연결한 티켓 예매 화면입니다. 빌드 과정이나 패키지 설치 없이 nginx에서 정적 파일로 제공합니다.
디자인은 `sample/dist`의 스타일(`styles.css`)을 그대로 사용합니다.

## 1. 폴더 구성

```
frontend/
├─ index.html          메인: 검색·카테고리 메뉴, 배너, 공연 목록, 랭킹, 예매·마이티킷(모달)
├─ login.html          로그인 페이지
├─ signup.html         회원가입 페이지
├─ mypage.html         마이페이지 (회원 정보 수정·비밀번호 변경, 준비 중 메뉴)
├─ css/styles.css      sample 스타일 + 로그인·회원가입·마이페이지 스타일
├─ js/
│  ├─ config.js        API 주소 설정 (기본값 /api/v1)
│  ├─ api.js           fetch 공통 처리, 서버 오류 → 한국어 메시지 변환
│  ├─ auth.js          가입·로그인·로그아웃·현재 사용자 조회, 토큰 보관
│  ├─ common.js        모든 페이지 공통: 헤더(카테고리 메뉴·계정 영역), 토스트, 폼 도우미, 로그인 페이지 이동
│  ├─ app.js           메인 페이지 동작
│  ├─ login.js         로그인 페이지 동작
│  ├─ signup.js        회원가입 페이지 동작
│  └─ mypage.js        마이페이지 동작
├─ nginx/templates/default.conf.template   Docker용 nginx 설정 (정적 파일 + /api/ 프록시)
└─ Dockerfile          nginx:1.27-alpine 이미지 빌드
```

모든 페이지는 `config.js → api.js → auth.js → common.js → (페이지 스크립트)` 순서로 불러옵니다(`defer`).

## 2. 화면 구성

### 공통 헤더 (모든 페이지)
- 맨 위에 검색창, 그 아래 카테고리 메뉴(홈·콘서트·뮤지컬·스포츠·전시·클래식·연극)
- 메뉴와 검색은 링크(`./?category=뮤지컬`, `./?q=재즈`)라서 로그인·회원가입·마이페이지에서 눌러도 메인의 해당 결과로 이동합니다.
- 로그인 전: `로그인` | `회원가입` | `마이티킷`
- 로그인 후: `○○님` | `마이페이지` | `로그아웃` | `마이티킷`

### 메인 (`index.html`)
- 추천 배너(3장 슬라이드), 카테고리 바로가기, 공연 카드 목록(인기순·공연일순·낮은 가격순 정렬, 더보기), MBTI 배너, 인기 랭킹
- 검색·카테고리·정렬은 서버(`GET /performances`)에서 처리하고, 현재 상태를 주소에 남깁니다. 그래서 로그인하고 돌아와도 보던 화면이 유지됩니다.
- 공연 카드를 누르면 예매 창이 열립니다: 날짜·회차·좌석 등급·수량 선택 → 모의 결제 → 완료
- 하트로 찜하기, 마이티킷에서 예매 내역·찜 목록 확인, 데이터 내려받기(JSON), 계정 삭제

### 로그인·회원가입 (`login.html`, `signup.html`)
- 별도 페이지로 이동합니다. 주소의 `next` 값으로 원래 보던 화면을 기억했다가, 성공하면 그 화면으로 돌아갑니다.
- `next`는 같은 사이트 안의 주소만 허용합니다(외부 사이트로 이동시키는 링크 차단).
- 로그인하지 않은 상태에서 결제를 누르면, 고른 날짜·회차를 현재 탭에 잠시 저장하고 로그인 페이지로 이동합니다. 로그인 후 결제 화면을 바로 다시 엽니다.
- 회원가입: 닉네임, 이메일, 비밀번호·확인(보기/숨기기), MBTI 16유형, 수집 동의. 화면에서 먼저 검사한 뒤 서버가 다시 검증합니다.

### 마이페이지 (`mypage.html`)
- 로그인하지 않았으면 로그인 페이지로 이동했다가 다시 돌아옵니다.
- 왼쪽 메뉴, 오른쪽 내용 구성이며, 메뉴마다 주소(`mypage.html#password` 등)가 있습니다.

| 메뉴 그룹 | 항목 | 상태 |
|---|---|---|
| 나의 계정 | 회원 정보 수정, 비밀번호 변경 | 동작 |
| 나의 티켓 | 예매 내역, 취소·환불 내역, 찜한 공연 | 준비 중 |
| 나의 취향 | MBTI 취향 리포트 | 준비 중 |
| 설정 | 알림 설정, 회원 탈퇴 | 준비 중 |

- 회원 정보 수정: 닉네임·이메일·MBTI. 이메일 칸을 바꿀 때만 "현재 비밀번호" 칸이 나타납니다.
- **준비 중 메뉴에 기능을 붙이는 방법:** `js/mypage.js` 위쪽 `MENU` 목록에서 해당 항목의 `soon` 문구를 지우고, 화면을 그리는 `render` 함수를 연결합니다.

## 3. 인증 처리 방식

- 가입·로그인 응답의 JWT를 **sessionStorage**(`tikit.token`)에 저장합니다. 새로고침해도 로그인이 유지되고, 탭을 닫으면 로그아웃됩니다.
- 페이지를 열 때 저장된 토큰으로 `/users/me`를 호출해 로그인 상태를 복원합니다. 만료(기본 60분)·무효 토큰이면 지우고 로그아웃 상태로 표시합니다.
- 로그인이 필요한 요청이 `401`을 받으면 토큰을 지우고 로그인 페이지로 보냅니다.
- 비밀번호는 서버로만 전송하며 브라우저에 저장하지 않습니다.
- 서버에서 받은 값과 사용자 입력은 `escapeHTML` 또는 `textContent`로만 화면에 넣어 HTML 삽입(XSS)을 막습니다.

## 4. 오류 메시지 처리 (`js/api.js`)

| 서버 응답 | 화면 메시지 |
|---|---|
| `detail`이 문자열 (409 중복, 401 로그인 실패 등) | 서버 메시지 그대로 |
| 422 검증 오류 중 서버의 한국어 메시지 | `Value error, ` 접두어를 떼고 표시 (예: 비밀번호 불일치) |
| 422 검증 오류 (형식·길이) | 항목별 한국어 문장 (예: email → "올바른 이메일 주소를 입력해 주세요.") |
| 5xx | "서버에 문제가 발생했습니다. 잠시 후 다시 시도해 주세요." |
| 네트워크 오류 | "서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요." |

## 5. 실행 방법

먼저 백엔드를 실행합니다 (`backend/readme_kor.md` 참고, 기본 `127.0.0.1:8000`).

### Windows에 설치한 nginx로 실행
1. `frontend/`의 `index.html`, `login.html`, `signup.html`, `mypage.html`, `css/`, `js/`를 nginx의 `html` 폴더로 복사합니다.
2. nginx의 `conf/nginx.conf`를 아래처럼 작성합니다.
   `default.conf.template`은 Docker 전용 조각 파일이라 **그대로 붙여 넣으면 동작하지 않습니다.** 반드시 `http { }` 안에 넣고, `${BACKEND_UPSTREAM}`은 실제 주소로 바꿔야 합니다.

```nginx
worker_processes 1;
events { worker_connections 1024; }

http {
    include       mime.types;          # 없으면 CSS/JS가 잘못된 형식으로 전달되어 브라우저가 차단함
    default_type  application/octet-stream;
    sendfile      on;

    server {
        listen 80;
        server_name localhost;
        root html;
        index index.html;
        charset utf-8;

        # 보안 헤더와 아래 location 설정은 default.conf.template 내용을 그대로 복사

        location /api/ {
            proxy_pass http://127.0.0.1:8000;   # ${BACKEND_UPSTREAM} 대신 직접 지정
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }

        location / {
            try_files $uri $uri/ /index.html;
        }
    }
}
```

3. nginx 폴더에서 `nginx -t`로 설정을 검사하고 `start nginx`로 시작합니다. 설정이나 파일을 바꾼 뒤에는 `nginx -s reload`를 실행합니다.
4. http://localhost 접속

자주 나는 오류:
| 오류 | 원인 |
|---|---|
| `"server" directive is not allowed here` | `server { }`가 `http { }` 밖에 있음 |
| `unknown "BACKEND_UPSTREAM" variable` | template의 변수를 바꾸지 않음 |
| 화면은 나오는데 API가 502 | 백엔드(8000번)가 꺼져 있음 |

> `frontend/`를 수정하면 nginx `html` 폴더에도 다시 복사해야 반영됩니다.

### Docker로 실행
```powershell
cd frontend
docker build -t tikit-frontend .
docker run --rm -p 8080:80 tikit-frontend
# 백엔드 주소가 다르면: docker run --rm -p 8080:80 -e BACKEND_UPSTREAM=backend:8000 tikit-frontend
```
http://localhost:8080 접속. 기본 `BACKEND_UPSTREAM`은 `host.docker.internal:8000`(호스트 PC에서 실행 중인 uvicorn)입니다.

### 프록시 없이 개발할 때
`js/config.js`의 `apiBase`를 `'http://localhost:8000/api/v1'`로 바꾸고 `python -m http.server 5173 --directory frontend`로 실행합니다. 백엔드 CORS 기본값이 `http://localhost:5173`을 허용합니다. 이 경우 nginx 보안 헤더는 적용되지 않습니다.

## 6. nginx 보안 설정

- `Content-Security-Policy`: 자체 스크립트만 허용(인라인 스크립트 금지), 외부는 Google Fonts·Unsplash 이미지만 허용
- `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`
- css/js는 `Cache-Control: no-cache`로 수정 사항이 바로 반영됩니다.

## 7. 남은 작업

- 마이페이지 준비 중 메뉴: 예매 내역, 취소·환불 내역, 찜한 공연, MBTI 취향 리포트, 알림 설정, 회원 탈퇴
  (예매 내역·찜·탈퇴는 지금은 메인의 마이티킷 창에서 이용할 수 있습니다)
- 비밀번호 찾기, 이메일 인증, 로그인 유지 기간 연장(refresh token)
