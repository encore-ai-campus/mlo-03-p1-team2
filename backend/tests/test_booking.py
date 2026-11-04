API = "/api/v1"

ORDER = {
    "performance_id": "opera",
    "performance_date": "2026-11-12",
    "session_time": "19:30",
    "seat_grade": "PREMIUM",
    "quantity": 2,
    "payment_method": "신용카드",
}


def test_list_filter_sort_and_detail(client):
    all_ = client.get(f"{API}/performances").json()
    assert len(all_) == 8
    musicals = client.get(f"{API}/performances", params={"category": "뮤지컬"}).json()
    assert {p["id"] for p in musicals} == {"opera", "dance"}
    by_price = client.get(f"{API}/performances", params={"sort": "price"}).json()
    assert [p["price"] for p in by_price] == sorted(p["price"] for p in by_price)
    found = client.get(f"{API}/performances", params={"q": "재즈"}).json()
    assert [p["id"] for p in found] == ["jazz"]
    detail = client.get(f"{API}/performances/city").json()
    assert detail["available_dates"] == ["2026-11-21", "2026-11-22"]
    assert client.get(f"{API}/performances/nope").status_code == 404


def test_order_requires_auth(client):
    assert client.post(f"{API}/orders", json=ORDER).status_code == 401


def test_order_price_computed_server_side(client, auth):
    tampered = {**ORDER, "unit_price": 1, "amount": 1}
    r = client.post(f"{API}/orders", json=tampered, headers=auth)
    assert r.status_code == 201, r.text
    o = r.json()
    assert o["unit_price"] == 80000 + 30000
    assert o["amount"] == 110000 * 2
    assert o["status"] == "MOCK_PAID" and o["is_mock"] is True
    assert o["performance_title"] == "뮤지컬 〈오페라의 유령〉"
    assert [x["id"] for x in client.get(f"{API}/orders", headers=auth).json()] == [o["id"]]


def test_order_validation(client, auth):
    cases = [
        {"performance_date": "2026-12-25"},  # outside available dates
        {"session_time": "09:00"},  # not a listed slot
        {"quantity": 5},
        {"quantity": 0},
        {"seat_grade": "VIP"},
        {"payment_method": "bitcoin"},
    ]
    for override in cases:
        r = client.post(f"{API}/orders", json={**ORDER, **override}, headers=auth)
        assert r.status_code == 422, override
    r = client.post(f"{API}/orders", json={**ORDER, "performance_id": "nope"}, headers=auth)
    assert r.status_code == 404


def test_favorites(client, auth):
    assert client.put(f"{API}/favorites/jazz", headers=auth).status_code == 204
    assert client.put(f"{API}/favorites/jazz", headers=auth).status_code == 204  # idempotent
    assert client.put(f"{API}/favorites/nope", headers=auth).status_code == 404
    assert client.get(f"{API}/favorites", headers=auth).json() == ["jazz"]
    assert client.delete(f"{API}/favorites/jazz", headers=auth).status_code == 204
    assert client.get(f"{API}/favorites", headers=auth).json() == []


def test_events_and_ranking(client, auth):
    assert client.post(f"{API}/events", json={"performance_id": "color"}).status_code == 201
    assert client.post(f"{API}/events", json={"performance_id": "color"}, headers=auth).status_code == 201
    client.post(f"{API}/orders", json=ORDER, headers=auth)
    ranking = client.get(f"{API}/performances/ranking").json()
    assert ranking[0]["id"] == "opera" and ranking[0]["purchases"] == 1
    assert ranking[1]["id"] == "color" and ranking[1]["views"] == 2
    popular = client.get(f"{API}/performances").json()
    assert popular[0]["id"] == "opera"


def test_export_and_delete_account(client, auth, db_session):
    client.post(f"{API}/orders", json=ORDER, headers=auth)
    client.put(f"{API}/favorites/city", headers=auth)
    export = client.get(f"{API}/users/me/export", headers=auth).json()
    assert len(export["orders"]) == 1 and export["favorites"] == ["city"]
    assert "password_hash" not in export["profile"]

    assert client.delete(f"{API}/users/me", headers=auth).status_code == 204
    assert client.get(f"{API}/users/me", headers=auth).status_code == 401

    from app.models import Event, Favorite, Order, User

    with db_session() as s:
        assert s.query(User).count() == 0
        assert s.query(Order).count() == 0
        assert s.query(Favorite).count() == 0
        assert s.query(Event).filter(Event.user_id.isnot(None)).count() == 0
