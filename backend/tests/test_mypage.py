from datetime import datetime, timedelta, timezone

from app.models import Performance
from tests.test_reservations import act, create, other_user

API = "/api/v1/users/me"


def test_mypage_requires_auth(client):
    for path in ("taste-report", "notification-settings", "notifications"):
        assert client.get(f"{API}/{path}").status_code == 401
    assert client.put(f"{API}/notification-settings", json={}).status_code == 401


def test_empty_report(client, auth):
    r = client.get(f"{API}/taste-report", headers=auth)
    assert r.status_code == 200, r.text
    report = r.json()
    assert report["mbti"] == "ENFP"
    assert report["totals"] == {"views": 0, "favorites": 0, "bookings": 0}
    assert report["peer_users"] == 0
    assert all(c["peer_favorites"] == 0 for c in report["categories"])


def test_report_uses_real_records_and_excludes_cancelled_bookings(client, auth):
    peer = other_user(client)
    client.put("/api/v1/favorites/jazz", headers=auth)
    client.put("/api/v1/favorites/color", headers=peer)
    client.post("/api/v1/events", json={"performance_id": "jazz"}, headers=auth)
    client.post("/api/v1/events", json={"performance_id": "color"}, headers=peer)
    paid = create(client, auth)
    act(client, auth, paid, "complete")
    cancelled = create(client, auth)
    act(client, auth, cancelled, "complete")
    act(client, auth, cancelled, "cancel")
    create(client, auth)  # unpaid
    report = client.get(f"{API}/taste-report", headers=auth).json()
    assert report["totals"] == {"views": 1, "favorites": 1, "bookings": 1}
    categories = {c["category"]: c for c in report["categories"]}
    assert categories["콘서트"]["views"] == 1
    assert categories["콘서트"]["favorites"] == 1
    assert categories["콘서트"]["bookings"] == 1
    assert categories["전시"]["views"] == 0
    assert categories["전시"]["peer_favorites"] == 1
    assert report["peer_users"] == 1
    client.patch(API, json={"mbti": "INTJ"}, headers=peer)
    report = client.get(f"{API}/taste-report", headers=auth).json()
    assert report["peer_users"] == 0
    assert all(c["peer_favorites"] == 0 for c in report["categories"])


def test_settings_persist_are_isolated_and_are_deleted_with_account(client, auth, db_session):
    peer = other_user(client)
    url = f"{API}/notification-settings"
    assert client.get(url, headers=auth).json() == {"booking_reminders": False, "favorite_updates": False}
    saved = client.put(url, json={"booking_reminders": True, "favorite_updates": False}, headers=auth)
    assert saved.status_code == 200, saved.text
    assert client.get(url, headers=auth).json()["booking_reminders"] is True
    assert client.get(url, headers=peer).json()["booking_reminders"] is False
    assert client.put(url, json={"booking_reminders": None, "favorite_updates": True}, headers=auth).status_code == 422
    assert client.delete(API, headers=auth).status_code == 204
    from app.models.notification import NotificationSettings
    with db_session() as db:
        assert db.query(NotificationSettings).count() == 0


def test_notifications_respect_settings_owner_status_and_dates(client, auth, db_session):
    peer = other_user(client)
    client.put("/api/v1/favorites/color", headers=auth)
    confirmed = create(client, auth)
    act(client, auth, confirmed, "complete")
    cancelled = create(client, auth)
    act(client, auth, cancelled, "cancel")
    create(client, auth)
    foreign = create(client, peer)
    act(client, peer, foreign, "complete")
    from app.models import Reservation
    tomorrow = (datetime.now(timezone(timedelta(hours=9))) + timedelta(days=1)).date()
    with db_session() as db:
        for row in db.query(Reservation).all():
            row.performance_date = tomorrow
        show = db.get(Performance, "color")
        show.start_date = tomorrow
        show.days = 2
        db.commit()
    assert client.get(f"{API}/notifications", headers=auth).json() == []
    client.put(f"{API}/notification-settings", json={"booking_reminders": True, "favorite_updates": True}, headers=auth)
    items = client.get(f"{API}/notifications", headers=auth).json()
    assert len(items) == 2
    assert {i["kind"] for i in items} == {"booking", "favorite"}
    assert [i["reservation_id"] for i in items if i["kind"] == "booking"] == [confirmed["id"]]
    with db_session() as db:
        db.get(Reservation, confirmed["id"]).performance_date = tomorrow - timedelta(days=2)
        db.get(Performance, "color").start_date = tomorrow - timedelta(days=10)
        db.commit()
    assert client.get(f"{API}/notifications", headers=auth).json() == []
