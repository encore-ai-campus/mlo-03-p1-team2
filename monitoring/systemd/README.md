# systemd 리소스 상한 (drop-in)

모니터링 프로세스가 같은 노트북의 FastAPI, nginx, HAProxy 자원을 빼앗지 않도록 상한을 겁니다.

| 파일 | 설치 위치 | 대상 VM |
|---|---|---|
| `alloy-limits.conf` | `/etc/systemd/system/alloy.service.d/limits.conf` | 모든 VM |
| `prometheus-limits.conf` | `/etc/systemd/system/prometheus.service.d/limits.conf` | mon-metrics (184) |
| `grafana-limits.conf` | `/etc/systemd/system/grafana-server.service.d/limits.conf` | mon-metrics (184) |
| `loki-limits.conf` | `/etc/systemd/system/loki.service.d/limits.conf` | mon-logs (186) |

```bash
sudo mkdir -p /etc/systemd/system/alloy.service.d
sudo cp alloy-limits.conf /etc/systemd/system/alloy.service.d/limits.conf
sudo systemctl daemon-reload
sudo systemctl restart alloy
systemctl show alloy -p MemoryMax -p CPUQuotaPerSecUSec   # 적용 확인
```

- `MemoryHigh`를 넘으면 커널이 메모리를 회수하며 속도를 늦추고, `MemoryMax`를 넘으면 OOM kill이 발생합니다.
- Go 프로그램(Alloy, Prometheus, Loki, Grafana)은 `GOMEMLIMIT`을 상한보다 조금 낮게 잡아야 GC가 먼저 동작해 OOM을 피합니다.
