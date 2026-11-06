# 프런트엔드 ↔ 백엔드 서버 연결 설정 가이드

| 항목 | 내용 |
|---|---|
| 작성일 | 2026-11-06 |
| 대상 서버 | 192.168.0.181, 177, 178 (프런트) / 192.168.0.179, 175, 176 (백엔드) |
| OS | Ubuntu 24.04.4 LTS (전 서버 공통) |
| 목적 | 프런트 HAProxy → nginx → 백엔드 HAProxy → FastAPI → DB 까지 요청이 흐르도록 연결 |

> 서버 접속 계정과 비밀번호는 이 문서에 적지 않습니다. 팀 내부 채널에서 확인하세요.

---

## 1. 전체 요청 흐름

```mermaid
flowchart LR
    U["브라우저"] -->|":80"| FH["181 · HAProxy<br/>(프런트)"]
    FH -->|"round-robin :80"| N1["177 · nginx"]
    FH -->|"round-robin :80"| N2["178 · nginx"]
    N1 -->|"/api/ 프록시"| BH["179 · HAProxy<br/>(백엔드)"]
    N2 -->|"/api/ 프록시"| BH
    BH -->|"round-robin :8000"| F1["175 · FastAPI"]
    BH -->|"round-robin :8000"| F2["176 · FastAPI"]
    F1 --> M[("171 · MariaDB :3306")]
    F2 --> M
    F1 --> G[("174 · MongoDB :27017")]
    F2 --> G
```

- nginx(177·178)는 **정적 파일(Vue 빌드 결과)** 을 제공하고, `/api/` 로 시작하는 요청만 백엔드 HAProxy(179)로 넘깁니다.
- 프런트엔드는 API를 상대 경로 `/api/v1` 으로 호출합니다(`frontend/src/api/client.js`). 브라우저 입장에서 같은 출처라 **CORS 설정이 필요 없습니다.**
- 175·176은 nginx가 아닌 **FastAPI(uvicorn) 서버**입니다. 호스트명(`fastapi175`, `fastapi176`)과 179 HAProxy 설정(`:8000`)도 이에 맞춰져 있습니다.

---

## 2. 현재 상태 점검 결과 (2026-11-06)

| 서버 | 역할 | 현재 상태 | 필요한 작업 |
|---|---|---|---|
| 192.168.0.181 | 프런트 HAProxy | `:80` → 177/178 round-robin, `GET /` 헬스체크, stats `:8404` | **없음** |
| 192.168.0.177 | 프런트 nginx | `/var/www/html` 에 빌드 파일 배포됨, `real_ip.conf` 설정됨 | **`/api/` 프록시 추가**, SPA fallback 수정 |
| 192.168.0.178 | 프런트 nginx | 177과 동일 | 177과 동일 |
| 192.168.0.179 | 백엔드 HAProxy | `:80` → 175/176:8000, `GET /health` 체크. 백엔드 미기동으로 **503** 응답 | 필수 없음 (보강 권장) |
| 192.168.0.175 | FastAPI | `/home/test/app` 에 코드만 있음. **venv·pip·.env·실행 프로세스 없음** | **실행 환경 구성 + systemd 등록** |
| 192.168.0.176 | FastAPI | 175와 동일 | 175와 동일 |

공통 확인 사항

- 6대 모두 `ufw` 비활성 → 방화벽 작업 불필요
- 175·176 → MariaDB(171:3306), MongoDB(174:27017), 179:80 **연결 가능**
- 177·178·181 의 호스트명이 모두 `test` 로 동일

---

## 3. 작업 순서

뒤쪽(백엔드)부터 앞쪽(프런트)으로 올라오며 작업하고, 단계마다 동작을 확인합니다.

1. 175·176 — FastAPI 실행
2. 179 — 백엔드 HAProxy 확인/보강
3. 177·178 — nginx `/api/` 프록시 추가
4. 181 — 변경 없음, 확인만
5. 전체 연결 확인

---

## Step 1. FastAPI 서버 (192.168.0.175, 192.168.0.176)

두 서버에 **똑같이** 적용합니다.

### 1-1. 디렉터리 구조 확인

`app` 패키지가 `/home/test/app` 에 있으므로 작업 디렉터리는 `/home/test` 입니다.

```
/home/test/
├── app/               # backend/app 복사본 (main.py, api, core, db, models, schemas)
├── requirements.txt
├── .env               # 새로 생성
└── .venv/             # 새로 생성
```

### 1-2. Python 가상환경과 패키지 설치

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip

cd /home/test
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 1-3. 환경 변수 파일 작성

`/home/test/.env` 를 작성합니다. 설정(`app/core/config.py`)은 **실행 디렉터리의 `.env`** 를 읽습니다.

```dotenv
DATABASE_URL=mysql+pymysql://<DB_USER>:<DB_PASSWORD>@192.168.0.171:3306/tikit?charset=utf8mb4
MONGODB_URL=mongodb://<MONGO_USER>:<MONGO_PASSWORD>@192.168.0.174:27017/tikit?authSource=admin
MONGODB_DB=tikit
MONGODB_EVENTS_COLLECTION=events
JWT_SECRET=<긴 랜덤 문자열, 175·176 동일 값>
JWT_EXPIRE_MINUTES=60
```

```bash
chmod 600 /home/test/.env
```

> ⚠️ **`JWT_SECRET` 은 175와 176에서 반드시 같은 값이어야 합니다.**
> 179가 요청을 두 서버에 번갈아 보내므로, 값이 다르면 한 서버에서 발급한 토큰을 다른 서버가 거부해 로그인 직후 401 오류가 납니다.

랜덤 문자열 생성 예시 (한 번 만들어 두 서버에 같이 사용):

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 1-4. DB 스키마 확인

서버에는 `alembic/` 디렉터리가 배포되어 있지 않습니다. MariaDB `tikit` 에 테이블이 아직 없다면, **로컬 또는 한 서버에서 한 번만** 마이그레이션을 실행합니다.

```bash
# 로컬 저장소의 backend 디렉터리에서 (.env 의 DATABASE_URL 이 171을 가리키는 상태)
alembic upgrade head
```

### 1-5. 수동 실행으로 확인

```bash
cd /home/test
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

# 다른 터미널에서
curl http://localhost:8000/health
# {"status":"ok"}
```

확인 후 `Ctrl+C` 로 종료합니다.

### 1-6. systemd 서비스 등록

`/etc/systemd/system/tikit-api.service`

```ini
[Unit]
Description=TIKIT FastAPI
After=network-online.target
Wants=network-online.target

[Service]
User=test
WorkingDirectory=/home/test
ExecStart=/home/test/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers --forwarded-allow-ips=192.168.0.179
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now tikit-api
sudo systemctl status tikit-api
```

- `app/` 디렉터리 권한이 `drwx------ test` 이므로 반드시 `User=test` 로 실행합니다.
- `--proxy-headers --forwarded-allow-ips=192.168.0.179` : 179가 넘겨주는 `X-Forwarded-For` 를 신뢰해 실제 사용자 IP를 인식합니다.
- 로그 확인: `journalctl -u tikit-api -f`

---

## Step 2. 백엔드 HAProxy (192.168.0.179)

Step 1이 끝나면 **현재 설정 그대로도 동작**합니다. 아래는 권장 보강안입니다.

`/etc/haproxy/haproxy.cfg` 의 `frontend` / `backend` 부분:

```haproxy
frontend webserver
    bind *:80
    mode http
    option forwardfor                       # 실제 사용자 IP를 X-Forwarded-For 로 전달
    default_backend fastapi-server

backend fastapi-server
    mode http
    balance roundrobin
    option httpchk GET /health
    http-check expect status 200            # 200이 아니면 제외
    server fastapi1 192.168.0.175:8000 check inter 3s fall 3 rise 2
    server fastapi2 192.168.0.176:8000 check inter 3s fall 3 rise 2
```

통계 화면(`:9000`)에 인증이 없으므로 추가를 권장합니다.

```haproxy
listen stats
    bind *:9000
    mode http
    stats enable
    stats uri /stats
    stats auth <STATS_USER>:<STATS_PASSWORD>
```

적용 및 확인:

```bash
sudo haproxy -c -f /etc/haproxy/haproxy.cfg   # 문법 검사
sudo systemctl reload haproxy
curl http://192.168.0.179/health              # {"status":"ok"}
```

---

## Step 3. 프런트 nginx (192.168.0.177, 192.168.0.178)

두 서버에 **똑같이** 적용합니다.

### 3-1. 사이트 설정 수정

`/etc/nginx/sites-available/default` 의 `server { }` 블록을 아래와 같이 수정합니다.

```nginx
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    root /var/www/html;
    index index.html;
    charset utf-8;
    server_tokens off;

    # 백엔드 API 프록시 → 백엔드 HAProxy(179)
    location /api/ {
        proxy_pass http://192.168.0.179;      # 끝에 '/' 없음 → /api/v1/... 경로 그대로 전달
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 30s;
        client_max_body_size 1m;
    }

    # 해시가 붙은 빌드 파일은 길게 캐시
    location /assets/ {
        add_header Cache-Control "public, max-age=31536000, immutable" always;
        try_files $uri =404;
    }

    # Vue Router(history 모드): /login 등 새로고침 시 index.html 반환
    location / {
        add_header Cache-Control "no-cache" always;
        try_files $uri $uri/ /index.html;
    }
}
```

변경 포인트

| 항목 | 기존 | 변경 | 이유 |
|---|---|---|---|
| `/api/` | 없음 | 179로 프록시 | API 요청이 백엔드로 전달되도록 |
| `location /` | `try_files ... =404` | `try_files ... /index.html` | `/login` 같은 주소에서 새로고침 시 404 방지 |

> 보안 헤더(CSP 등)까지 포함한 전체 설정은 저장소의 `frontend/nginx/templates/default.conf.template` 에 있습니다. `${BACKEND_UPSTREAM}` 을 `192.168.0.179` 로 바꿔 사용할 수 있습니다.

`/etc/nginx/conf.d/real_ip.conf` 는 이미 있으므로 그대로 둡니다.

```nginx
set_real_ip_from 192.168.0.181;
real_ip_header X-Forwarded-For;
```

### 3-2. 적용

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 3-3. 프런트 빌드 배포 (코드 변경 시)

```bash
# 로컬
cd frontend
npm run build          # frontend/dist 생성

# dist 내용을 177·178 의 /var/www/html 로 복사
scp -r dist/* test@192.168.0.177:/tmp/dist/
# 서버에서
sudo rsync -a --delete /tmp/dist/ /var/www/html/
```

---

## Step 4. 프런트 HAProxy (192.168.0.181)

변경할 내용이 없습니다. 현재 설정:

```haproxy
frontend http_in
    bind *:80
    option forwardfor
    default_backend nginx_servers

backend nginx_servers
    balance roundrobin
    option httpchk
    http-check send meth GET uri /
    http-check expect status 200
    server nginx1 192.168.0.177:80 check inter 3s fall 3 rise 2
    server nginx2 192.168.0.178:80 check inter 3s fall 3 rise 2
```

---

## Step 5. 전체 연결 확인

안쪽부터 한 단계씩 확인합니다.

```bash
# 1) FastAPI 단독
curl -s http://192.168.0.175:8000/health
curl -s http://192.168.0.176:8000/health

# 2) 백엔드 HAProxy
curl -s http://192.168.0.179/health

# 3) nginx → 179 (실제 API 경로 사용)
curl -s http://192.168.0.177/api/v1/<엔드포인트>
curl -s http://192.168.0.178/api/v1/<엔드포인트>

# 4) 전체 경로 (사용자 진입점)
curl -s http://192.168.0.181/api/v1/<엔드포인트>
```

브라우저 확인

- 서비스: `http://192.168.0.181/`
- 프런트 HAProxy 상태: `http://192.168.0.181:8404/stats` → nginx1, nginx2 **UP**
- 백엔드 HAProxy 상태: `http://192.168.0.179:9000/stats` → fastapi1, fastapi2 **UP**

---

## 6. 문제 해결

| 증상 | 확인할 곳 | 원인 / 조치 |
|---|---|---|
| 179에서 `503` | `systemctl status tikit-api` (175·176) | FastAPI 미기동 또는 `/health` 실패 |
| 화면은 나오는데 API가 `404` | 177·178 nginx 설정 | `/api/` location 누락 |
| `/login` 등에서 새로고침 시 `404` | 177·178 `location /` | `try_files ... /index.html` 로 수정 |
| 로그인 직후 간헐적 `401` | 175·176 `.env` | `JWT_SECRET` 값 불일치 |
| `502 Bad Gateway` (nginx) | `/var/log/nginx/error.log` | 179 접속 불가 또는 HAProxy 중지 |
| FastAPI 시작 실패 | `journalctl -u tikit-api` | `.env` 위치/DB 접속 정보/패키지 설치 확인 |
| DB 테이블 없음 오류 | MariaDB 171 | `alembic upgrade head` 실행 |

---

## 7. 참고 사항

- **로컬 개발 환경**: `frontend/vite.config.js` 의 `/api` 프록시 대상은 기본값을 `http://127.0.0.1:8000` 으로 두고, 서버 연결이 필요할 때 환경 변수로 지정하는 것을 권장합니다.
  ```bash
  BACKEND_URL=http://192.168.0.179 npm run dev
  ```
- **호스트명**: 177·178·181 의 호스트명이 모두 `test` 입니다. Alloy/Prometheus 에서 서버를 구분하려면 변경을 권장합니다.
  ```bash
  sudo hostnamectl set-hostname nginx177   # 예시
  ```
- **CORS**: 브라우저는 항상 같은 출처(181)로 요청하므로 `CORS_ORIGINS` 변경은 필요 없습니다.

---

## 8. SSL(HTTPS) 적용

### 8-1. 적용 현황

| 단계 | 암호화 구간 | 인증서 | 상태 |
|---|---|---|---|
| **1단계** | 브라우저 ⇄ **181** | 공인 인증서 (ZeroSSL, `www.yaaho.kro.kr`) | ✅ **적용 완료** (2026-11-06) |
| 2단계-A | 181 → 177·178 | 내부용 사설 인증서 (별도 준비) | 미적용 |
| 2단계-B | 177·178 → 179 | 내부용 사설 인증서 (별도 준비) | 미적용 |
| 2단계-C | 179 → 175·176 | 내부용 사설 인증서 (별도 준비) | 미적용 |

```mermaid
flowchart LR
    U["브라우저<br/>https://www.yaaho.kro.kr"] -->|"HTTPS :443 (1단계 ✅)"| FH["181 HAProxy<br/>TLS 종료"]
    FH -->|"HTTP :80 (2-A)"| N["177·178 nginx"]
    N -->|"HTTP :80 (2-B)"| BH["179 HAProxy"]
    BH -->|"HTTP :8000 (2-C)"| F["175·176 FastAPI"]
```

- 현재는 **181에서 TLS를 종료**하고, 그 뒤 내부망 구간은 HTTP로 동작합니다.
- 서비스 접속 주소는 **`https://www.yaaho.kro.kr`** 입니다. `http://` 로 접속하면 HTTPS로 자동 이동합니다.

### 8-2. 사용 인증서 정보

| 항목 | 값 |
|---|---|
| 발급 기관 | ZeroSSL (중간: `ZeroSSL RSA DV SSL CA 2`, 루트: `Sectigo Public Server Authentication Root R46`) |
| 종류 | DV (도메인 검증), 공인 인증서 |
| 도메인 (CN / SAN) | `www.yaaho.kro.kr` **한 개만** |
| 유효기간 | 2026-10-15 ~ **2027-01-13** (90일) |
| 키 | RSA |
| 원본 파일 (181) | `/home/test/ssl/certificate.crt`, `ca_bundle.crt`, `private.key` |
| HAProxy 사용 파일 | `/etc/haproxy/certs/tikit.pem` (인증서 + 중간 인증서 + 키) |

주의 사항

- 인증서에 **도메인만** 들어 있습니다. `https://192.168.0.181` 처럼 IP로 접속하면 이름 불일치 경고(`SEC_E_WRONG_PRINCIPAL`, `ERR_CERT_COMMON_NAME_INVALID`)가 납니다.
- `yaaho.kro.kr` (www 없이) 도 인증서에 포함되지 않습니다.
- 공인 인증서이므로 **접속 PC에 CA를 등록할 필요가 없습니다.**
- 도메인의 DNS A 레코드는 **`192.168.0.181` 하나만** 있어야 합니다. 다른 IP가 함께 등록되어 있으면 일부 접속이 다른 서버로 갑니다.
  ```bash
  nslookup www.yaaho.kro.kr     # Address: 192.168.0.181 만 나와야 함
  ```
- 개인 키(`private.key`, `tikit.pem`)는 **git 에 올리지 않습니다.**

### 8-3. 인증서 파일 점검

181 서버에서 원본 파일을 확인합니다.

```bash
cd /home/test/ssl
# 도메인과 유효기간
openssl x509 -in certificate.crt -noout -subject -issuer -dates -ext subjectAltName
# 인증서와 키가 짝이 맞는지 (두 값이 같아야 함)
openssl x509 -in certificate.crt -noout -pubkey | openssl sha256
openssl pkey -in private.key -pubout | openssl sha256
# 중간 인증서로 체인이 검증되는지 → "certificate.crt: OK"
openssl verify -untrusted ca_bundle.crt certificate.crt
```

---

### 8-4. [1단계] 181 HAProxy HTTPS 적용 ✅

#### ① 설정 백업

```bash
sudo cp /etc/haproxy/haproxy.cfg /etc/haproxy/haproxy.cfg.bak.$(date +%Y%m%d%H%M)
```

#### ② HAProxy용 PEM 만들기

HAProxy는 **인증서 → 중간 인증서 → 키** 순서로 이어 붙인 파일 하나를 사용합니다.

```bash
sudo mkdir -p /etc/haproxy/certs
cat /home/test/ssl/certificate.crt /home/test/ssl/ca_bundle.crt /home/test/ssl/private.key \
  | sudo tee /etc/haproxy/certs/tikit.pem > /dev/null
sudo cp /home/test/ssl/ca_bundle.crt /etc/haproxy/certs/
sudo chmod 600 /etc/haproxy/certs/tikit.pem
sudo chmod 644 /etc/haproxy/certs/ca_bundle.crt
```

> ⚠️ `ca_bundle.crt`(중간 인증서)를 빼면 Windows 브라우저는 정상처럼 보이지만, Linux curl·Python·모바일·부하 테스트 도구에서는 `unable to verify the first certificate` 오류가 납니다.

PEM 구성 확인 — 아래 순서로 3개 블록이 나와야 합니다.

```bash
sudo grep "BEGIN" /etc/haproxy/certs/tikit.pem
# -----BEGIN CERTIFICATE-----      ← www.yaaho.kro.kr
# -----BEGIN CERTIFICATE-----      ← ZeroSSL RSA DV SSL CA 2
# -----BEGIN RSA PRIVATE KEY-----
```

#### ③ haproxy.cfg 수정

`/etc/haproxy/haproxy.cfg` 의 `frontend http_in`:

```haproxy
frontend http_in
    bind *:80
    bind *:443 ssl crt /etc/haproxy/certs/tikit.pem alpn h2,http/1.1
    http-request redirect scheme https code 301 unless { ssl_fc }      # HTTP → HTTPS
    http-request set-header X-Forwarded-Proto https if { ssl_fc }
    option forwardfor
    default_backend nginx_servers
```

- `global` 의 `ssl-default-bind-*` (TLS 1.2 이상) 설정은 기본으로 들어 있으므로 그대로 둡니다.
- vi 로 수정했다면 반드시 **`:wq`** 로 저장하고, 저장됐는지 확인합니다.
  ```bash
  grep -n 443 /etc/haproxy/haproxy.cfg
  ```

#### ④ 적용

```bash
sudo haproxy -c -f /etc/haproxy/haproxy.cfg     # Configuration file is valid
sudo systemctl reload haproxy
ss -tlnp | grep :443                            # haproxy 가 443 을 열었는지
```

> ⚠️ HAProxy는 **reload 할 때만** 인증서 파일을 다시 읽습니다. `tikit.pem` 을 수정했다면 그 뒤에 반드시 reload 합니다.

#### ⑤ 177·178 nginx — 헤더 1줄 수정

181에서 TLS를 처리하므로 nginx 입장에서는 `$scheme` 이 `http` 입니다. 앞단에서 받은 값을 그대로 넘기도록 바꿉니다.

`/etc/nginx/sites-available/default` 의 `location /api/`:

```nginx
proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;   # 기존: $scheme
```

```bash
sudo nginx -t && sudo systemctl reload nginx
```

#### ⑥ 확인

181 서버에서:

```bash
# 인증서 2장(서버 + 중간)을 보내고 검증 결과가 0 (ok) 이어야 함
echo | openssl s_client -connect 127.0.0.1:443 -servername www.yaaho.kro.kr \
  -verify_hostname www.yaaho.kro.kr -showcerts 2>/dev/null | grep -E "^ *[0-9] s:|Verify return" | sort -u
#  0 s:CN = www.yaaho.kro.kr
#  1 s:C = AT, O = ZeroSSL GmbH, CN = ZeroSSL RSA DV SSL CA 2
# Verify return code: 0 (ok)
```

접속 PC에서:

```bash
curl -I http://www.yaaho.kro.kr/                                          # 301, location: https://www.yaaho.kro.kr/
curl -s -o /dev/null -w "%{http_code}\n" https://www.yaaho.kro.kr/          # 200
curl -s -o /dev/null -w "%{http_code}\n" https://www.yaaho.kro.kr/api/v1/performances/ranking?limit=1   # 200
```

브라우저에서 `https://www.yaaho.kro.kr/` 접속 → 자물쇠 표시, 로그인·예매 등 API 동작 확인.

2026-11-06 확인 결과: 위 항목 모두 정상.

#### ⑦ 되돌리기

`bind *:443 ...`, `redirect`, `set-header` 3줄을 주석 처리하거나 백업 파일로 복구한 뒤 reload 합니다.

```bash
sudo cp /etc/haproxy/haproxy.cfg.bak.<시각> /etc/haproxy/haproxy.cfg
sudo haproxy -c -f /etc/haproxy/haproxy.cfg && sudo systemctl reload haproxy
```

#### ⑧ 선택 적용

- stats 화면(:8404) HTTPS 전환
  ```haproxy
  listen stats
      bind *:8404 ssl crt /etc/haproxy/certs/tikit.pem
  ```
  이후 `https://www.yaaho.kro.kr:8404/stats` 로 접속합니다.
- HSTS — 2단계까지 진행할 경우 **모두 안정된 뒤** 추가합니다. 먼저 넣으면 문제가 생겼을 때 브라우저가 HTTP 로 돌아가지 못합니다.
  ```haproxy
  http-response set-header Strict-Transport-Security "max-age=31536000"
  ```

---

### 8-5. [2단계] 내부 구간 암호화 (선택)

#### 왜 별도 인증서가 필요한가

`www.yaaho.kro.kr` 인증서는 **도메인 하나만** 인증합니다. 내부 서버는 IP(`192.168.0.177` 등)로 서로 접속하므로 이 인증서를 그대로 쓰면 인증서 검증이 실패합니다.

| 방안 | 설명 |
|---|---|
| **A. 내부용 사설 CA 인증서 (권장)** | 사설 CA 하나로 내부 서버 5대(177·178·179·175·176)의 IP SAN 인증서를 발급. 서버 간에만 쓰이므로 브라우저에 CA 등록 불필요 |
| B. 내부 구간 HTTP 유지 | 내부망이 분리되어 있다면 1단계만으로 운영. 작업·성능 부담 없음 |

아래는 **방안 A** 기준입니다.

#### 내부 인증서 준비 요건

| 서버 | 파일 | SAN (필수) |
|---|---|---|
| 177 | `177.crt`, `177.key` | `IP:192.168.0.177` |
| 178 | `178.crt`, `178.key` | `IP:192.168.0.178` |
| 179 | `179.crt`, `179.key` | `IP:192.168.0.179` |
| 175 | `175.crt`, `175.key` | `IP:192.168.0.175` |
| 176 | `176.crt`, `176.key` | `IP:192.168.0.176` |
| 공통 | `internal-ca.crt` (사설 CA 인증서) | — |

- 키 파일은 암호(passphrase) 없이 만듭니다.
- 사설 CA 키는 발급 PC에만 보관하고 서버·git 에 올리지 않습니다.
- 점검: `openssl x509 -in 177.crt -noout -ext subjectAltName`, `openssl verify -CAfile internal-ca.crt 177.crt`

파일 배치

| 서버 | 위치 | 권한 |
|---|---|---|
| 181 | `/etc/haproxy/certs/internal-ca.crt` | `644` |
| 179 | `/etc/haproxy/certs/internal.pem` (179.crt + 179.key), `internal-ca.crt` | pem `600` |
| 177, 178 | `/etc/nginx/ssl/<IP끝자리>.crt`, `.key`, `internal-ca.crt` | key `600`, `root` 소유 |
| 175, 176 | `/home/test/ssl/<IP끝자리>.crt`, `.key`, `internal-ca.crt` | key `600`, `test` 소유 |

> 181 의 `/home/test/ssl/` 에는 공인 인증서 원본이 있으므로, 내부 인증서와 파일명이 겹치지 않게 합니다.

#### 2단계-A. 181 → 177·178

**177·178 nginx** — `server` 블록에 443 추가 (178 은 `178.*`)

```nginx
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    listen 443 ssl default_server;
    listen [::]:443 ssl default_server;
    http2 on;

    ssl_certificate     /etc/nginx/ssl/177.crt;
    ssl_certificate_key /etc/nginx/ssl/177.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_session_cache shared:SSL:10m;

    ...기존 설정 그대로...
}
```

`/etc/nginx/nginx.conf` 의 `ssl_protocols TLSv1 TLSv1.1 TLSv1.2 TLSv1.3;` 도 `TLSv1.2 TLSv1.3` 으로 정리합니다.

```bash
sudo nginx -t && sudo systemctl reload nginx
curl --cacert /etc/nginx/ssl/internal-ca.crt -s -o /dev/null -w "%{http_code}\n" https://192.168.0.177/   # 200
```

**181 HAProxy** — `backend nginx_servers`

```haproxy
    server nginx1 192.168.0.177:443 ssl verify required ca-file /etc/haproxy/certs/internal-ca.crt check check-ssl inter 3s fall 3 rise 2
    server nginx2 192.168.0.178:443 ssl verify required ca-file /etc/haproxy/certs/internal-ca.crt check check-ssl inter 3s fall 3 rise 2
```

```bash
sudo haproxy -c -f /etc/haproxy/haproxy.cfg && sudo systemctl reload haproxy
```

stats 화면에서 nginx1, nginx2 가 **UP** 인지 확인한 뒤, 필요하면 177·178 의 `listen 80` 을 제거합니다.

#### 2단계-B. 177·178 → 179

**179 HAProxy** — `frontend webserver` 에 443 추가 (전환 완료 전까지 80 유지)

```haproxy
frontend webserver
    bind *:80
    bind *:443 ssl crt /etc/haproxy/certs/internal.pem
    mode http
    option forwardfor
    default_backend fastapi-server
```

```bash
sudo haproxy -c -f /etc/haproxy/haproxy.cfg && sudo systemctl reload haproxy
curl --cacert /etc/haproxy/certs/internal-ca.crt -s https://192.168.0.179/health   # {"status":"ok"}
```

**177·178 nginx** — `location /api/`

```nginx
location /api/ {
    proxy_pass https://192.168.0.179;
    proxy_ssl_verify on;
    proxy_ssl_trusted_certificate /etc/nginx/ssl/internal-ca.crt;
    proxy_ssl_name 192.168.0.179;
    proxy_ssl_session_reuse on;

    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;
    proxy_read_timeout 30s;
    client_max_body_size 1m;
}
```

```bash
sudo nginx -t && sudo systemctl reload nginx
```

두 서버 모두 정상이면 179 의 `bind *:80` 을 제거합니다.

#### 2단계-C. 179 → 175·176

**175·176 FastAPI** — `/etc/systemd/system/tikit-api.service` (176 은 `176.*`)

```ini
ExecStart=/home/test/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8443 --workers 2 \
  --ssl-certfile /home/test/ssl/175.crt \
  --ssl-keyfile /home/test/ssl/175.key \
  --proxy-headers --forwarded-allow-ips=192.168.0.179
```

```bash
sudo systemctl daemon-reload && sudo systemctl restart tikit-api
curl --cacert /home/test/ssl/internal-ca.crt -s https://192.168.0.175:8443/health   # {"status":"ok"}
```

**179 HAProxy** — `backend fastapi-server`

```haproxy
    server fastapi1 192.168.0.175:8443 ssl verify required ca-file /etc/haproxy/certs/internal-ca.crt check check-ssl inter 3s fall 3 rise 2
    server fastapi2 192.168.0.176:8443 ssl verify required ca-file /etc/haproxy/certs/internal-ca.crt check check-ssl inter 3s fall 3 rise 2
```

> 무중단 순서: **175 전환 → 179 의 fastapi1 줄 수정·reload → 176 전환 → fastapi2 줄 수정·reload**
> uvicorn 이 TLS 를 직접 처리하면 CPU 사용량이 늘어납니다. 부하 테스트에 영향이 크면 2-C 만 HTTP 로 유지하는 것도 선택지입니다.

#### 2단계 확인

```bash
for t in 192.168.0.177:443 192.168.0.178:443 192.168.0.179:443 192.168.0.175:8443 192.168.0.176:8443; do
  printf "%s  " $t
  echo | openssl s_client -connect $t -CAfile internal-ca.crt 2>/dev/null | grep "Verify return code"
done
# 모두 Verify return code: 0 (ok)
```

---

### 8-6. SSL 문제 해결

| 증상 | 원인 / 조치 |
|---|---|
| `https://` 접속 시 `Connection refused` | `haproxy.cfg` 에 `bind *:443` 이 저장되지 않음 → `grep -n 443 /etc/haproxy/haproxy.cfg`, `ss -tlnp \| grep :443` 확인 |
| 브라우저 `ERR_CERT_COMMON_NAME_INVALID` / curl `SEC_E_WRONG_PRINCIPAL` | IP 또는 인증서에 없는 이름으로 접속 → `https://www.yaaho.kro.kr` 로 접속 |
| Linux curl·Python 에서 `unable to verify the first certificate` (브라우저는 정상) | `tikit.pem` 에 중간 인증서(`ca_bundle.crt`) 누락, 또는 PEM 수정 후 reload 안 함 |
| PEM 을 고쳤는데 그대로임 | HAProxy 는 reload 시에만 인증서를 읽음 → `sudo systemctl reload haproxy` |
| 가끔 접속이 안 되거나 다른 사이트가 열림 | 도메인 DNS 에 다른 A 레코드가 있음 → `nslookup` 으로 `192.168.0.181` 하나만인지 확인 |
| HAProxy 시작 실패 `unable to load SSL private key` | PEM 에 키 누락, 또는 키에 암호가 걸려 있음 |
| `tee: /etc/harpoxy/...: No such file or directory` | 경로 오타 (`haproxy`) |
| 로그인 후 리다이렉트 주소가 `http://` | 177·178 nginx 의 `X-Forwarded-Proto` 가 `$scheme` 으로 남아 있음 (8-4 ⑤) |
| (2단계) stats 에서 `SSL handshake failure` | 내부 인증서 SAN IP 불일치 또는 `internal-ca.crt` 로 검증 불가 |
| (2단계) nginx `502` + `upstream SSL certificate verify error` | `proxy_ssl_trusted_certificate` 경로, `proxy_ssl_name` 확인 |

### 8-7. 인증서 갱신 (ZeroSSL, 90일)

현재 인증서 만료일: **2027-01-13** — 만료 2주 전까지 갱신합니다.

1. ZeroSSL 에서 `www.yaaho.kro.kr` 인증서를 재발급하고 `certificate.crt`, `ca_bundle.crt`, `private.key` 를 받습니다.
2. 181 의 `/home/test/ssl/` 에 덮어씁니다 (`private.key` 는 `chmod 600`).
3. 8-3 의 점검 명령으로 도메인·유효기간·키 짝을 확인합니다.
4. 8-4 ② 의 명령으로 `tikit.pem` 을 다시 만듭니다.
5. **`sudo systemctl reload haproxy`** — 빼먹으면 이전 인증서가 계속 사용됩니다.
6. 8-4 ⑥ 의 확인 명령으로 새 만료일과 `Verify return code: 0 (ok)` 를 확인합니다.
   ```bash
   echo | openssl s_client -connect 127.0.0.1:443 -servername www.yaaho.kro.kr 2>/dev/null | openssl x509 -noout -enddate
   ```

기타

- 키 파일이 저장소에 들어가지 않도록 `*.key`, `*.pem` 을 `.gitignore` 에 추가합니다.
- 로컬 개발에서 Vite 프록시 대상을 HTTPS 로 바꿀 경우, 공인 인증서는 별도 설정 없이 동작합니다. 내부 사설 인증서 서버로 직접 연결할 때만 `NODE_EXTRA_CA_CERTS=internal-ca.crt` 또는 `secure: false` 가 필요합니다.
