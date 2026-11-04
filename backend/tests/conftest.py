import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET", "test-secret-that-is-long-enough-for-hs256")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.base import Base
from app.db.seed import seed
from app.db.session import get_db
from app.main import app


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with Session() as s:
        seed(s)
    yield Session
    engine.dispose()


@pytest.fixture()
def client(db_session):
    def override():
        with db_session() as s:
            yield s

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


SIGNUP = {
    "name": "티킷유저",
    "email": "User@Example.com",
    "password": "password123",
    "password_confirm": "password123",
    "mbti": "ENFP",
    "consent": True,
}


@pytest.fixture()
def auth(client):
    r = client.post("/api/v1/auth/signup", json=SIGNUP)
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
