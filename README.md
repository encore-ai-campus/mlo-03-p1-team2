# Tikit (티킷)

> 고객 행동 데이터 기반 공연 예매 및 데이터 분석 플랫폼

---

## 01. 팀 소개

**팀명: 티키타카 (TikiTaka)**

| 김한울 | 오정민 | 정상효 |
|:---:|:---:|:---:|
| <img src="https://github.com/user-attachments/assets/fb0b0b0f-60b8-4f1b-9035-baa75c7b5903" width="150" alt="김한울"> | <img src="https://github.com/OZAM0415.png" width="120" alt="오정민"> | <img width="120" height="120" alt="정상효" src="https://github.com/user-attachments/assets/5680e383-1dcb-4e1c-9e58-77f838c24c88" />|
| [@hannyeee](https://github.com/hannyeee) | [@OZAM0415](https://github.com/OZAM0415) | [@nomorehuman90](https://github.com/nomorehuman90) |
| 예매 및 결제 관리 | 공연 관리 | 회원 관리 |
| 팀장 1 | 팀장 2 | 팀장(진) 3 |

---

## 02. 프로젝트 개요

### 2.1 프로젝트명

**Tikit (티킷)**

### 2.2 프로젝트 소개

콘서트, 뮤지컬, 스포츠, 전시, 클래식, 연극 등 다양한 공연 정보를 제공하고 예매할 수 있는 데이터 기반 공연 예매 플랫폼

### 2.3 프로젝트 배경

- 예매·결제 내역만으로는 사용자의 탐색 과정과 예매 이탈 지점 파악에 한계
- 고객 이용 흐름 분석을 위한 검색·조회·찜 행동과 예매·결제 데이터의 연계 필요
- 요청 집중 상황에서의 데이터 정합성과 처리 성능을 검증 과제로 선정

### 2.4 프로젝트 목표

1. 공연 예매 서비스의 핵심 기능 구현
2. 사용자 행동 및 예매·결제 데이터 수집 환경 구축
3. 데이터 수집·정제·적재를 위한 파이프라인 구축
4. 수집 데이터의 품질 및 정합성 검증
5. 데이터 분석 및 시각화를 통한 정보 제공
6. 부하 테스트를 통한 시스템 및 데이터 처리 성능 검증

---

## 03. 기술 스택

### Skills

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![SQL](https://img.shields.io/badge/SQL-4479A1?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![MariaDB](https://img.shields.io/badge/MariaDB-003545?style=for-the-badge&logo=mariadb&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=for-the-badge&logo=mongodb&logoColor=white)

### Infra

![VMware Workstation / Fusion](https://img.shields.io/badge/VMware_Workstation_%2F_Fusion-607078?style=for-the-badge)
![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)
![Nginx](https://img.shields.io/badge/Nginx-009639?style=for-the-badge&logo=nginx&logoColor=white)
![HAProxy](https://img.shields.io/badge/HAProxy-1E4B75?style=for-the-badge)

### Monitoring

![Prometheus](https://img.shields.io/badge/Prometheus-E6522C?style=for-the-badge&logo=prometheus&logoColor=white)
![Grafana Alloy](https://img.shields.io/badge/Grafana_Alloy-F46800?style=for-the-badge)
![Loki](https://img.shields.io/badge/Loki-F7B93E?style=for-the-badge)
![Grafana](https://img.shields.io/badge/Grafana-F46800?style=for-the-badge&logo=grafana&logoColor=white)

### Collaboration

![Git](https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=git&logoColor=white)
![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)

---

## 04. WBS

```mermaid
gantt
    title Tikit 프로젝트 작업 일정
    dateFormat YYYY-MM-DD
    axisFormat %m/%d
    tickInterval 1day
    todayMarker off

    section 기획·설계
    요구사항·ERD·API 설계           :done, planning, 2026-11-05, 1d
    section 개발
    회원·공연·예매·결제 기능    :done, development, 2026-11-05, 1d
    section 인프라
    서버 연결·DB 클러스터 구성·모니터링 :done, infrastructure, 2026-11-06, 2026-11-08
    section 데이터
    로그 수집·데이터 생성 자동화     :done, data, 2026-11-06, 2026-11-09
    section 검증
    기능·정합성·부하 테스트         :done, verification, 2026-11-09, 1d
    section 마무리
    분석·문서 작성             :done, presentation, 2026-11-09, 1d
```

[→ 요구사항 명세서](https://github.com/encore-ai-campus/mlo-03-p1-team2/wiki/%EC%9A%94%EA%B5%AC%EC%82%AC%ED%95%AD-%EB%AA%85%EC%84%B8%EC%84%9C)

---

## 05. ERD

<img width="566" height="1024" alt="image" src="https://github.com/user-attachments/assets/533a4fa1-a554-40ac-bcde-88e611758815" />

[→ 주요 데이터 구조](https://github.com/encore-ai-campus/mlo-03-p1-team2/wiki/%EC%A3%BC%EC%9A%94-%EB%8D%B0%EC%9D%B4%ED%84%B0-%EA%B5%AC%EC%A1%B0)

---

## 06. 주요 프로시저


<img width="1280" height="721" alt="image" src="https://github.com/user-attachments/assets/3e0ce5bd-c6e9-4612-840f-998992123f35" />

[→ 시스템 아키텍처](https://github.com/encore-ai-campus/mlo-03-p1-team2/wiki/%EC%8B%9C%EC%8A%A4%ED%85%9C-%EC%95%84%ED%82%A4%ED%85%8D%EC%B2%98)

[→ 주요 처리 흐름](https://github.com/encore-ai-campus/mlo-03-p1-team2/wiki/%EC%A3%BC%EC%9A%94-%EC%B2%98%EB%A6%AC-%ED%9D%90%EB%A6%84)

---


## 07. 수행 결과

<img src="docs/images/playwrighting_1.gif" width="320" alt="Playwright 자동화 시연" />

<img width="480" height="226" alt="화면 녹화 중 2026-11-09 145942" src="https://github.com/user-attachments/assets/200f7aa7-0d84-488b-9572-64afe48e9028" />

[→ 주요 기능 소개](https://github.com/encore-ai-campus/mlo-03-p1-team2/wiki/%EC%A3%BC%EC%9A%94-%EA%B8%B0%EB%8A%A5-%EC%86%8C%EA%B0%9C)

---

## 08. 회고

### 김한울

> "회고 작성 예정"

### 오정민

> "회고 작성 예정"

### 정상효

> "AI의 신세계를 경험해보았습니다. 한단계 벽을 뛰어넘은 기분이며 다음 단계는 어떻게 해야할지 고민됩니다."
  
---

## 09. 문서 및 실행 안내

| 구분 | 안내 |
|---|---|
| 백엔드 실행 | 환경 설정과 FastAPI 실행 (docs/backend.md) |
| 프런트엔드 실행 | 개발 서버 실행과 빌드 (docs/frontend.md) |
| 서버 배포 | 프록시 연결과 HTTPS 설정 (docs/FrontToBackSetting.md) |
| 데이터 자동화 | 가상 사용자와 행동 데이터 생성 (docs/playwrightGuide.md) |
| 아키텍처 의사결정 | 주요 기술 선택 및 아키텍처 변경에 대한 의사결정 기록 (docs/adr) |
| 전체 문서 | 문서 목록 (docs/index.md) |
