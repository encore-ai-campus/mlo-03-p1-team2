# ADR-001: 3대의 PC를 활용한 VMware 서버 배치 및 리소스 할당

| 항목 | 내용 |
|---|---|
| 상태 | 제안됨 |
| 작성일 | 2026-11-05 |
| 적용 범위 | 학습·개발 및 소규모 서비스 환경 |
| 결정 대상 | VM 구성, 서비스 배치, CPU·메모리·디스크 할당 |

## 1. 배경

3대의 PC에서 VMware를 이용해 다음 서비스를 운영하려고 한다.

- Nginx, FastAPI
- MariaDB, MongoDB
- 프록시 서버 3대
- Grafana, Prometheus, Alloy, Loki

제한된 물리 자원 안에서 애플리케이션, 데이터베이스, 모니터링의 부하를 분리하고, 호스트 운영체제의 여유 자원을 확보해야 한다.

### 하드웨어 및 산정 가정

| 장비 | 제공된 사양 | 본 ADR의 산정 기준 |
|---|---|---|
| PC 1 | RAM 32GB, 100G | RAM 32GB, VM용 여유 디스크 100GB |
| PC 2 | RAM 32GB, 100G | RAM 32GB, VM용 여유 디스크 100GB |
| PC 3 | Mac, “RAM 24 core” | RAM 24GB로 가정. CPU 및 디스크 사양 미확정 |

다음 조건을 전제로 한다.

- VM 운영체제는 GUI 없는 Linux를 사용한다.
- 프록시는 일반적인 HTTP/HTTPS 프록시이며, 대용량 캐싱이나 콘텐츠 검사를 수행하지 않는다.
- 대규모 트래픽과 대용량 데이터 처리는 초기 범위에 포함하지 않는다.
- 할당값은 성능을 보장하는 수치가 아닌 초기 운영 예산이다.
- PC 1·2의 100GB가 전체 디스크 용량이라면, 호스트 OS 사용량을 제외하고 배치를 재산정한다.
- Mac의 “24 core”가 CPU 코어 수를 의미한다면, 실제 RAM을 기준으로 재산정한다.

## 2. 결정

**PC 1은 웹·애플리케이션, PC 2는 데이터베이스, PC 3은 모니터링·로그 저장을 담당한다. 프록시는 PC마다 한 대씩 배치한다.**

총 7대의 VM을 생성하고, 각 VM에 Alloy를 설치한다.

### VM별 리소스 할당

| 물리 장비 | VM 이름 | 서비스 | vCPU | RAM | 디스크 |
|---|---|---|---:|---:|---:|
| PC 1 | app-vm | Nginx, FastAPI | 4 | 6GB | 25GB |
| PC 1 | proxy-1 | 프록시 1 | 1 | 2GB | 10GB |
| PC 2 | mariadb-vm | MariaDB | 2 | 8GB | 30GB |
| PC 2 | mongodb-vm | MongoDB | 2 | 8GB | 30GB |
| PC 2 | proxy-2 | 프록시 2 | 1 | 2GB | 10GB |
| PC 3 | monitoring-vm | Grafana, Prometheus, Loki | 4 | 10GB | 80GB |
| PC 3 | proxy-3 | 프록시 3 | 1 | 2GB | 10GB |

RAM과 디스크 할당량에는 게스트 OS 및 Alloy 사용분을 포함한다.

### 물리 장비별 합계

| 장비 | VM 수 | vCPU 합계 | VM RAM 합계 | 호스트용 잔여 RAM¹ | VM 디스크 합계 |
|---|---:|---:|---:|---:|---:|
| PC 1 | 2 | 5 | 8GB | 약 24GB | 35GB |
| PC 2 | 3 | 5 | 18GB | 약 14GB | 70GB |
| PC 3 | 2 | 5 | 12GB | 약 12GB | 90GB |

¹ 잔여 RAM은 물리 RAM에서 VM 할당량만 뺀 값이며, 호스트 OS와 VMware 등의 사용량은 여기서 차감된다.

vCPU 합계는 물리 코어를 전용으로 예약한다는 의미가 아니다. PC 1·2가 4코어 이하라면 app-vm을 2 vCPU로 낮추는 것을 우선 고려한다.

## 3. 결정 근거

| 결정 | 근거 |
|---|---|
| Nginx와 FastAPI를 같은 VM에 배치 | 요청 전달과 배포 구성을 단순화하고 게스트 OS 운영 부담을 줄인다. |
| DB별 VM 분리 | 메모리, 설정, 재시작 및 저장 공간을 독립적으로 관리한다. |
| DB를 PC 2에 배치 | 애플리케이션 및 로그 저장 부하와 물리적으로 분리한다. |
| 모니터링 서비스를 하나의 VM에 배치 | 소규모 환경에서 VM 수와 관리 복잡도를 줄인다. |
| 모니터링을 PC 3에 배치 | 애플리케이션·DB와 별도 장비에서 상태 및 로그를 관찰한다. |
| 프록시를 장비별로 분산 | 한 PC 중단 시 모든 프록시가 동시에 중단되는 상황을 피한다. |
| Alloy를 각 VM에 설치 | 로그가 생성되는 위치에서 직접 수집하고 중앙 Loki로 전송한다. |

## 4. 운영 구성

### 애플리케이션 및 데이터베이스

- Nginx는 외부 요청 수신, TLS 종료 및 FastAPI로의 요청 전달을 담당한다.
- FastAPI는 worker 2개로 시작한다. worker 수를 늘릴 때 프로세스별 메모리 증가를 고려한다.
- MariaDB의 InnoDB buffer pool은 약 4GB로 시작한다.
- MongoDB의 WiredTiger 캐시는 약 3GB로 시작한다.
- DB별 30GB 디스크에는 OS가 포함되므로, 초기 DB 데이터 예산은 각각 약 15~20GB 이내로 계획한다.
- 프록시의 디스크 캐시는 비활성화하거나 작은 크기로 제한한다.

### 모니터링 및 로그

monitoring-vm의 메모리 예산은 다음과 같이 배분한다.

| 용도 | RAM 예산 |
|---|---:|
| Grafana | 1GB |
| Prometheus | 2GB |
| Loki | 4GB |
| OS, Alloy, 파일 캐시 및 여유분 | 3GB |
| **합계** | **10GB** |

이 값은 VM 내부의 사용 예산이며 서비스별로 보장되는 전용 메모리는 아니다.

- Prometheus는 수집 주기 30초, 보관 기간 7일로 시작하고 저장 용량 제한도 적용한다.
- Loki는 단일 프로세스 방식으로 운영하며 보관 기간은 3일로 시작한다.
- monitoring-vm의 디스크 중 Prometheus에 약 15GB, Loki에 약 40GB를 사용 예산으로 둔다.
- Loki는 보관 기간과 Compactor 삭제 설정을 함께 적용한다. 보관 기간만으로 디스크 사용량의 상한이 보장되지는 않는다.
- Alloy는 각 VM의 로그를 Loki로 전송한다.
- Prometheus는 Alloy 또는 서비스별 exporter가 노출하는 메트릭을 수집한다.
- 로컬 로그에도 로그 회전을 적용한다.

### 가상화 및 네트워크

- PC 1·2가 Windows/Linux 호스트라면 VMware Workstation을 사용한다.
- Mac은 VMware Fusion을 사용한다.
- Apple Silicon Mac에서는 ARM64 Linux 게스트와 ARM64 지원 패키지·이미지를 사용한다.
- VM은 브리지 네트워크와 고정 IP 또는 DHCP 예약으로 연결한다.
- 물리 PC 간 연결은 유선 1Gbps 이상을 권장한다.
- DB, Prometheus, Loki는 내부망에서 필요한 대상만 접근하도록 제한한다.
- Mac은 상시 전원 연결 및 자동 잠자기 조정을 통해 모니터링의 연속성을 확보한다.

## 5. 검토한 대안

| 대안 | 장점 | 채택하지 않은 이유 |
|---|---|---|
| 모든 서비스를 개별 VM으로 분리 | 서비스별 격리 수준이 높음 | 게스트 OS의 메모리·디스크 사용과 관리 부담이 증가함 |
| 모든 서비스를 한 PC에 집중 | 초기 구성이 단순함 | 부하가 집중되고 해당 PC 장애 시 전체 서비스가 중단됨 |
| MariaDB와 MongoDB를 PC별로 분산 | 두 DB의 물리 디스크 부하를 분리할 수 있음 | 초기에는 역할별 구성을 단순하게 유지하고, DB 쓰기 부하 증가 시 재검토함 |
| 모니터링 서비스를 각각 별도 VM으로 구성 | 개별 증설과 재시작이 쉬움 | 초기 규모에서는 통합 VM의 운영 효율이 더 높다고 판단함 |

## 6. 결과 및 제약

### 기대 효과

- 애플리케이션, DB, 모니터링 간 물리 자원 경합을 줄인다.
- 호스트 OS와 개발 도구를 위한 메모리 여유를 확보한다.
- VM별 역할과 자원 사용량을 구분하기 쉽다.
- 프록시 장애 범위를 물리 PC 단위로 분산한다.

### 수용하는 제약

- PC 1 장애 시 Nginx와 FastAPI가 중단된다.
- PC 2 장애 시 MariaDB와 MongoDB가 모두 중단된다.
- 두 DB가 같은 물리 디스크를 사용하므로 동시 쓰기 부하가 높으면 병목이 발생할 수 있다.
- PC 3 또는 monitoring-vm 장애 시 중앙 모니터링 및 로그 조회가 중단된다.
- 프록시 분산 배치만으로 자동 장애 전환이 제공되지는 않는다.
- DB 복제와 애플리케이션 이중화는 포함하지 않는다.
- 백업 및 장기 보관용 저장소는 별도로 확보해야 한다. VM 스냅샷은 백업을 대체하지 않는다.

## 7. 재검토 조건

다음 상황에서는 이 ADR의 리소스 할당 또는 배치를 재검토한다.

- 실제 하드웨어 사양이 산정 가정과 다른 경우
- DB 데이터가 초기 저장 예산에 근접하는 경우
- 두 DB의 동시 쓰기로 디스크 병목이 발생하는 경우
- Prometheus 시계열 수 또는 Loki 로그 유입량이 증가하는 경우
- FastAPI에서 모델이나 대용량 데이터를 메모리에 적재하는 경우
- 장기 데이터 보관, 서비스 이중화 또는 자동 장애 전환이 필요한 경우

## 8. 참고 자료

- [VMware Fusion의 Apple Silicon 게스트 호환성](https://knowledge.broadcom.com/external/article/315602)
- [Prometheus 저장소 및 용량 산정](https://prometheus.io/docs/prometheus/latest/storage/)
- [Loki 배포 방식](https://grafana.com/docs/loki/latest/get-started/deployment-modes/)
- [Loki 로그 보관 정책](https://grafana.com/docs/loki/latest/operations/storage/retention/)
