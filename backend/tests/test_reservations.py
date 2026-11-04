"""예매 → 결제 → 취소 흐름 (booking-app의 API 테스트를 FastAPI로 옮김)"""
import uuid

from tests.conftest import SIGNUP

API = "/api/v1"


def payload(**changes):
    return {
        "performance_id": "city", "performance_date": "2026-11-21", "session_time": "18:00",
        "seat_grade": "PREMIUM", "quantity": 2, "request_key": str(uuid.uuid4()), **changes,
    }


def create(client, auth, **changes):
    r = client.post(f"{API}/reservations", json=payload(**changes), headers=auth)
    assert r.status_code == 201, r.text
    return r.json()


def act(client, auth, order, action):
    return client.post(f"{API}/reservations/{order['id']}/{action}", headers=auth)


def other_user(client):
    body = {**SIGNUP, "email": f"{uuid.uuid4()}@example.com", "name": "다른 관객"}
    r = client.post(f"{API}/auth/signup", json=body)
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_request_complete_cancel_preserves_times_and_history(client, auth, db_session):
    order = create(client, auth, amount=1, user_id="forged", status="CONFIRMED")
    assert (order["status"], order["payment_status"]) == ("REQUESTED", "PENDING")
    assert order["amount"] == (99000 + 30000) * 2
    assert order["completed_at"] is None and order["requested_at"]

    r = act(client, auth, order, "complete")
    assert r.status_code == 200
    paid = r.json()
    assert (paid["status"], paid["payment_status"]) == ("CONFIRMED", "COMPLETED")
    assert paid["completed_at"]
    assert act(client, auth, order, "complete").json()["completed_at"] == paid["completed_at"]  # 재시도

    cancelled = act(client, auth, order, "cancel").json()
    assert (cancelled["status"], cancelled["payment_status"]) == ("CANCELLED", "CANCELLED")
    assert cancelled["cancelled_at"] == cancelled["payment_cancelled_at"]
    assert cancelled["completed_at"] == paid["completed_at"]  # 결제 완료 시각 보존
    assert cancelled["amount"] == order["amount"]  # 금액 보존
    assert act(client, auth, order, "cancel").json()["cancelled_at"] == cancelled["cancelled_at"]
    r = act(client, auth, order, "complete")
    assert r.status_code == 409

    from app.models import Event, StatusHistory

    with db_session() as s:
        assert s.query(StatusHistory).filter_by(reservation_id=order["id"]).count() == 6
        kinds = [e.type for e in s.query(Event).filter_by(reservation_id=order["id"]).order_by(Event.created_at)]
    assert kinds == ["reservation_requested", "payment_completed", "reservation_cancelled"]


def test_cancel_pending(client, auth):
    order = create(client, auth)
    r = act(client, auth, order, "cancel")
    assert r.status_code == 200
    assert r.json()["payment_status"] == "CANCELLED"
    assert r.json()["completed_at"] is None


def test_request_key_is_idempotent(client, auth):
    body = payload()
    first = client.post(f"{API}/reservations", json=body, headers=auth)
    again = client.post(f"{API}/reservations", json=body, headers=auth)
    assert (first.status_code, again.status_code) == (201, 200)
    assert first.json()["id"] == again.json()["id"]
    changed = client.post(f"{API}/reservations", json={**body, "quantity": 1}, headers=auth)
    assert changed.status_code == 409
    assert len(client.get(f"{API}/reservations", headers=auth).json()) == 1


def test_owner_isolation_and_authentication(client, auth):
    order = create(client, auth)
    assert client.get(f"{API}/reservations").status_code == 401
    assert client.post(f"{API}/reservations/{order['id']}/cancel").status_code == 401
    stranger = other_user(client)
    assert client.get(f"{API}/reservations", headers=stranger).json() == []
    assert client.get(f"{API}/payments", headers=stranger).json() == []
    for action in ("cancel", "complete"):
        assert act(client, stranger, order, action).status_code == 404
    assert act(client, auth, {"id": "nope"}, "complete").status_code == 404
    assert client.post(f"{API}/reservations/{order['id']}/refund", headers=auth).status_code == 422


def test_validation(client, auth):
    cases = [
        {"performance_date": "2026-12-25"},
        {"session_time": "09:00"},
        {"quantity": 5},
        {"quantity": 0},
        {"seat_grade": "VIP"},
        {"request_key": "not-a-uuid"},
    ]
    for override in cases:
        r = client.post(f"{API}/reservations", json=payload(**override), headers=auth)
        assert r.status_code == 422, override
    r = client.post(f"{API}/reservations", json=payload(performance_id="nope"), headers=auth)
    assert r.status_code == 404


def test_payments_list_and_ranking(client, auth):
    order = create(client, auth, performance_id="jazz", performance_date="2026-11-14", session_time="20:00")
    payments = client.get(f"{API}/payments", headers=auth).json()
    assert payments[0]["reservation_id"] == order["id"]
    assert payments[0]["status"] == "PENDING" and payments[0]["amount"] == order["amount"]
    act(client, auth, order, "complete")
    ranking = client.get(f"{API}/performances/ranking").json()
    assert ranking[0]["id"] == "jazz" and ranking[0]["purchases"] == 1


def test_booking_started_event(client, auth):
    r = client.post(f"{API}/events", json={"performance_id": "city", "type": "booking_started"}, headers=auth)
    assert r.status_code == 201
    assert client.post(f"{API}/events", json={"performance_id": "city", "type": "payment_completed"}).status_code == 422


def test_export_and_delete_include_reservations(client, auth, db_session):
    order = create(client, auth)
    act(client, auth, order, "complete")
    export = client.get(f"{API}/users/me/export", headers=auth).json()
    assert [r["id"] for r in export["reservations"]] == [order["id"]]
    assert client.delete(f"{API}/users/me", headers=auth).status_code == 204

    from app.models import Payment, Reservation, StatusHistory

    with db_session() as s:
        assert s.query(Reservation).count() == 0
        assert s.query(Payment).count() == 0
        assert s.query(StatusHistory).count() == 0
