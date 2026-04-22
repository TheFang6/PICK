import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.pairing_token import PairingToken
from app.models.user import User
from app.models.web_session import WebSession
from app.services import pairing_repo, web_session_repo

TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)

Base.metadata.create_all(bind=TEST_ENGINE)


@pytest.fixture
def db():
    connection = TEST_ENGINE.connect()
    transaction = connection.begin()
    session = TestSession(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db):
    user = User(id=uuid.uuid4(), telegram_id="999888777", name="Test User")
    db.add(user)
    db.flush()
    return user


# --- Pairing endpoint ---

class TestPairEndpoint:
    def test_pair_valid_token(self, client, db, test_user):
        token = pairing_repo.create_token(db, test_user.id)
        res = client.post("/pair", json={"token": token.token})
        assert res.status_code == 200
        data = res.json()
        assert data["user_id"] == str(test_user.id)
        assert data["name"] == "Test User"
        assert "session_id" in res.cookies

    def test_pair_invalid_token(self, client):
        res = client.post("/pair", json={"token": "nonexistent"})
        assert res.status_code == 400
        assert "Invalid or expired" in res.json()["detail"]

    def test_pair_expired_token(self, client, db, test_user):
        token = PairingToken(
            id=uuid.uuid4(),
            token=uuid.uuid4().hex,
            user_id=test_user.id,
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
        db.add(token)
        db.flush()
        res = client.post("/pair", json={"token": token.token})
        assert res.status_code == 400

    def test_pair_consumed_token(self, client, db, test_user):
        token = pairing_repo.create_token(db, test_user.id)
        pairing_repo.consume_token(db, token)
        res = client.post("/pair", json={"token": token.token})
        assert res.status_code == 400

    def test_pair_sets_httponly_cookie(self, client, db, test_user):
        token = pairing_repo.create_token(db, test_user.id)
        res = client.post("/pair", json={"token": token.token})
        cookie_header = res.headers.get("set-cookie", "")
        assert "httponly" in cookie_header.lower()
        assert "samesite=lax" in cookie_header.lower()


# --- Session management ---

class TestSessionManagement:
    def test_get_me_with_valid_session(self, client, db, test_user):
        session = web_session_repo.create_session(db, test_user.id)
        client.cookies.set("session_id", session.session_token)
        res = client.get("/me")
        assert res.status_code == 200
        assert res.json()["name"] == "Test User"

    def test_get_me_without_session(self, client):
        res = client.get("/me")
        assert res.status_code == 401

    def test_get_me_with_expired_session(self, client, db, test_user):
        session = WebSession(
            user_id=test_user.id,
            session_token=uuid.uuid4().hex,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        db.add(session)
        db.flush()
        client.cookies.set("session_id", session.session_token)
        res = client.get("/me")
        assert res.status_code == 401

    def test_logout(self, client, db, test_user):
        session = web_session_repo.create_session(db, test_user.id)
        client.cookies.set("session_id", session.session_token)
        res = client.post("/logout")
        assert res.status_code == 200
        assert web_session_repo.get_valid_session(db, session.session_token) is None

    def test_logout_without_session(self, client):
        res = client.post("/logout")
        assert res.status_code == 200


# --- Web session repo ---

class TestWebSessionRepo:
    def test_create_session(self, db, test_user):
        session = web_session_repo.create_session(db, test_user.id)
        assert session.user_id == test_user.id
        assert session.session_token
        assert session.expires_at > datetime.now(timezone.utc).replace(tzinfo=None)

    def test_get_valid_session(self, db, test_user):
        session = web_session_repo.create_session(db, test_user.id)
        found = web_session_repo.get_valid_session(db, session.session_token)
        assert found is not None
        assert found.id == session.id

    def test_get_valid_session_not_found(self, db):
        found = web_session_repo.get_valid_session(db, "nonexistent")
        assert found is None

    def test_delete_session(self, db, test_user):
        session = web_session_repo.create_session(db, test_user.id)
        assert web_session_repo.delete_session(db, session.session_token)
        assert web_session_repo.get_valid_session(db, session.session_token) is None

    def test_delete_nonexistent_session(self, db):
        assert not web_session_repo.delete_session(db, "nonexistent")

    def test_session_lifetime(self, db, test_user):
        session = web_session_repo.create_session(db, test_user.id)
        expected = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30)
        assert abs((session.expires_at - expected).total_seconds()) < 5
