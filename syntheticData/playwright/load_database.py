"""Read-only evidence; API writes never bypass the service."""
import sys
from collections import Counter
from pathlib import Path

from pymongo import MongoClient
from sqlalchemy import bindparam, create_engine, text

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.core.config import Settings


class Evidence:
    def __init__(self, emails, run_id):
        settings = Settings(_env_file=ROOT / 'backend' / '.env')
        self.engine = create_engine(settings.database_url, pool_pre_ping=True,
                                   connect_args={'connect_timeout': 5, 'read_timeout': 10})
        self.mongo = MongoClient(settings.mongodb_url, serverSelectionTimeoutMS=5000,
                                 socketTimeoutMS=10000)
        self.collection = self.mongo[settings.mongodb_db][settings.mongodb_events_collection]
        self.run_id, self.emails = run_id, emails

    def query(self, sql, **params):
        statement = text(sql)
        if 'emails' in params:
            statement = statement.bindparams(bindparam('emails', expanding=True))
        if 'ids' in params:
            statement = statement.bindparams(bindparam('ids', expanding=True))
        with self.engine.connect() as connection:
            return [dict(r._mapping) for r in connection.execute(statement, params)]

    def members(self):
        return {r['email']: r for r in self.query(
            'SELECT id,email,name,mbti,consent,password_hash FROM users WHERE email IN :emails',
            emails=self.emails)}

    def counts(self):
        result = {'users': len(self.members())}
        for table in ('reservations', 'status_history', 'events', 'favorites', 'orders', 'notification_settings'):
            result[table] = self.query(
                f'SELECT COUNT(*) AS n FROM {table} t JOIN users u ON t.user_id=u.id WHERE u.email IN :emails',
                emails=self.emails)[0]['n']
        result['payments'] = self.query(
            'SELECT COUNT(*) AS n FROM payments p JOIN reservations r ON p.reservation_id=r.id '
            'JOIN users u ON r.user_id=u.id WHERE u.email IN :emails', emails=self.emails)[0]['n']
        result['tracking'] = self.collection.count_documents({'props.synthetic_run_id': self.run_id})
        return result

    def verify(self, baseline, reservation_ids):
        counts = self.counts()
        deltas = {k: counts[k] - baseline[k] for k in counts}
        issues = []
        states, business_events = {}, {}
        if any(v < 0 for v in deltas.values()):
            issues.append('Scoped database rows decreased during the run')
        if reservation_ids:
            rows = self.query(
                'SELECT r.id,r.status,r.amount,p.amount AS payment_amount,p.status AS payment_status '
                'FROM reservations r LEFT JOIN payments p ON p.reservation_id=r.id WHERE r.id IN :ids',
                ids=list(reservation_ids))
            if len(rows) != len(set(reservation_ids)):
                issues.append('A successfully acknowledged reservation is missing')
            mapping = {'REQUESTED': 'PENDING', 'CONFIRMED': 'COMPLETED', 'CANCELLED': 'CANCELLED'}
            if any(mapping.get(r['status']) != r['payment_status'] or r['amount'] != r['payment_amount'] for r in rows):
                issues.append('Reservation/payment state or amount mismatch')
            states = dict(Counter(r['status'] for r in rows))
            business_events = {r['type']: r['n'] for r in self.query(
                'SELECT type,COUNT(*) AS n FROM events WHERE reservation_id IN :ids GROUP BY type',
                ids=list(reservation_ids))}
        return dict(counts=counts, deltas=deltas, total=sum(deltas.values()), issues=issues,
                    reservation_states=states, business_events=business_events)

    def close(self):
        self.engine.dispose()
        self.mongo.close()
