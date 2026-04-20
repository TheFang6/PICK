import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.restaurant import Restaurant, RestaurantSource
from app.models.user import User
from app.models.user_blacklist import BlacklistMode, UserBlacklist
from app.services import blacklist_repo

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
    user = User(id=uuid.uuid4(), telegram_id="111222333", name="Blacklist User")
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def test_user_2(db):
    user = User(id=uuid.uuid4(), telegram_id="444555666", name="Other User")
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def test_restaurant(db):
    restaurant = Restaurant(
        id=uuid.uuid4(),
        name="Blacklist Restaurant",
        source=RestaurantSource.MANUAL,
        lat=13.756,
        lng=100.502,
    )
    db.add(restaurant)
    db.flush()
    return restaurant


@pytest.fixture
def test_restaurant_2(db):
    restaurant = Restaurant(
        id=uuid.uuid4(),
        name="Another Restaurant",
        source=RestaurantSource.MANUAL,
        lat=13.757,
        lng=100.503,
    )
    db.add(restaurant)
    db.flush()
    return restaurant


class TestBlacklistAdd:
    def test_add_permanent(self, db, test_user, test_restaurant):
        entry = blacklist_repo.add(db, test_user.id, test_restaurant.id, BlacklistMode.PERMANENT)
        assert entry.mode == BlacklistMode.PERMANENT
        assert entry.expires_at is None

    def test_add_today(self, db, test_user, test_restaurant):
        entry = blacklist_repo.add(db, test_user.id, test_restaurant.id, BlacklistMode.TODAY)
        assert entry.mode == BlacklistMode.TODAY
        assert entry.expires_at is not None

    def test_upsert_same_restaurant(self, db, test_user, test_restaurant):
        blacklist_repo.add(db, test_user.id, test_restaurant.id, BlacklistMode.TODAY)
        entry = blacklist_repo.add(db, test_user.id, test_restaurant.id, BlacklistMode.PERMANENT)
        assert entry.mode == BlacklistMode.PERMANENT
        assert entry.expires_at is None
        entries = blacklist_repo.list_by_user(db, test_user.id)
        assert len(entries) == 1


class TestBlacklistRemove:
    def test_remove_own(self, db, test_user, test_restaurant):
        entry = blacklist_repo.add(db, test_user.id, test_restaurant.id)
        assert blacklist_repo.remove(db, test_user.id, entry.id) is True

    def test_remove_other_user_fails(self, db, test_user, test_user_2, test_restaurant):
        entry = blacklist_repo.add(db, test_user.id, test_restaurant.id)
        assert blacklist_repo.remove(db, test_user_2.id, entry.id) is False

    def test_remove_nonexistent(self, db, test_user):
        assert blacklist_repo.remove(db, test_user.id, uuid.uuid4()) is False


class TestBlacklistList:
    def test_list_active_only(self, db, test_user, test_restaurant, test_restaurant_2):
        blacklist_repo.add(db, test_user.id, test_restaurant.id, BlacklistMode.PERMANENT)
        entry2 = blacklist_repo.add(db, test_user.id, test_restaurant_2.id, BlacklistMode.TODAY)
        entry2.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()

        entries = blacklist_repo.list_by_user(db, test_user.id)
        assert len(entries) == 1
        assert entries[0].restaurant_id == test_restaurant.id

    def test_list_empty(self, db, test_user):
        entries = blacklist_repo.list_by_user(db, test_user.id)
        assert len(entries) == 0


class TestGetBlacklistedIds:
    def test_returns_blacklisted(self, db, test_user, test_restaurant):
        blacklist_repo.add(db, test_user.id, test_restaurant.id)
        ids = blacklist_repo.get_blacklisted_restaurant_ids(db, [test_user.id])
        assert test_restaurant.id in ids

    def test_excludes_expired(self, db, test_user, test_restaurant):
        entry = blacklist_repo.add(db, test_user.id, test_restaurant.id, BlacklistMode.TODAY)
        entry.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()
        ids = blacklist_repo.get_blacklisted_restaurant_ids(db, [test_user.id])
        assert test_restaurant.id not in ids

    def test_union_multiple_users(self, db, test_user, test_user_2, test_restaurant, test_restaurant_2):
        blacklist_repo.add(db, test_user.id, test_restaurant.id)
        blacklist_repo.add(db, test_user_2.id, test_restaurant_2.id)
        ids = blacklist_repo.get_blacklisted_restaurant_ids(db, [test_user.id, test_user_2.id])
        assert test_restaurant.id in ids
        assert test_restaurant_2.id in ids

    def test_empty_user_ids(self, db):
        ids = blacklist_repo.get_blacklisted_restaurant_ids(db, [])
        assert len(ids) == 0


class TestCleanupExpired:
    def test_removes_expired(self, db, test_user, test_restaurant, test_restaurant_2):
        blacklist_repo.add(db, test_user.id, test_restaurant.id, BlacklistMode.PERMANENT)
        entry2 = blacklist_repo.add(db, test_user.id, test_restaurant_2.id, BlacklistMode.TODAY)
        entry2.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()

        count = blacklist_repo.cleanup_expired(db)
        assert count == 1
        entries = blacklist_repo.list_by_user(db, test_user.id)
        assert len(entries) == 1


class TestRecommendationBlacklistFilter:
    def test_filter_excludes_blacklisted(self):
        from dataclasses import dataclass, field

        @dataclass
        class FakeR:
            id: uuid.UUID = None
            name: str = "Test"
            source: str = RestaurantSource.GOOGLE_MAPS
            lat: float | None = 13.756
            lng: float | None = 100.502
            rating: float | None = 4.0
            price_level: int | None = 2
            closed_weekdays: list = field(default_factory=list)
            closed_monthly_ranges: list = field(default_factory=list)

            def __post_init__(self):
                if self.id is None:
                    self.id = uuid.uuid4()

        from datetime import date
        from app.services.recommendation import filter_restaurants

        r1 = FakeR(name="Blocked")
        r2 = FakeR(name="OK")
        context = {
            "today_weekday": 0,
            "today_date": date(2026, 4, 20),
            "blacklisted_ids": {r1.id},
        }
        result = filter_restaurants([r1, r2], context)
        assert len(result) == 1
        assert result[0].name == "OK"


class TestBlacklistAPI:
    def test_add_permanent(self, client, test_user, test_restaurant):
        resp = client.post(
            f"/blacklist?user_id={test_user.id}",
            json={"restaurant_id": str(test_restaurant.id), "mode": "permanent"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["mode"] == "permanent"
        assert data["expires_at"] is None

    def test_add_today(self, client, test_user, test_restaurant):
        resp = client.post(
            f"/blacklist?user_id={test_user.id}",
            json={"restaurant_id": str(test_restaurant.id), "mode": "today"},
        )
        assert resp.status_code == 201
        assert resp.json()["expires_at"] is not None

    def test_add_invalid_mode(self, client, test_user, test_restaurant):
        resp = client.post(
            f"/blacklist?user_id={test_user.id}",
            json={"restaurant_id": str(test_restaurant.id), "mode": "invalid"},
        )
        assert resp.status_code == 400

    def test_add_invalid_restaurant(self, client, test_user):
        resp = client.post(
            f"/blacklist?user_id={test_user.id}",
            json={"restaurant_id": str(uuid.uuid4()), "mode": "permanent"},
        )
        assert resp.status_code == 404

    def test_list_blacklist(self, client, test_user, test_restaurant):
        client.post(
            f"/blacklist?user_id={test_user.id}",
            json={"restaurant_id": str(test_restaurant.id)},
        )
        resp = client.get(f"/blacklist?user_id={test_user.id}")
        assert resp.status_code == 200
        assert len(resp.json()["entries"]) == 1

    def test_remove_blacklist(self, client, test_user, test_restaurant):
        add_resp = client.post(
            f"/blacklist?user_id={test_user.id}",
            json={"restaurant_id": str(test_restaurant.id)},
        )
        entry_id = add_resp.json()["id"]
        resp = client.delete(f"/blacklist/{entry_id}?user_id={test_user.id}")
        assert resp.status_code == 204

    def test_remove_not_found(self, client, test_user):
        resp = client.delete(f"/blacklist/{uuid.uuid4()}?user_id={test_user.id}")
        assert resp.status_code == 404
