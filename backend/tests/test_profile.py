from tests.conftest import SIGNUP

API = "/api/v1"


def login(client, email, password):
    return client.post(f"{API}/auth/login", json={"email": email, "password": password})


def test_update_requires_login(client):
    assert client.patch(f"{API}/users/me", json={"name": "x"}).status_code == 401
    assert client.put(f"{API}/users/me/password", json={}).status_code == 401


def test_update_name_and_mbti(client, auth):
    r = client.patch(f"{API}/users/me", json={"name": "  새이름 ", "mbti": "INTJ"}, headers=auth)
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "새이름"
    assert r.json()["mbti"] == "INTJ"
    assert r.json()["email"] == "user@example.com"  # untouched
    assert client.get(f"{API}/users/me", headers=auth).json()["mbti"] == "INTJ"


def test_update_rejects_blank_name_and_bad_mbti(client, auth):
    assert client.patch(f"{API}/users/me", json={"name": "   "}, headers=auth).status_code == 422
    assert client.patch(f"{API}/users/me", json={"mbti": "XXXX"}, headers=auth).status_code == 422


def test_email_change_requires_current_password(client, auth):
    no_pw = client.patch(f"{API}/users/me", json={"email": "new@example.com"}, headers=auth)
    assert no_pw.status_code == 403
    wrong = client.patch(f"{API}/users/me", json={"email": "new@example.com", "current_password": "wrongpass1"},
                         headers=auth)
    assert wrong.status_code == 403
    ok = client.patch(f"{API}/users/me", json={"email": "New@Example.com", "current_password": "password123"},
                      headers=auth)
    assert ok.status_code == 200
    assert ok.json()["email"] == "new@example.com"
    assert login(client, "new@example.com", "password123").status_code == 200
    assert login(client, "user@example.com", "password123").status_code == 401


def test_same_email_needs_no_password(client, auth):
    r = client.patch(f"{API}/users/me", json={"email": "user@example.com", "name": "a"}, headers=auth)
    assert r.status_code == 200


def test_email_change_to_taken_email_conflicts(client, auth):
    client.post(f"{API}/auth/signup", json={**SIGNUP, "email": "other@example.com"})
    r = client.patch(f"{API}/users/me", json={"email": "other@example.com", "current_password": "password123"},
                     headers=auth)
    assert r.status_code == 409


def test_change_password(client, auth):
    url = f"{API}/users/me/password"
    wrong = client.put(url, json={"current_password": "wrongpass1", "new_password": "newpass1234",
                                  "new_password_confirm": "newpass1234"}, headers=auth)
    assert wrong.status_code == 403
    mismatch = client.put(url, json={"current_password": "password123", "new_password": "newpass1234",
                                     "new_password_confirm": "different12"}, headers=auth)
    assert mismatch.status_code == 422
    assert "newpass1234" not in mismatch.text
    same = client.put(url, json={"current_password": "password123", "new_password": "password123",
                                 "new_password_confirm": "password123"}, headers=auth)
    assert same.status_code == 400
    ok = client.put(url, json={"current_password": "password123", "new_password": "newpass1234",
                               "new_password_confirm": "newpass1234"}, headers=auth)
    assert ok.status_code == 204
    assert login(client, "user@example.com", "newpass1234").status_code == 200
    assert login(client, "user@example.com", "password123").status_code == 401
