"""서버별 /etc/alloy/config.alloy 생성 (로그 전용 → Loki 189)."""
import os

OUT = os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT, exist_ok=True)

HOSTS = {
    "175": ("fastapi1", "fastapi"),
    "176": ("fastapi2", "fastapi"),
    "177": ("nginx1", "nginx"),
    "178": ("nginx2", "nginx"),
    "179": ("haproxy-backend", "haproxy"),
    "181": ("haproxy-frontend", "haproxy"),
    "187": ("prometheus", "monitoring"),
    "188": ("grafana", "monitoring"),
    "189": ("loki", "monitoring"),
}

COMMON = r'''// =====================================================================
// Alloy 로그 수집 설정 — {host} (192.168.0.{ip})
// 관리: 저장소 monitoring/alloy/deployed/ 에서 생성. 직접 수정 시 저장소도 함께 반영.
// 메트릭은 Prometheus(187)가 node_exporter(:9100)를 직접 수집하므로 여기서는 로그만 보냅니다.
// =====================================================================

logging {{
  level  = "warn"
  format = "logfmt"
}}

loki.write "loki189" {{
  endpoint {{
    url        = "http://192.168.0.189:3100/loki/api/v1/push"
    batch_wait = "2s"
    batch_size = "512KiB"
  }}

  external_labels = {{
    host     = "{host}",
    instance = "192.168.0.{ip}",
    role     = "{role}",
  }}
}}

// ---------------------------------------------------------------------
// journald: 시스템 · 서비스 로그 (syslog, auth 포함)
// ---------------------------------------------------------------------
loki.relabel "journal" {{
  forward_to = []

  rule {{
    source_labels = ["__journal__systemd_unit"]
    target_label  = "unit"
  }}

  rule {{
    source_labels = ["__journal_priority_keyword"]
    target_label  = "level"
  }}

  rule {{
    source_labels = ["__journal__systemd_unit"]
    regex         = "(.*)"
    target_label  = "job"
    replacement   = "systemd-journal"
  }}

  // FastAPI 를 systemd(tikit-api.service)로 실행하면 job="fastapi" 로 분류됩니다.
  rule {{
    source_labels = ["__journal__systemd_unit"]
    regex         = "tikit-api\\.service"
    target_label  = "job"
    replacement   = "fastapi"
  }}
}}

loki.source.journal "system" {{
  max_age       = "12h"
  relabel_rules = loki.relabel.journal.rules
  forward_to    = [loki.process.journal.receiver]
}}

loki.process "journal" {{
  // Grafana 가 쿼리마다 남기는 info 로그 제거 (대시보드 새로고침 → 로그 → Loki 순환 방지)
  stage.drop {{
    expression          = "^logger=(plugin|tsdb|context|infra|cleanup|ngalert)[^ ]* .*level=(info|debug) "
    drop_counter_reason = "grafana_info"
  }}

  // HAProxy 헬스체크(/health)와 메트릭 수집 요청 로그 제거
  stage.drop {{
    expression          = "\"GET /(health|metrics) HTTP"
    drop_counter_reason = "healthcheck"
  }}

  forward_to = [loki.write.loki189.receiver]
}}
'''

NGINX = r'''
// ---------------------------------------------------------------------
// nginx 접근 · 오류 로그
// ---------------------------------------------------------------------
local.file_match "nginx" {
  path_targets = [
    {"__path__" = "/var/log/nginx/access.log", "job" = "nginx", "log_type" = "access"},
    {"__path__" = "/var/log/nginx/error.log",  "job" = "nginx", "log_type" = "error"},
  ]
}

loki.source.file "nginx" {
  targets    = local.file_match.nginx.targets
  forward_to = [loki.process.nginx.receiver]
}

loki.process "nginx" {
  // 181 HAProxy 헬스체크: 192.168.0.181 "GET / HTTP/1.0" ... "-" "-"  (전체 로그의 대부분)
  stage.drop {
    expression          = "^192\\.168\\.0\\.181 .*\"GET / HTTP/1\\.[01]\" \\d+ \\d+ \"-\" \"-\"$"
    drop_counter_reason = "healthcheck"
  }

  // 해시가 붙은 정적 파일 요청
  stage.drop {
    expression          = "\"GET /(assets/|favicon\\.ico)"
    drop_counter_reason = "static_asset"
  }

  forward_to = [loki.write.loki189.receiver]
}
'''

HAPROXY = r'''
// ---------------------------------------------------------------------
// HAProxy 접근 로그 (rsyslog → /var/log/haproxy.log)
// ---------------------------------------------------------------------
local.file_match "haproxy" {
  path_targets = [
    {"__path__" = "/var/log/haproxy.log", "job" = "haproxy"},
  ]
}

loki.source.file "haproxy" {
  targets    = local.file_match.haproxy.targets
  forward_to = [loki.process.haproxy.receiver]
}

loki.process "haproxy" {
  stage.drop {
    expression          = "\"GET (https?://[^/ ]+)?/(assets/|favicon\\.ico)"
    drop_counter_reason = "static_asset"
  }

  forward_to = [loki.write.loki189.receiver]
}
'''

for ip, (host, role) in HOSTS.items():
    body = COMMON.format(host=host, ip=ip, role=role)
    if role == "nginx":
        body += NGINX
    if role == "haproxy":
        body += HAPROXY
    with open(os.path.join(OUT, f"{ip}-{host}.alloy"), "w", encoding="utf-8", newline="\n") as f:
        f.write(body)
    print(ip, host, role)
