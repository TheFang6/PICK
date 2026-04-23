import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.lunch_history import LunchHistory
from app.models.restaurant import Restaurant, RestaurantSource
from app.models.user import User
from app.services import history_repo

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


@pytest.fixture
def test_restaurant(db):
    restaurant = Restaurant(
        id=uuid.uuid4(),
        name="Test Restaurant",
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


class TestLogLunch:
    def test_log_lunch_default_date(self, db, test_restaurant):
        user_id = uuid.uuid4()
        entry = history_repo.log_lunch(db, test_restaurant.id, [user_id])
        assert entry.restaurant_id == test_restaurant.id
        assert entry.date is not None
        assert str(user_id) in entry.attendees

    def test_log_lunch_custom_date(self, db, test_restaurant):
        user_id = uuid.uuid4()
        custom_date = date(2026, 4, 15)
        entry = history_repo.log_lunch(db, test_restaurant.id, [user_id], lunch_date=custom_date)
        assert entry.date == custom_date

    def test_log_lunch_multiple_attendees(self, db, test_restaurant):
        users = [uuid.uuid4() for _ in range(3)]
        entry = history_repo.log_lunch(db, test_restaurant.id, users)
        assert len(entry.attendees) == 3
        for u in users:
            assert str(u) in entry.attendees


class TestGetRecentRestaurantIds:
    def test_returns_recent(self, db, test_restaurant):
        user_id = uuid.uuid4()
        history_repo.log_lunch(db, test_restaurant.id, [user_id], lunch_date=date.today())
        recent = history_repo.get_recent_restaurant_ids(db, [user_id], days=7)
        assert test_restaurant.id in recent

    def test_excludes_old(self, db, test_restaurant):
        user_id = uuid.uuid4()
        old_date = date.today() - timedelta(days=10)
        history_repo.log_lunch(db, test_restaurant.id, [user_id], lunch_date=old_date)
        recent = history_repo.get_recent_restaurant_ids(db, [user_id], days=7)
        assert test_restaurant.id not in recent

    def test_union_multiple_users(self, db, test_restaurant, test_restaurant_2):
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()
        history_repo.log_lunch(db, test_restaurant.id, [user_a], lunch_date=date.today())
        history_repo.log_lunch(db, test_restaurant_2.id, [user_b], lunch_date=date.today())
        recent = history_repo.get_recent_restaurant_ids(db, [user_a, user_b], days=7)
        assert test_restaurant.id in recent
        assert test_restaurant_2.id in recent

    def test_ignores_unrelated_users(self, db, test_restaurant):
        other_user = uuid.uuid4()
        history_repo.log_lunch(db, test_restaurant.id, [other_user], lunch_date=date.today())
        querying_user = uuid.uuid4()
        recent = history_repo.get_recent_restaurant_ids(db, [querying_user], days=7)
        assert test_restaurant.id not in recent

    def test_empty_when_no_history(self, db):
        recent = history_repo.get_recent_restaurant_ids(db, [uuid.uuid4()], days=7)
        assert len(recent) == 0


class TestGetUserHistory:
    def test_returns_user_entries(self, db, test_restaurant, test_restaurant_2):
        user_id = uuid.uuid4()
        other_user = uuid.uuid4()
        history_repo.log_lunch(db, test_restaurant.id, [user_id], lunch_date=date.today())
        history_repo.log_lunch(db, test_restaurant_2.id, [other_user], lunch_date=date.today())
        entries = history_repo.get_user_history(db, user_id)
        assert len(entries) == 1
        assert entries[0].restaurant_id == test_restaurant.id

    def test_limit_and_offset(self, db, test_restaurant):
        user_id = uuid.uuid4()
        for i in range(5):
            history_repo.log_lunch(db, test_restaurant.id, [user_id], lunch_date=date.today() - timedelta(days=i))
        entries = history_repo.get_user_history(db, user_id, limit=2, offset=1)
        assert len(entries) == 2


class TestGetTeamHistory:
    def test_returns_all_entries(self, db, test_restaurant, test_restaurant_2):
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()
        history_repo.log_lunch(db, test_restaurant.id, [user_a], lunch_date=date.today())
        history_repo.log_lunch(db, test_restaurant_2.id, [user_b], lunch_date=date.today())
        entries = history_repo.get_team_history(db)
        assert len(entries) == 2

    def test_limit(self, db, test_restaurant):
        user_id = uuid.uuid4()
        for i in range(5):
            history_repo.log_lunch(db, test_restaurant.id, [user_id], lunch_date=date.today() - timedelta(days=i))
        entries = history_repo.get_team_history(db, limit=3)
        assert len(entries) == 3


class TestRecommendationHistoryFilter:
    def test_filter_excludes_recent(self):
        from dataclasses import dataclass, field

        @dataclass
        class FakeR:
            id: uuid.UUID = None
            name: str = "Test"
            source: str = RestaurantSource.GOOGLE_MAPS
            lat: float | None = 13.756
            lng: float | None = 100.502
            rating: float | None = 4.0
            user_ratings_total: int | None = 50
            price_level: int | None = 2
            closed_weekdays: list = field(default_factory=list)
            closed_monthly_ranges: list = field(default_factory=list)

            def __post_init__(self):
                if self.id is None:
                    self.id = uuid.uuid4()

        from app.services.recommendation import filter_restaurants

        r1 = FakeR(name="Recent")
        r2 = FakeR(name="Fresh")
        context = {
            "today_weekday": 0,
            "today_date": date(2026, 4, 20),
            "recent_restaurant_ids": {r1.id},
        }
        result = filter_restaurants([r1, r2], context)
        assert len(result) == 1
        assert result[0].name == "Fresh"

    def test_filter_passes_when_no_history(self):
        from dataclasses import dataclass, field

        @dataclass
        class FakeR:
            id: uuid.UUID = None
            name: str = "Test"
            source: str = RestaurantSource.GOOGLE_MAPS
            lat: float | None = 13.756
            lng: float | None = 100.502
            rating: float | None = 4.0
            user_ratings_total: int | None = 50
            price_level: int | None = 2
            closed_weekdays: list = field(default_factory=list)
            closed_monthly_ranges: list = field(default_factory=list)

            def __post_init__(self):
                if self.id is None:
                    self.id = uuid.uuid4()

        from app.services.recommendation import filter_restaurants

        r1 = FakeR(name="A")
        r2 = FakeR(name="B")
        context = {
            "today_weekday": 0,
            "today_date": date(2026, 4, 20),
            "recent_restaurant_ids": set(),
        }
        result = filter_restaurants([r1, r2], context)
        assert len(result) == 2


class TestHistoryAPI:
    def test_log_lunch(self, client, test_restaurant):
        user_id = str(uuid.uuid4())
        resp = client.post("/history", json={
            "restaurant_id": str(test_restaurant.id),
            "attendees": [user_id],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["restaurant_id"] == str(test_restaurant.id)
        assert user_id in data["attendees"]

    def test_log_lunch_invalid_restaurant(self, client):
        resp = client.post("/history", json={
            "restaurant_id": str(uuid.uuid4()),
            "attendees": [str(uuid.uuid4())],
        })
        assert resp.status_code == 404

    def test_get_user_history(self, client, test_restaurant):
        user_id = str(uuid.uuid4())
        client.post("/history", json={
            "restaurant_id": str(test_restaurant.id),
            "attendees": [user_id],
        })
        resp = client.get(f"/history?user_id={user_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["entries"]) == 1

    def test_get_team_history(self, client, test_restaurant):
        client.post("/history", json={
            "restaurant_id": str(test_restaurant.id),
            "attendees": [str(uuid.uuid4())],
        })
        resp = client.get("/history/team")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["entries"]) == 1

    def test_log_lunch_with_custom_date(self, client, test_restaurant):
        resp = client.post("/history", json={
            "restaurant_id": str(test_restaurant.id),
            "attendees": [str(uuid.uuid4())],
            "date": "2026-04-15",
        })
        assert resp.status_code == 201
        assert resp.json()["date"] == "2026-04-15"
