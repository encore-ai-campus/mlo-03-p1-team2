# 🎫 Tikit (티킷)

> 고객 행동 데이터 기반 공연 예매 및 데이터 분석 플랫폼

---

## 01. 👥 팀 소개

**팀명: 티키타카 (TikiTaka)**

| 이름 | GitHub | 담당 역할 |
|---|---|---|
| 김한울 | [@hannyeee](https://github.com/hannyeee) | 예매 및 결제 관리 |
| 오정민 | [@OZAM0415](https://github.com/OZAM0415) | 공연 관리 |
| 정상효 | [@nomorehuman90](https://github.com/nomorehuman90) | 회원 관리 |


---

## 02. 📌 프로젝트 개요

### 2.1 프로젝트명

**Tikit (티킷)**

### 2.2 프로젝트 소개

Tikit은 콘서트, 뮤지컬, 스포츠, 전시, 클래식, 연극 등 다양한 공연 정보를 제공하고 예매할 수 있는 데이터 기반 공연 예매 플랫폼입니다.

회원 관리, 공연 조회 및 검색, 예매와 모의 결제 기능을 구현하고, 서비스 이용 과정에서 발생하는 데이터를 수집·처리하여 데이터 분석에 활용하는 것을 목표로 합니다.

### 2.3 프로젝트 필요성

- 공연 서비스에서 발생하는 다양한 사용자 행동 및 거래 데이터의 체계적인 관리 필요
- 고객의 공연 이용 패턴과 공연별 수요를 파악하기 위한 데이터 수집·처리 환경 필요
- 대량의 데이터가 발생하는 환경에서 데이터 처리의 안정성과 정합성을 검증할 필요

### 2.4 프로젝트 목표

1. 공연 예매 서비스의 핵심 기능 구현
2. 사용자 행동 및 예매·결제 데이터 수집 환경 구축
3. 데이터 수집·정제·적재를 위한 파이프라인 구축
4. 수집 데이터의 품질 및 정합성 검증
5. 데이터 분석 및 시각화를 통한 정보 제공
6. 부하 테스트를 통한 시스템 및 데이터 처리 성능 검증

---

## 03. 🛠 기술 스택

| 구분 | 기술 | 역할 |
|---|---|---|
| 언어 | Python, SQL | 백엔드 개발 및 데이터 조회·처리 |
| 백엔드 | FastAPI | API 및 서비스 로직 처리 |
| 서비스 데이터 저장 | MariaDB | 회원·공연·예매·결제 데이터 저장 |
| 이벤트 로그 저장 | MongoDB | 사용자 행동 이벤트 저장 (공연 조회·검색·예매 등) |
| 데이터 처리 | 추후 확정 | 데이터 추출·정제·변환·적재 |
| 데이터 분석 시각화 | 추후 확정 | 고객 행동 및 예매 데이터 분석 결과 시각화 |
| 가상화 | VMware Workstation / Fusion | 물리 PC에서 Linux VM 실행 |
| 운영체제 | Linux | VM의 서버 운영체제 |
| 웹 서버 | Nginx | 외부 요청 수신, TLS 종료, FastAPI로 요청 전달 |
| 프록시 | HAProxy | PC마다 1대씩 배치. 연결 경로는 미정 |
| 메트릭 | Prometheus | Alloy 또는 서비스별 exporter의 메트릭 수집·저장 |
| 로그 수집 | Grafana Alloy | 각 VM의 로그를 수집하여 Loki로 전송 |
| 로그 저장 | Loki | 중앙 로그 저장 |
| 운영 모니터링 시각화 | Grafana | 메트릭·로그 대시보드 |
| 협업 | Git, GitHub | 버전 관리 및 협업 |

---

## 04. 📅 WBS (Work Breakdown Structure)

프로젝트의 단계별 작업 및 진행 일정을 관리합니다.

| 단계 | 주요 작업 | 담당자 | 일정 | 상태 |
|---|---|---|---|---|
| 1. 기획 | 프로젝트 주제 및 기능 정의 | 전체 | 1일차 | 완료 |
| 2. 설계 | 요구사항 명세서 및 ERD 작성 | 전체 | 1일차 | 완료 |
| 3. 개발 | 회원 기능 구현 | 정상효 | 1일차 | 완료 |
| 3. 개발 | 공연 기능 구현 | 오정민 | 1일차 | 완료 |
| 3. 개발 | 예매·결제 기능 구현 | 김한울 | 1일차 | 완료 |
| 4. 데이터 | 데이터 수집 및 처리 파이프라인 구축 | 전체 | 1일차 | 완료 |
| 5. 검증 | 기능·데이터·성능 테스트 | 전체 | 2일차 | 완료 |
| 6. 마무리 | 결과 분석 및 발표 자료 작성 | 전체 | 2일차 | 완료 |
(기간 2026-11-05 ~ 2026-11-09 작업기간 3 ) 
---

## 05. 📋 요구사항 명세서

### 5.1 기능 요구사항

| ID | 구분 | 요구사항 | 우선순위 |
|---|---|---|---|
| FR-001 | 회원 | 회원가입 및 로그인 | 높음 |
| FR-002 | 회원 | 회원정보 및 MBTI 관리 | 높음 |
| FR-003 | 공연 | 공연 등록 및 수정 | 높음 |
| FR-004 | 공연 | 공연 목록 및 상세 조회 | 높음 |
| FR-005 | 공연 | 공연 검색 및 카테고리별 조회 | 높음 |
| FR-006 | 공연 | 공연 회차 관리 | 중간 |
| FR-007 | 예매 | 공연 예매 및 내역 조회 | 높음 |
| FR-008 | 결제 | 모의 결제 및 상태 관리 | 높음 |
| FR-009 | 결제 | 예매·결제 취소 | 높음 |

### 5.2 비기능 요구사항

| ID | 구분 | 요구사항 |
|---|---|---|
| NFR-001 | 보안 | 사용자 비밀번호는 안전한 해시 방식으로 저장 |
| NFR-002 | 데이터 | 예매 및 결제 데이터의 정합성 보장 |
| NFR-003 | 안정성 | 중복 결제 및 잘못된 상태 변경 방지 |
| NFR-004 | 성능 | 동시 요청 환경에서 서비스 동작 검증 |
| NFR-005 | 유지보수 | 기능별 모듈 분리 및 API 문서화 |

---

## 06. 🏗 시스템 아키텍처

서비스와 데이터 처리 시스템의 전체 구조를 나타냅니다.

```mermaid
flowchart TB
    USER["사용자"]

    subgraph PC1["PC 1 · 웹 / 애플리케이션"]
        subgraph APP["app-vm"]
            NGINX["Nginx"]
            API["FastAPI"]
            NGINX -->|"요청 전달"| API
        end
        P1["proxy-1 · HAProxy"]
    end

    subgraph PC2["PC 2 · 데이터베이스"]
        MARIA[("mariadb-vm · MariaDB")]
        MONGO[("mongodb-vm · MongoDB")]
        P2["proxy-2 · HAProxy"]
    end

    subgraph PC3["PC 3 · 모니터링 / 로그"]
        subgraph MON["monitoring-vm"]
            PROM["Prometheus"]
            LOKI["Loki"]
            GRAFANA["Grafana"]
        end
        P3["proxy-3 · HAProxy"]
    end

    LOGS["각 VM의 Alloy"]
    METRICS["각 VM의 Alloy 또는 서비스별 exporter"]

    USER -->|"외부 요청 · TLS 종료"| NGINX
    LOGS -.->|"로그 전송"| LOKI
    PROM -.->|"메트릭 수집"| METRICS
    GRAFANA -->|"조회"| PROM
    GRAFANA -->|"조회"| LOKI
```

포함할 구성 요소:
- 사용자 및 웹서비스
- FastAPI 서버
- MariaDB
- 데이터 처리 파이프라인
- 분석 및 시각화 시스템
- 모니터링 환경

---

## 07. 🗃 ERD (Entity Relationship Diagram)

서비스의 데이터베이스 테이블과 관계를 나타냅니다.

주요 테이블:
- `users`
- `performances`
- `performance_schedules`
- `orders`
- `payments`

**추후 ERD 이미지 추가 예정**
<img width="562" height="747" alt="image" src="https://github.com/user-attachments/assets/3c980295-c06b-4966-99ef-517c266d0d35" />

---

## 08. 📖 API 명세서

| 구분 | Method | Endpoint | 설명 |
|---|---|---|---|
| 회원 | POST | `/users/signup` | 회원가입 |
| 회원 | POST | `/auth/login` | 로그인 |
| 회원 | GET | `/users/me` | 회원정보 조회 |
| 공연 | GET | `/performances` | 공연 목록 조회 |
| 공연 | GET | `/performances/{id}` | 공연 상세 조회 |
| 공연 | POST | `/performances` | 공연 등록 |
| 예매 | POST | `/orders` | 예매 생성 |
| 예매 | GET | `/orders/{id}` | 예매 내역 조회 |
| 결제 | POST | `/orders/{id}/payments` | 결제 요청 |
| 결제 | POST | `/payments/{id}/complete` | 결제 완료 |
| 결제 | POST | `/payments/{id}/cancel` | 결제 취소 |

※ API 경로는 개발 과정에서 변경될 수 있습니다.

---

## 09. 📁 프로젝트 디렉터리 구조

프로젝트의 소스 코드 및 주요 디렉터리 구성을 설명합니다.

| 폴더 | 내용 | 문서 |
|---|---|---|
| `backend/` | FastAPI + MySQL(MariaDB) API (회원·공연·예매·결제·찜) | [docs/backend.md](docs/backend.md) |
| `frontend/` | Vue 3 + Vite 화면 (메인·로그인·회원가입·마이페이지·마이티킷), 빌드 결과를 nginx로 제공 | [docs/frontend.md](docs/frontend.md) |
| `docs/` | 프로젝트 문서 (예매 → 모의 결제 → 취소 기능 명세 포함) | [docs/booking.md](docs/booking.md) |
| `sample/` | 처음 디자인 시안 (브라우저 저장소만 쓰는 시연 버전) | [docs/sample.md](docs/sample.md) |

---

## 10. 🔄 데이터 파이프라인

### 10.1 데이터 수집

- 회원 데이터
- 공연 정보 데이터
- 공연 조회 및 검색 데이터
- 예매 및 결제 데이터

### 10.2 데이터 처리

- 데이터 추출 및 정제
- 중복 및 결측값 검증
- 데이터 변환 및 집계
- 분석용 데이터 적재

### 10.3 데이터 품질 관리

- 데이터 중복 검증
- 데이터 누락 검증
- 데이터 정합성 검증
- 처리 오류 및 실패 이력 관리

※ 데이터 파이프라인의 세부 기술과 구조는 추후 확정합니다.

---

## 11. 📊 데이터 분석 및 활용

수집된 데이터를 기반으로 분석을 수행하고 결과를 시각화합니다.

- 고객별 공연 이용 패턴 분석
- 공연 카테고리별 예매 현황 분석
- 공연별 수요 및 예매 추이 분석
- 예매·결제 상태별 통계 분석

※ 구체적인 분석 기능과 지표는 추후 확정합니다.

---

## 12. 🧪 테스트 및 성능 검증

### 12.1 기능 테스트

- 회원가입 및 로그인 테스트
- 공연 등록·조회 테스트
- 예매 및 결제 상태 변경 테스트

### 12.2 데이터 검증

- 데이터 누락 및 중복 여부 확인
- 예매·결제 데이터 정합성 검증
- 데이터 처리 결과 검증

### 12.3 부하 테스트

- Locust 기반 동시 사용자 요청 테스트
- 요청 처리량 및 응답시간 측정
- 부하 증가에 따른 시스템 동작 확인

---

## 13. 🔧 트러블슈팅

프로젝트 진행 중 발생한 문제와 해결 과정을 기록합니다.

| 문제 | 원인 | 해결 방법 |
|---|---|---|
| 추후 작성 | 추후 작성 | 추후 작성 |

---

## 14. 🏁 프로젝트 결과 및 회고

### 주요 결과

*프로젝트 완료 후 작성 예정*

### 개선 사항 및 한계점

*프로젝트 완료 후 작성 예정*

### 팀 회고

*프로젝트 완료 후 작성 예정*

---

## 15. 🚀 실행 방법

### 개발 환경

- Python 3.10 이상, Node.js 18 이상
- MySQL 8 또는 MariaDB 10.11 (`tikit` 데이터베이스)

### 설치 및 실행

1. **백엔드**: `backend/.env` 작성 → `tikit` 데이터베이스 생성 → `python -m alembic upgrade head` (예매 테이블 0002 포함) → `python -m app.db.seed` → `python -m uvicorn app.main:app --port 8000`
2. **프론트엔드**
   - 개발: `cd frontend` → `npm install` → `npm run dev` → http://localhost:5173
   - 배포: `npm run build` → `frontend/dist/` 내용을 nginx `html` 폴더에 복사 (`/api/`는 `127.0.0.1:8000`으로 프록시, `try_files ... /index.html` 설정) → http://localhost

자세한 방법과 자주 나는 오류는 [docs/backend.md](docs/backend.md), [docs/frontend.md](docs/frontend.md)를 참고하세요.
