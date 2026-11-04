"""Real local HTTP + SQLite regression tests; no external services or packages."""
import http.client
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import make_server


class Client:
    def __init__(self, port):
        self.port, self.cookie = port, ''

    def request(self, method, path, data=None, **headers):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=15)
        body = json.dumps(data).encode() if data is not None else None
        conn.request(method, path, body, {'Content-Type':'application/json', 'Cookie':self.cookie, **headers})
        response = conn.getresponse()
        cookie = response.getheader('Set-Cookie')
        if cookie is not None:
            self.cookie = cookie.split(';')[0]
        raw = response.read()
        content_type = response.getheader('Content-Type', '')
        result = json.loads(raw) if 'application/json' in content_type else raw
        status = response.status
        conn.close()
        return status, result


class BookingAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp.name) / 'test.sqlite3'
        frontend = Path(cls.temp.name) / 'dist'
        frontend.mkdir()
        (frontend / 'index.html').write_text('<div id="app"></div>', encoding='utf-8')
        cls.server = make_server(cls.db_path, 0, frontend_dir=frontend)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def setUp(self):
        self.client = Client(self.server.server_port)
        self.email = f'{uuid.uuid4()}@example.com'
        status, self.user = self.client.request('POST', '/api/auth/signup', {
            'name':'테스트 관객', 'email':self.email, 'password':'example-password', 'mbti':'INFP', 'consent':True})
        self.assertEqual(status, 201)

    def payload(self, **changes):
        return {'performanceId':'city', 'performanceDate':'2026-11-21', 'sessionTime':'18:00',
                'seatGrade':'PREMIUM', 'quantity':2, 'requestKey':str(uuid.uuid4()), **changes}

    def create(self, **changes):
        status, order = self.client.request('POST', '/api/reservations', self.payload(**changes))
        self.assertEqual(status, 201, order)
        return order

    def action(self, order, action, client=None):
        return (client or self.client).request('POST', f"/api/reservations/{order['id']}/{action}", {})

    def test_request_complete_cancel_preserves_times_and_history(self):
        order = self.create(amount=1, userId='forged', status='COMPLETED')
        self.assertEqual((order['status'], order['paymentStatus']), ('REQUESTED','PENDING'))
        self.assertEqual(order['amount'], 258000)
        self.assertEqual(order['userId'], self.user['id'])
        self.assertIsNone(order['completedAt'])
        self.assertTrue(order['requestedAt'])
        status, paid = self.action(order, 'complete')
        self.assertEqual(status, 200)
        self.assertEqual((paid['status'], paid['paymentStatus']), ('CONFIRMED','COMPLETED'))
        self.assertTrue(paid['completedAt'])
        self.assertEqual(self.action(order, 'complete')[1]['completedAt'], paid['completedAt'])
        status, cancelled = self.action(order, 'cancel')
        self.assertEqual(status, 200)
        self.assertEqual((cancelled['status'], cancelled['paymentStatus']), ('CANCELLED','CANCELLED'))
        self.assertEqual(cancelled['cancelledAt'], cancelled['paymentCancelledAt'])
        self.assertEqual(cancelled['completedAt'], paid['completedAt'])
        self.assertEqual(cancelled['amount'], 258000)
        self.assertEqual(self.action(order, 'cancel')[1]['cancelledAt'], cancelled['cancelledAt'])
        self.assertEqual(self.action(order, 'complete')[0], 409)
        with closing(sqlite3.connect(self.db_path)) as db:
            history = db.execute('SELECT COUNT(*) FROM status_history WHERE reservation_id=?', (order['id'],)).fetchone()[0]
            events = db.execute('SELECT type FROM events WHERE reservation_id=? ORDER BY created_at', (order['id'],)).fetchall()
        self.assertEqual(history, 6)
        self.assertEqual([e[0] for e in events], ['reservation_requested','payment_completed','reservation_cancelled'])

    def test_cancel_pending(self):
        order = self.create()
        status, result = self.action(order, 'cancel')
        self.assertEqual(status, 200)
        self.assertEqual(result['paymentStatus'], 'CANCELLED')
        self.assertIsNone(result['completedAt'])

    def test_owner_isolation_and_authentication(self):
        order = self.create()
        stranger = Client(self.server.server_port)
        self.assertEqual(stranger.request('GET', '/api/reservations')[0], 401)
        self.assertEqual(self.action(order, 'cancel', stranger)[0], 401)
        stranger.request('POST', '/api/auth/signup', {'name':'다른 관객', 'email':f'{uuid.uuid4()}@example.com',
                        'password':'other-password', 'mbti':'ENTJ', 'consent':True})
        self.assertEqual(stranger.request('GET','/api/reservations')[1], [])
        self.assertEqual(stranger.request('GET','/api/payments')[1], [])
        for action in ('cancel','complete'):
            self.assertEqual(self.action(order, action, stranger)[0], 404)

    def test_duplicate_and_concurrent_requests(self):
        data = self.payload()
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: self.client.request('POST','/api/reservations',data), range(4)))
        self.assertEqual(sorted(s for s,r in results), [200,200,200,201])
        self.assertEqual(len({r['id'] for s,r in results}), 1)
        self.assertEqual(self.client.request('POST','/api/reservations', {**data,'quantity':1})[0],409)

    def test_concurrent_complete_and_cancel_are_consistent(self):
        order = self.create()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda action:self.action(order,action), ['complete','cancel']))
        self.assertIn(results[0][0], (200,409))
        self.assertEqual(results[1][0], 200)
        result = self.client.request('GET','/api/reservations')[1][0]
        self.assertEqual((result['status'],result['paymentStatus']),('CANCELLED','CANCELLED'))

    def test_validation_and_event_collection(self):
        for changes in ({'quantity':0},{'quantity':5},{'quantity':True},{'performanceId':'missing'},
                        {'performanceDate':'2027-01-01'},{'sessionTime':'01:00'}, {'seatGrade':'VIP'},
                        {'requestKey':'bad'}, {'performanceId':{'bad':True}}):
            with self.subTest(changes=changes):
                self.assertEqual(self.client.request('POST','/api/reservations',self.payload(**changes))[0],400)
        for kind in ('performance_view','booking_started'):
            self.assertEqual(self.client.request('POST','/api/events',{'type':kind,'performanceId':'city'})[0],201)
        self.assertEqual(self.client.request('POST','/api/events',{'type':'payment_completed','performanceId':'city'})[0],400)

    def test_logout_login_persistence_and_password_hash(self):
        order = self.create()
        old_cookie = self.client.cookie
        self.assertEqual(self.client.request('POST','/api/auth/logout',{})[0],200)
        self.assertIsNone(self.client.request('GET','/api/me')[1])
        stale = Client(self.server.server_port)
        stale.cookie = old_cookie
        self.assertEqual(stale.request('GET','/api/reservations')[0],401)
        self.assertEqual(self.client.request('POST','/api/auth/login',{'email':self.email,'password':'wrong-pass'})[0],401)
        self.assertEqual(self.client.request('POST','/api/auth/login',{'email':self.email,'password':'example-password'})[0],200)
        self.assertEqual(self.client.request('GET','/api/reservations')[1][0]['id'],order['id'])
        self.assertEqual(self.client.request('GET','/api/payments')[1][0]['paymentId'],order['paymentId'])
        with closing(sqlite3.connect(self.db_path)) as db:
            hashed, salt = db.execute('SELECT password_hash,salt FROM users WHERE id=?',(self.user['id'],)).fetchone()
        self.assertNotEqual(hashed,'example-password')
        self.assertEqual(len(salt),32)
        # A separately initialized server opens the same durable database.
        restarted = make_server(self.db_path,0)
        thread = threading.Thread(target=restarted.serve_forever,daemon=True)
        thread.start()
        try:
            client = Client(restarted.server_port)
            client.cookie = self.client.cookie
            self.assertEqual(client.request('GET','/api/reservations')[1][0]['id'],order['id'])
        finally:
            restarted.shutdown()
            restarted.server_close()
            thread.join()

    def test_origin_and_static_file_protection(self):
        self.assertEqual(self.client.request('POST','/api/reservations',self.payload(),Origin='https://other.example')[0],403)
        self.assertEqual(self.client.request('POST','/api/reservations',self.payload(),Host='attacker.example')[0],403)
        for path in ('/server.py','/data/tikit.sqlite3','/../server.py'):
            self.assertEqual(self.client.request('GET',path)[0],404)
        self.assertEqual(self.client.request('GET','/')[0],200)
        self.assertEqual(len(self.client.request('GET','/api/performances')[1]),8)


class FrontendServing(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.frontend = self.root / 'dist'
        (self.frontend / 'assets').mkdir(parents=True)
        (self.frontend / 'index.html').write_text('<div id="app"></div>', encoding='utf-8')
        (self.frontend / 'assets' / 'app-123.js').write_text('console.log("vue")', encoding='utf-8')
        (self.root / 'private.txt').write_text('private', encoding='utf-8')
        self.server = make_server(self.root / 'test.sqlite3', 0, frontend_dir=self.frontend)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.client = Client(self.server.server_port)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def test_serves_vue_page_and_hashed_assets(self):
        for path in ('/', '/index.html', '/?page=home'):
            self.assertEqual(self.client.request('GET', path), (200, b'<div id="app"></div>'))
        self.assertEqual(self.client.request('GET', '/assets/app-123.js?v=1'), (200, b'console.log("vue")'))
        self.assertEqual(self.client.request('HEAD', '/assets/app-123.js'), (200, b''))

    def test_private_paths_and_traversal_are_not_served(self):
        for path in ('/server.py', '/data/tikit.sqlite3', '/static/index.html', '/src/App.vue',
                     '/package.json', '/assets/', '/assets/missing.js', '/assets/../index.html',
                     '/assets/%2e%2e/%2e%2e/private.txt', '/assets/%5c..%5cprivate.txt',
                     '/assets/%00.js'):
            for method in ('GET', 'HEAD'):
                with self.subTest(path=path, method=method):
                    self.assertEqual(self.client.request(method, path)[0], 404)

    def test_missing_build_explains_build_step_and_keeps_api_available(self):
        (self.frontend / 'index.html').unlink()
        status, body = self.client.request('GET', '/')
        self.assertEqual(status, 503)
        self.assertIn(b'npm run build', body)
        self.assertEqual(self.client.request('GET', '/api/performances')[0], 200)


if __name__ == '__main__':
    unittest.main()
