# tikit

취향이 만나는 순간, **티킷(TIKIT)** — MBTI로 공연 취향을 발견하는 티켓 예매 시연 서비스입니다.

| 폴더 | 내용 | 문서 |
|---|---|---|
| `backend/` | FastAPI + MySQL API (회원·공연·예매·찜) | [backend/readme_kor.md](backend/readme_kor.md) |
| `frontend/` | nginx로 제공하는 화면 (메인·로그인·회원가입·마이페이지) | [frontend/readme_kor.md](frontend/readme_kor.md) |
| `sample/` | 처음 디자인 시안 (브라우저 저장소만 쓰는 시연 버전) | [sample/README.md](sample/README.md) |

## 빠른 실행 순서

1. **백엔드**: `backend/.env` 작성 → MySQL에 `tikit` 데이터베이스 생성 → `python -m alembic upgrade head` → `python -m app.db.seed` → `python -m uvicorn app.main:app --port 8000`
2. **프론트엔드**: `frontend/` 파일을 nginx `html` 폴더에 복사하고, `/api/` 요청을 `127.0.0.1:8000`으로 전달하도록 `nginx.conf` 설정 → nginx 시작
3. 브라우저에서 http://localhost 접속

자세한 방법과 자주 나는 오류는 각 폴더의 `readme_kor.md`를 참고하세요.
