from tests.conftest import SIGNUP

API = "/api/v1"


def test_signup_returns_token_and_normalized_email(client):
    r = client.post(f"{API}/auth/signup", json=SIGNUP)
    assert r.status_code == 201
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "user@example.com"
    assert "password_hash" not in body["user"]


def test_duplicate_email_conflict(client, auth):
    r = client.post(f"{API}/auth/signup", json={**SIGNUP, "email": "USER@example.com"})
    assert r.status_code == 409


def test_password_mismatch_rejected(client):
    r = client.post(f"{API}/auth/signup", json={**SIGNUP, "password_confirm": "different123"})
    assert r.status_code == 422
    assert "비밀번호가 일치하지 않습니다." in r.json()["detail"][0]["msg"]
    assert "password123" not in r.text  # request input (password) must not be echoed back


def test_missing_consent_rejected(client):
    r = client.post(f"{API}/auth/signup", json={**SIGNUP, "consent": False})
    assert r.status_code == 422


def test_invalid_mbti_and_short_password_rejected(client):
    assert client.post(f"{API}/auth/signup", json={**SIGNUP, "mbti": "XXXX"}).status_code == 422
    short = {**SIGNUP, "password": "short", "password_confirm": "short"}
    assert client.post(f"{API}/auth/signup", json=short).status_code == 422


def test_login_success_and_failure(client, auth):
    ok = client.post(f"{API}/auth/login", json={"email": "user@example.com", "password": "password123"})
    assert ok.status_code == 200
    bad = client.post(f"{API}/auth/login", json={"email": "user@example.com", "password": "wrongpass1"})
    assert bad.status_code == 401
    unknown = client.post(f"{API}/auth/login", json={"email": "nobody@example.com", "password": "password123"})
    assert unknown.status_code == 401
    assert bad.json()["detail"] == unknown.json()["detail"]


def test_me_requires_valid_token(client, auth):
    assert client.get(f"{API}/users/me").status_code == 401
    assert client.get(f"{API}/users/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
    r = client.get(f"{API}/users/me", headers=auth)
    assert r.status_code == 200
    assert r.json()["mbti"] == "ENFP"
