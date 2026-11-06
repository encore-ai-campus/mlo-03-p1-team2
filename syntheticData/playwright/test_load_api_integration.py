"""Exercise real API routes using SQLite and an in-memory Mongo substitute.

ASGITransport makes no network connections; production DB dependencies are
overridden before the first request.
"""
import tempfile
import time
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

import httpx
from pymongo.errors import BulkWriteError
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from syntheticData.playwright.load_client import Api
from syntheticData.playwright.load_control import Metrics
from syntheticData.playwright.load_test import Campaign
from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.db.mongo import get_event_collection
from app.db.seed import seed
from app.models import User, Reservation, Payment, StatusHistory, Event, Favorite


class MemoryMongo:
    def __init__(self):
        self.docs = {}

    def insert_many(self, docs, ordered=False):
        errors = []
        for doc in docs:
            if doc['_id'] in self.docs:
                errors.append({'code': 11000})
            else:
                self.docs[doc['_id']] = doc
        if errors:
            raise BulkWriteError({'writeErrors': errors})


class ApiIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_workflow_matches_reserved_cost_and_preserves_idempotency(self):
        engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            seed(db)
        def local_db():
            with Session(engine, expire_on_commit=False) as db:
                yield db
        mongo = MemoryMongo()
        previous = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = local_db
        app.dependency_overrides[get_event_collection] = lambda: mongo
        try:
            with (tempfile.TemporaryDirectory() as d,
                  patch('syntheticData.playwright.load_test.ARTIFACTS', Path(d)),
                  patch('app.core.security.get_settings', return_value=SimpleNamespace(
                      jwt_secret='offline-test-secret-at-least-32-bytes', jwt_algorithm='HS256', jwt_expire_minutes=60))):
                campaign = Campaign('offline-test')
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app)) as client:
                    api = Api(client, 'http://offline.test', campaign.budget, Metrics(), Path(d) / 'requests.jsonl')
                    campaign.api = api
                    signed = await api.call('POST', '/auth/signup', total=1, expected=(201,), payload=dict(
                        name='Offline User', email='offline@example.com', mbti='ENFP', consent=True,
                        password='offline-password-123', password_confirm='offline-password-123'))
                    account = dict(profile={'id': 'offline-persona', 'email': 'offline@example.com'},
                                   token=signed['access_token'], logged_at=time.monotonic())
                    await campaign.visit(account, 19, 'mixed', 'city')
                    rid = campaign.state['reservations'][0]
                    with Session(engine) as db:
                        r = db.get(Reservation, rid)
                        payload = dict(performance_id=r.performance_id, performance_date=str(r.performance_date),
                                       session_time=r.session_time, seat_grade=r.seat_grade,
                                       quantity=r.quantity, request_key=r.request_key)
                    replay = await api.call('POST', '/reservations', token=account['token'], payload=payload)
                    self.assertEqual(replay['id'], rid)
                    await api.call('POST', '/reservations', token=account['token'],
                                   payload=dict(payload, quantity=2), expected=(409,))
                    cancelled = await api.call('POST', f'/reservations/{rid}/cancel', token=account['token'], total=3)
                    self.assertEqual(cancelled['payment_status'], 'CANCELLED')
                    detail = await api.call('GET', '/performances/city')
                    events = campaign.events(account, detail, ['performance_view'])
                    for _ in range(2):
                        await api.call('POST', '/tracking/events', token=account['token'],
                                       payload={'events': events}, total=1, tracking=1, expected=(202,))
                    self.assertEqual(campaign.budget.used(), (20, 7))
                    # Favorite add/remove creates one row even though its final
                    # resident count is zero; search and tracking must also work.
                    await campaign.visit(account, 13, 'mixed')
                    self.assertEqual(len(campaign.state['favorite_removals']), 1)
                    # Cover cancellation both before and after a mock payment.
                    await campaign.visit(account, 78, 'mixed', 'city')
                    await campaign.visit(account, 79, 'mixed', 'city')
                    # A preexisting favorite is never removed by this workload.
                    with Session(engine) as db:
                        db.add(Favorite(user_id=signed['user']['id'], performance_id='baseball'))
                        db.commit()
                    account['favorites'].add('baseball')
                    await campaign.visit(account, 15, 'mixed', 'baseball')
                    self.assertEqual(len(campaign.state['favorite_removals']), 1)
                with Session(engine) as db:
                    total = sum(db.scalar(select(func.count()).select_from(model))
                                for model in (User, Reservation, Payment, StatusHistory, Event, Favorite))
                    self.assertEqual(db.scalar(select(func.count()).select_from(Reservation)), 3)
                    self.assertTrue(all(r.status == 'CANCELLED' for r in db.scalars(select(Reservation))))
                    self.assertIsNotNone(db.get(Favorite, (signed['user']['id'], 'baseball')))
                expected_total = total - 1 + len(mongo.docs) + len(campaign.state['favorite_removals'])
                self.assertEqual(campaign.budget.used(), (expected_total, len(mongo.docs)))
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(previous)
            engine.dispose()
