import uuid

import pytest
from pymongo.errors import BulkWriteError, ServerSelectionTimeoutError

from app.db.mongo import get_event_collection
from app.main import app

API = "/api/v1/tracking/events"


class FakeCollection:
    """insert_many(ordered=False) 동작만 흉내 낸 MongoDB 컬렉션 (_id 중복은 건너뜀)."""

    def __init__(self, fail: Exception | None = None):
        self.docs: dict[str, dict] = {}
        self.fail = fail

    def insert_many(self, docs, ordered=True):
        if self.fail:
            raise self.fail
        errors = []
        for i, doc in enumerate(docs):
            if doc["_id"] in self.docs:
                errors.append({"index": i, "code": 11000, "errmsg": "duplicate key"})
            else:
                self.docs[doc["_id"]] = doc
        if errors:
            raise BulkWriteError({"writeErrors": errors, "nInserted": len(docs) - len(errors)})


@pytest.fixture()
def events(client):
    fake = FakeCollection()
    app.dependency_overrides[get_event_collection] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_event_collection, None)


def make_event(**overrides):
    event = {
        "event_id": str(uuid.uuid4()),
        "type": "performance_view",
        "occurred_at": "2026-11-04T05:29:44.172Z",
        "session_id": str(uuid.uuid4()),
        "anonymous_id": str(uuid.uuid4()),
        "page": {"path": "/", "referrer": ""},
        "props": {"performance_id": "opera", "category": "뮤지컬", "price_krw": 80000},
        "schema_version": 1,
    }
    event.update(overrides)
    return event


def test_batch_is_stored_with_server_fields(client, events):
    batch = [make_event(), make_event(type="search", props={"query": "재즈", "result_count": 1})]
    r = client.post(API, json={"events": batch}, headers={"User-Agent": "pytest-agent"})
    assert r.status_code == 202, r.text
    assert r.json() == {"accepted": 2, "duplicates": 0}

    doc = events.docs[batch[0]["event_id"]]
    assert doc["event_id"] == batch[0]["event_id"]
    assert doc["type"] == "performance_view"
    assert doc["page"] == {"path": "/", "referrer": ""}
    assert doc["props"]["price_krw"] == 80000
    assert doc["occurred_at"].year == 2026
    assert doc["user_id"] is None
    assert doc["user_agent"] == "pytest-agent"
    assert "received_at" in doc


def test_logged_in_user_id_comes_from_token(client, events, auth):
    me = client.get("/api/v1/users/me", headers=auth).json()
    event = make_event(type="login", props={})
    assert client.post(API, json={"events": [event]}, headers=auth).status_code == 202
    assert events.docs[event["event_id"]]["user_id"] == me["id"]


def test_invalid_token_is_ignored_instead_of_losing_events(client, events):
    event = make_event()
    r = client.post(API, json={"events": [event]}, headers={"Authorization": "Bearer expired-or-garbage"})
    assert r.status_code == 202
    assert events.docs[event["event_id"]]["user_id"] is None


def test_resent_events_are_counted_as_duplicates(client, events):
    event = make_event()
    client.post(API, json={"events": [event]})
    r = client.post(API, json={"events": [event, make_event()]})
    assert r.status_code == 202
    assert r.json() == {"accepted": 1, "duplicates": 1}
    assert len(events.docs) == 2


@pytest.mark.parametrize("body", [
    {"events": []},
    {"events": [make_event() for _ in range(11)]},
    {"events": [make_event(type="hack_the_planet")]},
    {"events": [make_event(event_id="not-a-uuid")]},
    {"events": [make_event(props={f"k{i}": i for i in range(21)})]},
    {"events": [make_event(props={"nested": {"a": 1}})]},
    {"events": [make_event(props={"long": "x" * 501})]},
    {"events": [make_event(page={"path": "x" * 501, "referrer": ""})]},
])
def test_invalid_batches_are_rejected(client, events, body):
    assert client.post(API, json=body).status_code == 422
    assert events.docs == {}


def test_storage_outage_returns_503_so_client_can_retry(client):
    app.dependency_overrides[get_event_collection] = lambda: FakeCollection(fail=ServerSelectionTimeoutError("down"))
    try:
        r = client.post(API, json={"events": [make_event()]})
    finally:
        app.dependency_overrides.pop(get_event_collection, None)
    assert r.status_code == 503
