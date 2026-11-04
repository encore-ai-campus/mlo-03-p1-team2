"""Local TIKIT server. Python standard library only; never serves the DB."""
import argparse
import hashlib
import hmac
import json
import re
import secrets
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timedelta, timezone, date
from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
FRONTEND_ROOT = ROOT / 'frontend' / 'dist'
ITERATIONS = 600_000
MBTIS = {a+b+c+d for a in 'IE' for b in 'NS' for c in 'TF' for d in 'JP'}


def now():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def connect(path):
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    return db


def initialize(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(path)) as db, db:
        db.execute('PRAGMA journal_mode=WAL')
        db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
          id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
          password_hash TEXT NOT NULL, salt TEXT NOT NULL, mbti TEXT NOT NULL,
          consent INTEGER NOT NULL, consented_at TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions (
          token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), expires_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS performances (id TEXT PRIMARY KEY, title TEXT NOT NULL, data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS reservations (
          id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
          performance_id TEXT NOT NULL REFERENCES performances(id), performance_title TEXT NOT NULL,
          category TEXT NOT NULL, venue TEXT NOT NULL, performance_date TEXT NOT NULL,
          session_time TEXT NOT NULL, seat_grade TEXT NOT NULL CHECK(seat_grade IN ('STANDARD','PREMIUM')),
          quantity INTEGER NOT NULL CHECK(quantity BETWEEN 1 AND 4), unit_price INTEGER NOT NULL,
          amount INTEGER NOT NULL CHECK(amount>=0), mbti TEXT NOT NULL,
          status TEXT NOT NULL CHECK(status IN ('REQUESTED','CONFIRMED','CANCELLED')),
          request_key TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
          cancelled_at TEXT, UNIQUE(user_id, request_key));
        CREATE TABLE IF NOT EXISTS payments (
          id TEXT PRIMARY KEY, reservation_id TEXT NOT NULL UNIQUE REFERENCES reservations(id),
          amount INTEGER NOT NULL CHECK(amount>=0), currency TEXT NOT NULL DEFAULT 'KRW',
          status TEXT NOT NULL CHECK(status IN ('PENDING','COMPLETED','CANCELLED')),
          requested_at TEXT NOT NULL, completed_at TEXT, cancelled_at TEXT, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events (
          id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), mbti TEXT NOT NULL,
          performance_id TEXT NOT NULL REFERENCES performances(id), reservation_id TEXT REFERENCES reservations(id),
          type TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS status_history (
          id TEXT PRIMARY KEY, reservation_id TEXT NOT NULL REFERENCES reservations(id),
          user_id TEXT NOT NULL REFERENCES users(id), entity TEXT NOT NULL,
          from_status TEXT, to_status TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS reservations_user ON reservations(user_id,created_at);
        CREATE INDEX IF NOT EXISTS events_analysis ON events(performance_id,type,created_at);
        CREATE INDEX IF NOT EXISTS history_reservation ON status_history(reservation_id,created_at);
        ''')
        for show in json.loads((ROOT / 'performances.json').read_text(encoding='utf-8')):
            db.execute('INSERT OR IGNORE INTO performances VALUES (?,?,?)',
                       (show['id'], show['title'], json.dumps(show, ensure_ascii=False)))


class APIError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


def public_user(row):
    return {key: row[key] for key in ('id', 'name', 'email', 'mbti', 'consent')} | {'consentedAt': row['consented_at']}


def event(db, user, show_id, kind, timestamp, reservation_id=None):
    if user['consent']:
        db.execute('INSERT INTO events VALUES (?,?,?,?,?,?,?)',
                   (str(uuid.uuid4()), user['id'], user['mbti'], show_id, reservation_id, kind, timestamp))


def history(db, rid, uid, entity, before, after, timestamp):
    db.execute('INSERT INTO status_history VALUES (?,?,?,?,?,?,?)',
               (str(uuid.uuid4()), rid, uid, entity, before, after, timestamp))


ORDER_QUERY = '''SELECT r.*, p.id AS payment_id, p.status AS payment_status,
 p.requested_at, p.completed_at, p.cancelled_at AS payment_cancelled_at
 FROM reservations r JOIN payments p ON p.reservation_id=r.id'''


def order_dict(row):
    keys = {'id':'id', 'userId':'user_id', 'performanceId':'performance_id',
            'performanceTitle':'performance_title', 'category':'category', 'venue':'venue',
            'performanceDate':'performance_date', 'sessionTime':'session_time', 'seatGrade':'seat_grade',
            'quantity':'quantity', 'unitPrice':'unit_price', 'amount':'amount', 'mbti':'mbti',
            'status':'status', 'createdAt':'created_at', 'updatedAt':'updated_at', 'cancelledAt':'cancelled_at',
            'paymentId':'payment_id', 'paymentStatus':'payment_status', 'requestedAt':'requested_at',
            'completedAt':'completed_at', 'paymentCancelledAt':'payment_cancelled_at'}
    return {key: row[col] for key, col in keys.items()} | {'currency':'KRW', 'isMock':True}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, request, client_address, server, **kwargs):
        super().__init__(request, client_address, server, directory=str(server.frontend_dir), **kwargs)

    def do_GET(self):
        if urlsplit(self.path).path.startswith('/api/'):
            self.api()
        else:
            super().do_GET()

    def send_head(self):
        # GET and HEAD share this boundary: only the built page and its assets.
        path = unquote(urlsplit(self.path).path)
        root = self.server.frontend_dir.resolve()
        if path in ('/', '/index.html'):
            if not (root / 'index.html').is_file():
                self.send_error(503, 'Vue build missing. Run: cd frontend && npm ci && npm run build')
                return None
        elif not path.startswith('/assets/'):
            self.send_error(404)
            return None
        if '\\' in path or '\x00' in path or any(part.startswith('.') for part in path.split('/') if part):
            self.send_error(404)
            return None
        target = (root / ('index.html' if path == '/' else path.lstrip('/'))).resolve()
        if not target.is_relative_to(root) or not target.is_file():
            self.send_error(404)
            return None
        return super().send_head()

    def do_POST(self):
        self.api()

    def send_json(self, status, body, cookie=None):
        raw = json.dumps(body, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(raw)

    def body(self):
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 16384:
                raise ValueError()
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                raise ValueError()
            result = json.loads(self.rfile.read(size))
            if not isinstance(result, dict):
                raise ValueError()
            if any(not isinstance(value, (str, int, float, bool, type(None))) for value in result.values()):
                raise ValueError()
            return result
        except (ValueError, UnicodeError):
            raise APIError(400, '올바른 JSON 요청을 보내 주세요.')

    def session_hash(self):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get('Cookie', ''))
            token = cookie['tikit_session'].value if 'tikit_session' in cookie else ''
        except Exception:
            token = ''
        return hashlib.sha256(token.encode()).hexdigest()

    def user(self, db, required=True):
        user = db.execute('''SELECT u.* FROM users u JOIN sessions s ON s.user_id=u.id
                           WHERE s.token_hash=? AND s.expires_at>?''', (self.session_hash(), now())).fetchone()
        if user is None and required:
            raise APIError(401, '로그인 후 이용해 주세요.')
        return user

    def start_session(self, db, uid):
        token = secrets.token_urlsafe(32)
        expiry = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        db.execute('DELETE FROM sessions WHERE expires_at<? OR token_hash=?', (now(), self.session_hash()))
        db.execute('INSERT INTO sessions VALUES (?,?,?)', (hashlib.sha256(token.encode()).hexdigest(), uid, expiry))
        return f'tikit_session={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=604800'

    def api(self):
        try:
            host = self.headers.get('Host', '')
            # Block DNS rebinding and cross-site writes, including localhost attackers.
            if host not in {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}:
                raise APIError(403, '허용되지 않은 호스트입니다.')
            if self.command == 'POST':
                origin = self.headers.get('Origin')
                if (origin and origin != f'http://{host}') or self.headers.get('Sec-Fetch-Site') == 'cross-site':
                    raise APIError(403, '동일한 사이트에서 요청해 주세요.')
            with closing(connect(self.server.db_path)) as db, db:
                # Serialize writes so complete/cancel/retry races cannot duplicate transitions.
                if self.command == 'POST':
                    db.execute('BEGIN IMMEDIATE')
                status, result, cookie = self.route(db)
            self.send_json(status, result, cookie)
        except APIError as exc:
            self.send_json(exc.status, {'error':exc.message})
        except sqlite3.IntegrityError:
            self.send_json(409, {'error':'이미 사용 중인 이메일이거나 중복된 요청입니다.'})
        except Exception:
            import traceback
            traceback.print_exc()
            self.send_json(500, {'error':'서버 처리에 실패했습니다. 다시 시도해 주세요.'})

    def route(self, db):
        path = urlsplit(self.path).path
        method = self.command
        if method == 'GET' and path == '/api/performances':
            return 200, [json.loads(r['data']) for r in db.execute('SELECT data FROM performances ORDER BY rowid')], None
        if method == 'GET' and path == '/api/me':
            user = self.user(db, False)
            return 200, public_user(user) if user else None, None
        if method == 'POST' and path in ('/api/auth/signup', '/api/auth/login'):
            data = self.body()
            email, password = data.get('email'), data.get('password')
            if not isinstance(email, str) or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email.strip()) or len(email) > 100:
                raise APIError(400, '올바른 이메일을 입력해 주세요.')
            if not isinstance(password, str) or not 8 <= len(password) <= 128:
                raise APIError(400, '비밀번호는 8~128자로 입력해 주세요.')
            email = email.strip().lower()
            user = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
            if path.endswith('signup'):
                name = data.get('name')
                if not isinstance(name, str) or not 1 <= len(name.strip()) <= 20 or data.get('mbti') not in MBTIS or data.get('consent') is not True:
                    raise APIError(400, '닉네임, MBTI와 수집 동의를 확인해 주세요.')
                if user:
                    raise APIError(409, '이미 가입된 이메일입니다. 로그인해 주세요.')
                salt, uid, timestamp = secrets.token_hex(16), str(uuid.uuid4()), now()
                hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), ITERATIONS).hex()
                db.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)',
                           (uid, name.strip(), email, hashed, salt, data['mbti'], 1, timestamp, timestamp))
                user = db.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
            else:
                salt = user['salt'] if user else '0' * 32
                hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), ITERATIONS).hex()
                if not user or not hmac.compare_digest(hashed, user['password_hash']):
                    raise APIError(401, '이메일 또는 비밀번호가 일치하지 않습니다.')
            return (201 if path.endswith('signup') else 200), public_user(user), self.start_session(db, user['id'])
        if method == 'POST' and path == '/api/auth/logout':
            db.execute('DELETE FROM sessions WHERE token_hash=?', (self.session_hash(),))
            return 200, {'ok':True}, 'tikit_session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0'
        user = self.user(db)
        if method == 'GET' and path in ('/api/reservations', '/api/payments'):
            rows = db.execute(ORDER_QUERY + ' WHERE r.user_id=? ORDER BY r.created_at DESC', (user['id'],))
            return 200, [order_dict(row) for row in rows], None
        if method == 'POST' and path == '/api/events':
            data = self.body()
            if data.get('type') not in ('performance_view', 'booking_started'):
                raise APIError(400, '허용되지 않은 이벤트입니다.')
            if not db.execute('SELECT 1 FROM performances WHERE id=?', (data.get('performanceId'),)).fetchone():
                raise APIError(400, '공연을 찾을 수 없습니다.')
            event(db, user, data['performanceId'], data['type'], now())
            return 201, {'ok':True}, None
        if method == 'POST' and path == '/api/reservations':
            data = self.body()
            row = db.execute('SELECT data FROM performances WHERE id=?', (data.get('performanceId'),)).fetchone()
            if row is None:
                raise APIError(400, '공연을 찾을 수 없습니다.')
            show = json.loads(row['data'])
            dates = [(date.fromisoformat(show['start']) + timedelta(days=i)).isoformat() for i in range(show['days'])]
            if (data.get('performanceDate') not in dates or data.get('sessionTime') not in show['slots']
                or data.get('seatGrade') not in ('STANDARD','PREMIUM')
                or type(data.get('quantity')) is not int or not 1 <= data['quantity'] <= 4):
                raise APIError(400, '공연 날짜, 회차, 좌석과 수량을 확인해 주세요.')
            try:
                key = str(uuid.UUID(data.get('requestKey', '')))
            except (ValueError, TypeError, AttributeError):
                raise APIError(400, '예매 요청 키가 올바르지 않습니다.')
            existing = db.execute(ORDER_QUERY + ' WHERE r.user_id=? AND r.request_key=?', (user['id'], key)).fetchone()
            if existing:
                pairs = [('performanceId','performance_id'), ('performanceDate','performance_date'),
                         ('sessionTime','session_time'), ('seatGrade','seat_grade'), ('quantity','quantity')]
                if any(data[a] != existing[b] for a,b in pairs):
                    raise APIError(409, '이미 사용한 예매 요청 키입니다. 예매 창을 다시 열어 주세요.')
                return 200, order_dict(existing), None
            rid, pid, timestamp = str(uuid.uuid4()), str(uuid.uuid4()), now()
            price = show['price'] + (30000 if data['seatGrade'] == 'PREMIUM' else 0)
            amount = price * data['quantity']
            db.execute('''INSERT INTO reservations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                       (rid, user['id'], show['id'], show['title'], show['category'], show['venue'],
                        data['performanceDate'], data['sessionTime'], data['seatGrade'], data['quantity'], price,
                        amount, user['mbti'], 'REQUESTED', key, timestamp, timestamp, None))
            db.execute('INSERT INTO payments VALUES (?,?,?,?,?,?,?,?,?)',
                       (pid, rid, amount, 'KRW', 'PENDING', timestamp, None, None, timestamp))
            history(db, rid, user['id'], 'reservation', None, 'REQUESTED', timestamp)
            history(db, rid, user['id'], 'payment', None, 'PENDING', timestamp)
            event(db, user, show['id'], 'reservation_requested', timestamp, rid)
            return 201, order_dict(db.execute(ORDER_QUERY + ' WHERE r.id=?', (rid,)).fetchone()), None
        match = re.fullmatch(r'/api/reservations/([a-f0-9-]+)/(complete|cancel)', path)
        if method == 'POST' and match:
            rid, action = match.groups()
            row = db.execute(ORDER_QUERY + ' WHERE r.id=? AND r.user_id=?', (rid, user['id'])).fetchone()
            if row is None:
                raise APIError(404, '예매 내역을 찾을 수 없습니다.')
            new_r, new_p = ('CONFIRMED','COMPLETED') if action == 'complete' else ('CANCELLED','CANCELLED')
            if row['status'] == new_r:
                return 200, order_dict(row), None
            if action == 'complete' and row['status'] == 'CANCELLED':
                raise APIError(409, '취소한 예매는 결제할 수 없습니다.')
            timestamp = now()
            db.execute('UPDATE reservations SET status=?, updated_at=?, cancelled_at=? WHERE id=?',
                       (new_r, timestamp, timestamp if action == 'cancel' else None, rid))
            time_col = 'completed_at' if action == 'complete' else 'cancelled_at'
            db.execute(f'UPDATE payments SET status=?, updated_at=?, {time_col}=? WHERE reservation_id=?',
                       (new_p, timestamp, timestamp, rid))
            history(db, rid, user['id'], 'reservation', row['status'], new_r, timestamp)
            history(db, rid, user['id'], 'payment', row['payment_status'], new_p, timestamp)
            event(db, user, row['performance_id'], 'payment_completed' if action == 'complete' else 'reservation_cancelled', timestamp, rid)
            return 200, order_dict(db.execute(ORDER_QUERY + ' WHERE r.id=?', (rid,)).fetchone()), None
        raise APIError(404, '요청한 API를 찾을 수 없습니다.')


def make_server(db_path, port=8000, frontend_dir=None):
    initialize(db_path)
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.db_path = str(db_path)
    server.frontend_dir = Path(frontend_dir) if frontend_dir is not None else FRONTEND_ROOT
    return server


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--db', type=Path, default=ROOT / 'data' / 'tikit.sqlite3')
    args = parser.parse_args()
    server = make_server(args.db, args.port)
    print(f'TIKIT: http://127.0.0.1:{server.server_port} (Ctrl+C to stop)', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
