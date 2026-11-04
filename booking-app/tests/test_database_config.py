"""Verify default DB routing and local credential loading without a live DB."""
import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server


class DatabaseRouting(unittest.TestCase):
    def test_normal_start_uses_mariadb(self):
        with patch.object(server, 'make_mariadb_server') as maria, patch.object(server, 'initialize') as sqlite:
            self.assertIs(server.server_from_args(['--port', '8123']), maria.return_value)
            maria.assert_called_once_with(port=8123, frontend_dir=None)
            sqlite.assert_not_called()

    def test_connection_error_does_not_fall_back_to_sqlite(self):
        with patch.object(server, 'make_mariadb_server', side_effect=ConnectionError('unavailable')), patch.object(server, 'initialize') as sqlite:
            with self.assertRaises(ConnectionError):
                server.server_from_args([])
            sqlite.assert_not_called()

    def test_sqlite_remains_explicitly_available(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / 'compat.sqlite3'
            http_server = server.server_from_args(['--backend', 'sqlite', '--db', str(db_path), '--port', '0'])
            try:
                self.assertTrue(db_path.is_file())
                self.assertEqual(http_server.db_path, str(db_path))
            finally:
                http_server.server_close()

    def test_sqlite_path_requires_explicit_backend(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            server.server_from_args(['--db', 'unexpected.sqlite3'])
        self.assertEqual(error.exception.code, 2)


class MariaDBSettings(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.patch_root = patch.object(server, 'ROOT', self.root)
        self.patch_root.start()
        self.addCleanup(self.patch_root.stop)
        self.patch_env = patch.dict(os.environ, {}, clear=True)
        self.patch_env.start()
        self.addCleanup(self.patch_env.stop)

    def test_loads_app_env_and_preserves_password_characters(self):
        (self.root / '.env').write_text(
            'MARIADB_USER=tikit_app\nMARIADB_DATABASE=tikit\n'
            'MARIADB_PASSWORD="literal${VALUE}#?password"\nMARIADB_PORT=3307\n',
            encoding='utf-8-sig',
        )
        config = server.mariadb_settings()
        self.assertEqual(config['password'], 'literal${VALUE}#?password')
        self.assertEqual(config['user'], 'tikit_app')
        self.assertEqual(config['port'], 3307)
        self.assertEqual(config['host'], '127.0.0.1')

    def test_process_environment_takes_precedence(self):
        (self.root / '.env').write_text('MARIADB_USER=file_user\nMARIADB_DATABASE=tikit\nMARIADB_PASSWORD=file_password\n', encoding='utf-8')
        os.environ['MARIADB_USER'] = 'process_user'
        self.assertEqual(server.mariadb_settings()['user'], 'process_user')

    def test_missing_password_stops_startup_without_sqlite(self):
        (self.root / '.env').write_text('MARIADB_USER=tikit_app\nMARIADB_DATABASE=tikit\nMARIADB_PASSWORD=\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'MARIADB_PASSWORD'):
            server.mariadb_settings()
