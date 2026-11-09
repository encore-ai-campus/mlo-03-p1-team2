# 🎫 Tikit (티킷)

> 고객 행동 데이터 기반 공연 예매 및 데이터 분석 플랫폼

---

## 01. 👥 팀 소개

**팀명: 티키타카 (TikiTaka)**

| 김한울 | 오정민 | 정상효 |
|:---:|:---:|:---:|
| <img src="https://github.com/user-attachments/assets/fb0b0b0f-60b8-4f1b-9035-baa75c7b5903" width="150" alt="김한울"> | <img src="https://github.com/OZAM0415.png" width="120" alt="오정민"> | <img width="120" height="120" alt="정상효" src="https://github.com/user-attachments/assets/5680e383-1dcb-4e1c-9e58-77f838c24c88" />|
| [@hannyeee](https://github.com/hannyeee) | [@OZAM0415](https://github.com/OZAM0415) | [@nomorehuman90](https://github.com/nomorehuman90) |
| 예매 및 결제 관리 | 공연 관리 | 회원 관리 |
| 팀장 1 | 팀장 2 | 팀장 3 |

---

## 02. 📌 프로젝트 개요

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

## 03. 🛠 기술 스택

### 📚 Skills

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![SQL](https://img.shields.io/badge/SQL-4479A1?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![MariaDB](https://img.shields.io/badge/MariaDB-003545?style=for-the-badge&logo=mariadb&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=for-the-badge&logo=mongodb&logoColor=white)

### ⚙️ Infra

![VMware Workstation / Fusion](https://img.shields.io/badge/VMware_Workstation_%2F_Fusion-607078?style=for-the-badge)
![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)
![Nginx](https://img.shields.io/badge/Nginx-009639?style=for-the-badge&logo=nginx&logoColor=white)
![HAProxy](https://img.shields.io/badge/HAProxy-1E4B75?style=for-the-badge)

### 📊 Monitoring

![Prometheus](https://img.shields.io/badge/Prometheus-E6522C?style=for-the-badge&logo=prometheus&logoColor=white)
![Grafana Alloy](https://img.shields.io/badge/Grafana_Alloy-F46800?style=for-the-badge)
![Loki](https://img.shields.io/badge/Loki-F7B93E?style=for-the-badge)
![Grafana](https://img.shields.io/badge/Grafana-F46800?style=for-the-badge&logo=grafana&logoColor=white)

### 🤝 Collaboration

![Git](https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=git&logoColor=white)
![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)

---

## 04. 📅 WBS

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

[요구사항 명세서](https://github.com/encore-ai-campus/mlo-03-p1-team2/wiki/Requirements-Specification)

---

## 05. 🏗 시스템 아키텍처
<img width="1280" height="721" alt="image" src="https://github.com/user-attachments/assets/3e0ce5bd-c6e9-4612-840f-998992123f35" />

[시스템 구성 상세](https://github.com/encore-ai-campus/mlo-03-p1-team2/wiki/System-Architecture)

---

## 06. 🗃 ERD

<img width="566" height="1024" alt="image" src="https://github.com/user-attachments/assets/533a4fa1-a554-40ac-bcde-88e611758815" />

---

## 07. 주요 프로시저

---

## 08. 진행 결과

<img width="49%" alt="화면 1" src="https://github.com/user-attachments/assets/f77759a5-fa35-47fd-852f-39ba7085f257" />
<img width="49%" alt="화면 2" src="https://github.com/user-attachments/assets/afc0151c-81df-4a8d-b138-17328d01629d" />

[기능 소개](https://github.com/encore-ai-campus/mlo-03-p1-team2/wiki/Functional-Specification)

---

## 09. 회고

---

## 10. 문서·실행 안내
