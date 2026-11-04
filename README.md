# tikit

취향이 만나는 순간, **티킷(TIKIT)** — MBTI로 공연 취향을 발견하는 티켓 예매 시연 서비스입니다.

| 폴더 | 내용 | 문서 |
|---|---|---|
| `backend/` | FastAPI + MySQL API (회원·공연·예매·찜) | [docs/backend.md](docs/backend.md) |
| `frontend/` | Vue 3 + Vite 화면 (메인·로그인·회원가입·마이페이지·마이티킷), 빌드 결과를 nginx로 제공 | [docs/frontend.md](docs/frontend.md) |
| (기능 명세) | 예매 → 모의 결제 → 취소 기능 명세 (booking-app에서 이전) | [docs/booking.md](docs/booking.md) |
| `sample/` | 처음 디자인 시안 (브라우저 저장소만 쓰는 시연 버전) | [docs/sample.md](docs/sample.md) |

문서는 모두 [`docs/`](docs/) 폴더에 있습니다.

## 빠른 실행 순서

1. **백엔드**: `backend/.env` 작성 → MySQL에 `tikit` 데이터베이스 생성 → `python -m alembic upgrade head` (예매 테이블 0002 포함) → `python -m app.db.seed` → `python -m uvicorn app.main:app --port 8000`
2. **프론트엔드**
   - 개발: `cd frontend` → `npm install` → `npm run dev` → http://localhost:5173
   - 배포: `npm run build` → `frontend/dist/` 내용을 nginx `html` 폴더에 복사 (`/api/`는 `127.0.0.1:8000`으로 프록시, `try_files ... /index.html` 설정) → http://localhost

자세한 방법과 자주 나는 오류는 [docs/backend.md](docs/backend.md), [docs/frontend.md](docs/frontend.md)를 참고하세요.
