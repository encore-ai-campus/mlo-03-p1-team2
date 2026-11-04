"""Opt-in real HTTP + MariaDB checks using a separate, explicitly named DB."""
import os
import sys
import tempfile
import threading
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server
from test_api import Client


@unittest.skipUnless(os.environ.get('MARIADB_TEST_DATABASE'), 'MARIADB_TEST_DATABASE not configured')
class MariaDBAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = server.mariadb_settings()
        test_database = os.environ['MARIADB_TEST_DATABASE']
        if test_database.casefold() == cls.config['database'].casefold():
            raise ValueError('MARIADB_TEST_DATABASE must differ from MARIADB_DATABASE')
        cls.config['database'] = test_database
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        frontend = Path(cls.temp.name)
        (frontend / 'index.html').write_text('<div id="app"></div>', encoding='utf-8')
        cls.server = server.make_mariadb_server(cls.config, port=0, frontend_dir=frontend)
        cls.addClassCleanup(cls.server.server_close)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.addClassCleanup(cls.thread.join)
        cls.addClassCleanup(cls.server.shutdown)

    def test_booking_concurrency_history_and_persistence(self):
        client = Client(self.server.server_port)
        email = f'{uuid.uuid4()}@example.com'
        status, user = client.request('POST', '/api/auth/signup', {
            'name': '마리아 관객', 'email': email, 'password': 'example-password',
            'mbti': 'INFP', 'consent': True,
        })
        self.assertEqual(status, 201, user)
        self.assertEqual(user['name'], '마리아 관객')
        shows = client.request('GET', '/api/performances')[1]
        show = shows[0]
        payload = {
            'performanceId': show['id'], 'performanceDate': show['start'],
            'sessionTime': show['slots'][0], 'seatGrade': 'STANDARD',
            'quantity': 2, 'requestKey': str(uuid.uuid4()),
        }
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: client.request('POST', '/api/reservations', payload), range(4)))
        self.assertEqual(sorted(status for status, _ in results), [200, 200, 200, 201], results)
        self.assertEqual(len({order['id'] for _, order in results}), 1)
        order = results[0][1]
        self.assertEqual(order['amount'], show['price'] * 2)
        base = f"/api/reservations/{order['id']}"
        with ThreadPoolExecutor(max_workers=2) as pool:
            actions = list(pool.map(lambda action: client.request('POST', base + '/' + action, {}), ('complete', 'cancel')))
        self.assertIn(actions[0][0], (200, 409), actions)
        self.assertEqual(actions[1][0], 200, actions)
        final = client.request('GET', '/api/reservations')[1][0]
        self.assertEqual((final['status'], final['paymentStatus']), ('CANCELLED', 'CANCELLED'))
        self.assertEqual(client.request('POST', base + '/complete', {})[0], 409)
        stranger = Client(self.server.server_port)
        self.assertEqual(stranger.request('POST', base + '/cancel', {})[0], 401)
        self.assertEqual(client.request('POST', '/api/auth/signup', {
            'name': '중복', 'email': email, 'password': 'example-password',
            'mbti': 'INFP', 'consent': True,
        })[0], 409)
        with closing(server.MariaDBConnection(self.config)) as db, db:
            count_before = db.execute('SELECT COUNT(*) AS n FROM status_history WHERE reservation_id=?', (order['id'],)).fetchone()['n']
        self.assertEqual(client.request('POST', base + '/cancel', {})[0], 200)
        server.initialize_mariadb(self.config)
        with closing(server.MariaDBConnection(self.config)) as db, db:
            self.assertEqual(db.execute('SELECT COUNT(*) AS n FROM status_history WHERE reservation_id=?', (order['id'],)).fetchone()['n'], count_before)
            self.assertEqual(db.execute('SELECT name FROM users WHERE id=?', (user['id'],)).fetchone()['name'], '마리아 관객')
            with self.assertRaises(RuntimeError):
                with db:
                    db.execute('UPDATE users SET name=? WHERE id=?', ('rollback', user['id']))
                    raise RuntimeError('force rollback')
            self.assertEqual(db.execute('SELECT name FROM users WHERE id=?', (user['id'],)).fetchone()['name'], '마리아 관객')
