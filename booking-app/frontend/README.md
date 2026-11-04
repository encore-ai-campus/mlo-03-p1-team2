# TIKIT Vue 프론트엔드

기존 `static/` 화면을 Vue 3 + Vite로 옮긴 프로젝트입니다. 공연 검색·분류·정렬,
찜, 추천 배너, 회원가입·로그인, 예매, 결제·취소, 마이티킷, MBTI 취향 탐색을 제공합니다.
화면 데이터는 Vue의 반응형 상태와 템플릿으로 관리하며 기존 Python API와 SQLite를 사용합니다.

## 빌드 후 서버 하나로 실행

Node.js 22.12 이상이 필요합니다. `node --version`과 `npm --version`으로 확인하세요.
NVM이 설치되어 있는데 활성 버전이 없다고 나오면, 설치된 버전을 `nvm list`로 확인하고
`nvm use 24.22.0`처럼 선택한 뒤 터미널을 다시 여세요.

`booking-app`을 기준으로 실행합니다.

```powershell
cd frontend
npm ci
npm run build
cd ..
python server.py
```

**http://127.0.0.1:8000**에서 Vue 화면과 API를 함께 사용합니다.
Python 서버는 `frontend/dist/`만 화면 파일로 제공하며 기존 `static/`은 사용하지 않습니다.
빌드가 없으면 503 오류와 빌드 명령을 표시하지만 API는 계속 사용할 수 있습니다.
Vue 소스를 수정한 뒤에는 `npm run build`를 다시 실행하고 브라우저를 새로고침하세요.

## 화면 개발 중 자동 갱신

수정 내용을 바로 반영하려면 Python 서버를 켠 상태에서 별도 터미널에 개발 서버를 실행합니다.

```powershell
cd frontend
npm run dev
```

브라우저에서 **http://127.0.0.1:5173**을 여세요. 이 방식은 개발 중에만 선택적으로 사용합니다.
Vite가 `/api` 요청을 `http://127.0.0.1:8000`으로 전달합니다.
세션은 HttpOnly 쿠키를 사용합니다. 개발 프록시는 동일 출처 요청의 Origin만 백엔드
주소로 변환하므로 Python 서버의 출처 검사를 유지합니다.

8000번과 5173번 화면은 같은 백엔드 DB를 사용합니다. 브라우저 찜 목록은
출처별 localStorage에 저장되므로 서로 다른 포트 간에 공유되지 않습니다.

## 구조

```text
frontend/
  index.html
  package.json
  package-lock.json
  vite.config.js           # 개발 및 미리보기 API 프록시
  src/
    main.js               # Vue 시작점
    App.vue               # 공통 헤더·푸터, 화면 전환, 로그인 상태
    api.js                # Python API 호출
    utils.js              # 금액·날짜 표시
    styles.css            # 기존 디자인과 반응형 스타일
    components/
      HomePage.vue        # 검색, 공연 목록, 배너, 랭킹
      ShowPoster.vue      # 재사용하는 공연 포스터
      AuthForm.vue        # 로그인·회원가입
      BookingPanel.vue    # 예매 선택·확인·완료
      TicketsPage.vue     # 예매·결제 내역
      ModalDialog.vue     # 공통 대화상자
```

`/#my-tickets`로 직접 접속하거나 새로고침해도 마이티킷이 열립니다.
`node_modules/`, `dist/`는 자동 생성 파일이므로 커밋에서 제외하며,
`package-lock.json`은 함께 커밋합니다.

## 빌드 및 미리보기

```powershell
npm run build
npm run preview
```

빌드 결과는 `frontend/dist/`에 생성됩니다. Python 서버를 실행한 상태에서
**http://127.0.0.1:4173**에서도 결과를 확인할 수 있습니다.
일반적인 실행은 미리보기 서버 없이 `python server.py`와 **8000번** 주소만 사용하면 됩니다.

## 브라우저 검증

기존 `tests/browser-smoke.cjs`로 Vue 화면도 검사할 수 있습니다.
테스트 계정과 예매가 생성되므로 첫 번째 터미널은 실제 DB 대신 임시 DB로 실행하세요.

```powershell
# booking-app에서 실행. 기존 8000번 서버는 먼저 종료합니다.
python server.py --db "$env:TEMP/tikit-vue-test.sqlite3"
```

빌드 후 테스트 서버를 실행하고, Playwright가 설치된 환경에서 `booking-app` 기준으로 실행합니다.

```powershell
$env:BASE_URL = 'http://127.0.0.1:8000'
node tests/browser-smoke.cjs <Playwright 패키지 경로>
```

Playwright가 Node 모듈 검색 경로에 설치되어 있으면 마지막 경로는 생략할 수 있습니다.
검사 화면 캡처는 `tests/artifacts/`에 생성됩니다.

Vue와 Vite의 기본 사용법은 [Vue 공식 가이드](https://vuejs.org/guide/quick-start.html)와
[Vite 프록시 문서](https://vite.dev/config/server-options#server-proxy)를 참고하세요.
