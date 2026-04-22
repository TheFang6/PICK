import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.lunch_history import LunchHistory
from app.models.restaurant import Restaurant, RestaurantSource
from app.models.user import User
from app.services import history_repo, restaurant_repo

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
    user = User(id=uuid.uuid4(), telegram_id="111222333", name="Search User")
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def restaurants(db):
    names = ["Som Tam Nua", "Khao Man Gai", "Pad Thai Place", "Somtam Seafood"]
    result = []
    for name in names:
        r = Restaurant(
            id=uuid.uuid4(),
            name=name,
            source=RestaurantSource.MANUAL,
        )
        db.add(r)
        result.append(r)
    db.flush()
    return result


# --- Restaurant search ---

class TestRestaurantSearch:
    def test_search_by_name(self, db, restaurants):
        results = restaurant_repo.search(db, "Som")
        names = [r.name for r in results]
        assert "Som Tam Nua" in names
        assert "Somtam Seafood" in names

    def test_search_case_insensitive(self, db, restaurants):
        results = restaurant_repo.search(db, "som tam")
        assert len(results) >= 1

    def test_search_no_match(self, db, restaurants):
        results = restaurant_repo.search(db, "Sushi")
        assert len(results) == 0

    def test_search_api(self, client, restaurants):
        res = client.get("/restaurants?search=Khao")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1
        assert any("Khao" in r["name"] for r in data["restaurants"])

    def test_search_api_empty(self, client, restaurants):
        res = client.get("/restaurants?search=NotFound")
        assert res.status_code == 200
        assert res.json()["total"] == 0


# --- History month filter ---

class TestHistoryMonthFilter:
    def test_filter_by_month(self, db, test_user, restaurants):
        r1, r2 = restaurants[0], restaurants[1]
        history_repo.log_lunch(db, r1.id, [test_user.id], lunch_date=date(2026, 4, 10))
        history_repo.log_lunch(db, r2.id, [test_user.id], lunch_date=date(2026, 3, 15))

        april = history_repo.get_user_history(db, test_user.id, month="2026-04")
        assert len(april) == 1
        assert april[0].restaurant_id == r1.id

        march = history_repo.get_user_history(db, test_user.id, month="2026-03")
        assert len(march) == 1
        assert march[0].restaurant_id == r2.id

    def test_filter_no_results(self, db, test_user, restaurants):
        history_repo.log_lunch(db, restaurants[0].id, [test_user.id], lunch_date=date(2026, 4, 10))
        result = history_repo.get_user_history(db, test_user.id, month="2026-01")
        assert len(result) == 0

    def test_team_history_month_filter(self, db, test_user, restaurants):
        history_repo.log_lunch(db, restaurants[0].id, [test_user.id], lunch_date=date(2026, 4, 5))
        history_repo.log_lunch(db, restaurants[1].id, [test_user.id], lunch_date=date(2026, 3, 5))

        april = history_repo.get_team_history(db, month="2026-04")
        assert len(april) == 1

    def test_history_api_month_filter(self, client, db, test_user, restaurants):
        history_repo.log_lunch(db, restaurants[0].id, [test_user.id], lunch_date=date(2026, 4, 10))
        history_repo.log_lunch(db, restaurants[1].id, [test_user.id], lunch_date=date(2026, 3, 15))

        res = client.get(f"/history?user_id={test_user.id}&month=2026-04")
        assert res.status_code == 200
        assert len(res.json()["entries"]) == 1

    def test_team_history_api_month_filter(self, client, db, test_user, restaurants):
        history_repo.log_lunch(db, restaurants[0].id, [test_user.id], lunch_date=date(2026, 4, 10))
        history_repo.log_lunch(db, restaurants[1].id, [test_user.id], lunch_date=date(2026, 3, 15))

        res = client.get("/history/team?month=2026-04")
        assert res.status_code == 200
        assert len(res.json()["entries"]) == 1


# --- Enriched responses ---

class TestEnrichedResponses:
    def test_blacklist_includes_restaurant_name(self, client, db, test_user, restaurants):
        res = client.post(
            f"/blacklist?user_id={test_user.id}",
            json={"restaurant_id": str(restaurants[0].id), "mode": "permanent"},
        )
        assert res.status_code == 201

        res = client.get(f"/blacklist?user_id={test_user.id}")
        assert res.status_code == 200
        entries = res.json()["entries"]
        assert len(entries) == 1
        assert entries[0]["restaurant_name"] == restaurants[0].name

    def test_history_includes_restaurant_name(self, client, db, test_user, restaurants):
        history_repo.log_lunch(db, restaurants[0].id, [test_user.id], lunch_date=date(2026, 4, 10))
        res = client.get(f"/history?user_id={test_user.id}")
        assert res.status_code == 200
        entries = res.json()["entries"]
        assert len(entries) == 1
        assert entries[0]["restaurant_name"] == restaurants[0].name

    def test_history_includes_attendee_names(self, client, db, test_user, restaurants):
        history_repo.log_lunch(db, restaurants[0].id, [test_user.id], lunch_date=date(2026, 4, 10))
        res = client.get(f"/history?user_id={test_user.id}")
        entries = res.json()["entries"]
        assert entries[0]["attendee_names"] == ["Search User"]
