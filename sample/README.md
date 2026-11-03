# TIKIT · 티킷

보라색 기반의 반응형 티켓 예매 프론트엔드. 패키지 설치와 빌드 없이 실행합니다.

## 실행

프로젝트 루트에서 실행한 후 http://localhost:5173 에 접속합니다.

```powershell
python -m http.server 5173 --directory ticket-platform/dist
```

## 기능

- 콘서트·뮤지컬·스포츠·전시·클래식·연극 탐색, 검색, 정렬, 찜, 랭킹
- 닉네임·이메일·비밀번호·비밀번호 확인·MBTI(16유형)·수집 동의 필수 가입
- 이메일 중복 검사, 비밀번호 일치 검사, 비밀번호 표시 전환
- 이메일·비밀번호 로그인, 로그아웃, 새로고침 시 현재 탭 로그인 유지
- 공연 상세에서 날짜·회차·좌석 등급·수량 선택 및 금액 계산
- 모의 결제, 사용자별 예매 내역, JSON 다운로드, 계정 및 연결 데이터 삭제

## 시연용 인증

같은 브라우저에 저장된 계정으로 로그인합니다. 로그아웃해도 가입 정보와 예매 내역은 유지됩니다. 비밀번호는 PBKDF2-SHA-256(210,000회)과 무작위 16바이트 솔트를 사용한 검증값으로 저장하며 원문은 보관하지 않습니다. JSON 내보내기에 검증값은 포함하지 않습니다. 실제 사용하는 비밀번호는 입력하지 마세요.

서버 인증, 기기 간 연동, 이메일 확인, 비밀번호 재설정은 구현하지 않았습니다. 브라우저 저장 데이터는 사용자가 변경할 수 있으므로 실서비스 인증으로 사용할 수 없습니다. 실제 서비스 연결 시 `auth.js`의 `demoAuth`를 서버 인증 요청으로 교체하고 브라우저의 비밀번호 검증값 저장을 제거해야 합니다.

이전 버전에서 비밀번호 없이 만든 프로필은 같은 이메일로 재가입해 비밀번호를 설정하면 기존 ID와 예매 내역을 이어받습니다. 이전 시연 프로필에 한정된 이전 처리입니다.

## 저장 데이터 및 DB 연동 지점

- `tikit.accounts` (localStorage): id, name, email, mbti, consent, consentedAt, credentials(algorithm, iterations, salt, hash)
- `tikit.session` (sessionStorage): 로그인한 계정 ID
- `tikit.orders`: id, userId, mbti, performanceId, performanceTitle, category, venue, performanceDate, sessionTime, seatGrade, quantity, unitPrice, amount, currency, paymentMethod, status(`MOCK_PAID`), isMock, createdAt
- `tikit.events`: id, userId, mbti, type(`performance_view`/`mock_purchase`), performanceId, category, createdAt
- `tikit.favorites`: 찜한 공연 ID 배열
- `tikit.profile`: 이전 버전 프로필. 비밀번호 설정 가입 시 이전 후 삭제

데이터는 현재 브라우저에만 저장됩니다. `app.js`의 `paymentForm` 제출 처리에서 주문 객체를 만듭니다. 향후 주문 저장 API에 연결하고 서버에서 인증·가격·잔여 좌석을 검증한 후 저장 성공 시 완료 화면을 표시해야 합니다. 카드번호·계좌번호는 수집하지 않습니다. 좌석은 등급만 선택하며 실제 좌석 재고와 번호는 관리하지 않습니다.

## 확인 항목

회원가입 후 로그아웃하고 같은 이메일·비밀번호로 다시 로그인합니다. 틀린 비밀번호, 중복 이메일, 비밀번호 확인 불일치는 거절됩니다. 예매 중 로그인·회원가입을 전환해도 날짜·회차 선택이 유지됩니다. 마이티킷 데이터 삭제는 계정과 검증값도 삭제합니다.

공연 일정과 가격은 시연 데이터입니다. MBTI 추천은 E/I에 따른 탐색 예시이며 실제 통계가 아닙니다. 이미지는 Unsplash, 폰트는 Google Fonts에서 불러옵니다. 참고 사이트 YES24는 자동 접근 제한으로 직접 확인하지 못해 자체 디자인으로 구현했습니다.
