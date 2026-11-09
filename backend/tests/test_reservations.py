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


def test_request_key_race_returns_existing(client, auth, db_session, monkeypatch):
    """다른 요청이 키 조회와 INSERT 사이에 먼저 저장한 경우: 500이 아니라 기존 예매(200) 또는 409"""
    from app.api.routes import reservations as routes
    from app.models import StatusHistory

    body = payload()
    first = client.post(f"{API}/reservations", json=body, headers=auth)
    assert first.status_code == 201

    real_find = routes._find_by_key
    calls = []

    def find_misses_once(db, user_id, key):
        calls.append(key)
        return None if len(calls) == 1 else real_find(db, user_id, key)

    monkeypatch.setattr(routes, "_find_by_key", find_misses_once)
    again = client.post(f"{API}/reservations", json=body, headers=auth)
    assert again.status_code == 200, again.text
    assert again.json()["id"] == first.json()["id"]

    calls.clear()
    changed = client.post(f"{API}/reservations", json={**body, "quantity": 1}, headers=auth)
    assert changed.status_code == 409

    assert len(client.get(f"{API}/reservations", headers=auth).json()) == 1
    with db_session() as s:
        assert s.query(StatusHistory).filter_by(reservation_id=first.json()["id"]).count() == 2


def test_request_key_concurrent_requests(tmp_path):
    """같은 키로 8건을 실제 동시에 보내도 예매는 1건, 응답은 201 1건 + 200 7건"""
    import threading

    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.db.base import Base
    from app.db.seed import seed
    from app.db.session import get_db
    from app.main import app
    from app.models import Reservation

    engine = create_engine(f"sqlite:///{tmp_path / 'race.db'}", connect_args={"check_same_thread": False, "timeout": 30})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with Session() as s:
        seed(s)

    def override():
        with Session() as s:
            yield s

    app.dependency_overrides[get_db] = override
    try:
        with TestClient(app) as c:
            r = c.post(f"{API}/auth/signup", json=SIGNUP)
            headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
        body = payload()
        n = 8
        barrier = threading.Barrier(n)
        codes = [None] * n

        def send(i):
            with TestClient(app, raise_server_exceptions=False) as c:
                barrier.wait()
                resp = c.post(f"{API}/reservations", json=body, headers=headers)
                codes[i] = (resp.status_code, resp.json().get("id") if resp.status_code < 300 else None)

        threads = [threading.Thread(target=send, args=(i,)) for i in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    finally:
        app.dependency_overrides.clear()

    statuses = sorted(code for code, _ in codes)
    assert statuses == [200] * (n - 1) + [201], codes
    assert len({rid for _, rid in codes}) == 1
    with Session() as s:
        assert s.query(Reservation).count() == 1
    engine.dispose()


class _InjectDbError:
    """지정한 SQL이 실행될 때 MariaDB 오류(기본 1213 데드락)를 times번 일으킵니다."""

    def __init__(self, engine, sql_prefix, times, errno=1213):
        import pymysql
        from sqlalchemy import event
        from sqlalchemy.exc import OperationalError

        self.hits = 0

        def before(conn, cursor, statement, params, context, executemany):
            if statement.lstrip().upper().startswith(sql_prefix) and self.hits < times:
                self.hits += 1
                orig = pymysql.err.OperationalError(errno, "Deadlock found when trying to get lock; "
                                                           "try restarting transaction")
                raise OperationalError(statement, params, orig)

        self._remove = lambda: event.remove(engine, "before_cursor_execute", before)
        event.listen(engine, "before_cursor_execute", before)

    def close(self):
        self._remove()


def _engine(db_session):
    return db_session.kw["bind"]


def test_create_retries_after_deadlock(client, auth, db_session, monkeypatch):
    from app.api.routes import reservations as routes
    from app.models import Event, Reservation, StatusHistory

    monkeypatch.setattr(routes.time, "sleep", lambda s: None)
    fault = _InjectDbError(_engine(db_session), "INSERT INTO STATUS_HISTORY", times=2)
    try:
        r = client.post(f"{API}/reservations", json=payload(), headers=auth)
    finally:
        fault.close()
    assert r.status_code == 201, r.text
    assert fault.hits == 2  # 두 번 데드락, 세 번째 시도에 성공
    with db_session() as s:
        assert s.query(Reservation).count() == 1  # 실패한 시도의 행은 롤백되어 남지 않음
        assert s.query(StatusHistory).count() == 2
        assert s.query(Event).filter_by(type="reservation_requested").count() == 1


def test_change_retries_after_deadlock(client, auth, db_session, monkeypatch):
    from app.api.routes import reservations as routes
    from app.models import StatusHistory

    monkeypatch.setattr(routes.time, "sleep", lambda s: None)
    order = create(client, auth)
    fault = _InjectDbError(_engine(db_session), "UPDATE RESERVATIONS", times=1)
    try:
        r = act(client, auth, order, "complete")
    finally:
        fault.close()
    assert r.status_code == 200, r.text
    assert fault.hits == 1
    assert (r.json()["status"], r.json()["payment_status"]) == ("CONFIRMED", "COMPLETED")
    with db_session() as s:
        assert s.query(StatusHistory).filter_by(reservation_id=order["id"]).count() == 4  # 생성 2 + 결제 2


def test_retry_gives_up_and_does_not_retry_other_errors(auth, db_session, monkeypatch):
    from fastapi.testclient import TestClient

    from app.api.routes import reservations as routes
    from app.main import app
    from app.models import Reservation

    monkeypatch.setattr(routes.time, "sleep", lambda s: None)
    with TestClient(app, raise_server_exceptions=False) as c:
        # 데드락이 계속되면 MAX_ATTEMPTS번 시도한 뒤 500
        fault = _InjectDbError(_engine(db_session), "INSERT INTO RESERVATIONS", times=99)
        try:
            assert c.post(f"{API}/reservations", json=payload(), headers=auth).status_code == 500
        finally:
            fault.close()
        assert fault.hits == routes.MAX_ATTEMPTS

        # 재시도 대상이 아닌 오류(2013 연결 끊김)는 한 번만 시도
        fault = _InjectDbError(_engine(db_session), "INSERT INTO RESERVATIONS", times=99, errno=2013)
        try:
            assert c.post(f"{API}/reservations", json=payload(), headers=auth).status_code == 500
        finally:
            fault.close()
        assert fault.hits == 1
    with db_session() as s:
        assert s.query(Reservation).count() == 0


def test_transaction_is_closed_before_response_on_every_exit(client, auth, db_session):
    """변경 없이 끝나거나 409/404로 끝나도 FOR UPDATE 트랜잭션을 응답 전에 닫아야 합니다.

    열린 채로 남으면 잠금이 응답 후 get_db의 close까지 유지되고, 그때 난 데드락은 재시도 범위 밖에서
    'Exception in ASGI application'이 됩니다(2026-11-08 반복 부하 테스트에서 실제 발생).
    """
    from app.db.session import get_db
    from app.main import app

    open_at_teardown = []

    def recording_db():
        with db_session() as s:
            try:
                yield s
            finally:   # 409/404는 HTTPException이 여기까지 전파됩니다
                open_at_teardown.append(s.in_transaction())

    app.dependency_overrides[get_db] = recording_db
    body = payload()
    order = client.post(f"{API}/reservations", json=body, headers=auth).json()
    cancelled = create(client, auth)
    assert act(client, auth, cancelled, "cancel").status_code == 200
    open_at_teardown.clear()

    cases = [
        ("same request_key replay", lambda: client.post(f"{API}/reservations", json=body, headers=auth), 200),
        ("request_key reused with other body",
         lambda: client.post(f"{API}/reservations", json={**body, "quantity": 1}, headers=auth), 409),
        ("complete", lambda: act(client, auth, order, "complete"), 200),
        ("complete again (unchanged)", lambda: act(client, auth, order, "complete"), 200),
        ("complete a cancelled order", lambda: act(client, auth, cancelled, "complete"), 409),
        ("unknown reservation", lambda: act(client, auth, {"id": str(uuid.uuid4())}, "cancel"), 404),
    ]
    for name, call, expected in cases:
        open_at_teardown.clear()
        assert call().status_code == expected, name
        assert open_at_teardown == [False], name


def test_deadlock_when_closing_unchanged_transaction_is_retried(client, auth, db_session, monkeypatch):
    """변경 없는 경로의 트랜잭션 종료(commit)에서 난 데드락도 재시도되어 정상 응답이 나가야 합니다."""
    import pymysql
    from sqlalchemy.exc import OperationalError
    from sqlalchemy.orm import Session

    from app.api.routes import reservations as routes
    from app.models import StatusHistory

    monkeypatch.setattr(routes.time, "sleep", lambda s: None)
    order = create(client, auth)
    assert act(client, auth, order, "complete").status_code == 200

    real_commit, calls = Session.commit, []

    def flaky_commit(self):
        calls.append(1)
        if len(calls) == 1:
            raise OperationalError("COMMIT", {}, pymysql.err.OperationalError(1213, "Deadlock found"))
        return real_commit(self)

    monkeypatch.setattr(Session, "commit", flaky_commit)
    r = act(client, auth, order, "complete")   # 이미 결제 완료: 변경 없이 commit만 합니다
    monkeypatch.setattr(Session, "commit", real_commit)

    assert r.status_code == 200, r.text
    assert (r.json()["status"], r.json()["payment_status"]) == ("CONFIRMED", "COMPLETED")
    assert len(calls) == 2   # 첫 commit 데드락 → 재시도 후 성공
    with db_session() as s:
        assert s.query(StatusHistory).filter_by(reservation_id=order["id"]).count() == 4  # 이력 중복 없음


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
