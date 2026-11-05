# Git 커밋 메시지 컨벤션

## 1. Git 커밋 메시지 종류

| 타입 | 의미 | 사용 예시 |
|---|---|---|
| `[feat]` | 새로운 기능 추가 | 회원가입 기능 구현 |
| `[fix]` | 버그 및 오류 수정 | 로그인 오류 수정 |
| `[add]` | 파일, 리소스 추가 | 이미지 파일 추가 |
| `[update]` | 기존 기능이나 내용 변경 | 공연 정보 수정 |
| `[refactor]` | 코드 리팩토링 | 중복 코드 제거 |
| `[docs]` | 문서 추가 및 수정 | README 수정 |
| `[style]` | 코드 스타일 변경 | 들여쓰기, 공백 수정 |
| `[test]` | 테스트 코드 추가 및 수정 | 회원가입 테스트 추가 |
| `[chore]` | 기타 작업 및 환경 설정 | .gitignore 수정 |
| `[build]` | 빌드 및 의존성 변경 | 라이브러리 추가 |
| `[ci]` | CI/CD 설정 변경 | GitHub Actions 수정 |
| `[perf]` | 성능 개선 | DB 조회 속도 개선 |
| `[remove]` | 파일이나 기능 삭제 | 불필요한 파일 삭제 |
| `[revert]` | 이전 커밋 되돌리기 | 로그인 변경 사항 복구 |

## 2. 커밋 메시지 작성 규칙

커밋 메시지는 아래 형식을 따른다.

`[타입] 작업 내용`

### 작성 예시

```bash
git commit -m "[feat] 회원가입 기능 구현"
git commit -m "[fix] 로그인 오류 수정"
git commit -m "[add] 공연 이미지 파일 추가"
git commit -m "[update] 공연 상세 정보 수정"
git commit -m "[refactor] 중복 코드 제거"
git commit -m "[docs] README 수정"
git commit -m "[style] 코드 들여쓰기 수정"
git commit -m "[test] 회원가입 테스트 추가"
git commit -m "[chore] .gitignore 수정"
git commit -m "[build] FastAPI 의존성 추가"
git commit -m "[ci] GitHub Actions 워크플로 수정"
git commit -m "[perf] DB 조회 성능 개선"
git commit -m "[remove] 불필요한 파일 삭제"
git commit -m "[revert] 로그인 변경 사항 복구"
```

## 3. 작성 시 주의사항

- 커밋 타입은 영문 소문자로 작성한다.
- 커밋 타입은 대괄호 `[ ]`로 감싼다.
- 대괄호 뒤에는 공백 한 칸을 넣는다.
- 작업 내용을 간결하고 명확하게 작성한다.
- 하나의 커밋에는 가급적 하나의 작업 목적만 포함한다.
- 팀원들이 변경 내용을 쉽게 이해할 수 있도록 작성한다.

## 4. 올바른 커밋 메시지 예시

**올바른 예시**

- `[feat] 회원가입 API 구현`
- `[fix] 로그인 토큰 만료 오류 수정`
- `[docs] 프로젝트 README 업데이트`

**잘못된 예시**

- `feat: 회원가입 API 구현` — 대괄호 형식 미사용
- `[FEAT] 회원가입 API 구현` — 타입에 대문자 사용
- `[feat]회원가입 API 구현` — 대괄호 뒤 공백 누락
- `수정함` — 타입 및 작업 내용 불명확