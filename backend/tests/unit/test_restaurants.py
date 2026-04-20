import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.restaurant import Restaurant, RestaurantSource
from app.models.user import User
from app.schemas.restaurant import ManualRestaurantCreate, RestaurantUpdate
from app.services import restaurant_repo

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
    user = User(id=uuid.uuid4(), telegram_id="123456789", name="Test User")
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def google_restaurant(db):
    r = Restaurant(
        id=uuid.uuid4(),
        place_id="ChIJtest123",
        name="Google Restaurant",
        source=RestaurantSource.GOOGLE_MAPS,
        lat=13.756,
        lng=100.502,
        vicinity="123 Test Street",
        rating=4.5,
        price_level=2,
        types=["restaurant", "food"],
        photo_reference="photo_ref_abc",
    )
    db.add(r)
    db.flush()
    return r


class TestCreateManual:
    def test_create(self, db, test_user):
        data = ManualRestaurantCreate(name="My Restaurant", vicinity="Near office")
        r = restaurant_repo.create_manual(db, data, test_user.id)
        assert r.name == "My Restaurant"
        assert r.source == RestaurantSource.MANUAL
        assert r.added_by == test_user.id
        assert r.place_id is None


class TestGetById:
    def test_found(self, db, google_restaurant):
        found = restaurant_repo.get_by_id(db, google_restaurant.id)
        assert found is not None
        assert found.name == "Google Restaurant"

    def test_not_found(self, db):
        found = restaurant_repo.get_by_id(db, uuid.uuid4())
        assert found is None


class TestListAll:
    def test_empty(self, db):
        restaurants, total = restaurant_repo.list_all(db)
        assert restaurants == []
        assert total == 0

    def test_filter_by_source(self, db, test_user, google_restaurant):
        restaurant_repo.create_manual(db, ManualRestaurantCreate(name="Manual"), test_user.id)

        maps_list, maps_total = restaurant_repo.list_all(db, source="google_maps")
        assert maps_total == 1
        manual_list, manual_total = restaurant_repo.list_all(db, source="manual")
        assert manual_total == 1

    def test_pagination(self, db, test_user):
        for i in range(5):
            restaurant_repo.create_manual(db, ManualRestaurantCreate(name=f"R{i}"), test_user.id)

        page1, total = restaurant_repo.list_all(db, page=1, page_size=2)
        assert len(page1) == 2
        assert total == 5
        page2, _ = restaurant_repo.list_all(db, page=2, page_size=2)
        assert len(page2) == 2


class TestUpdate:
    def test_update_manual(self, db, test_user):
        r = restaurant_repo.create_manual(db, ManualRestaurantCreate(name="Old Name"), test_user.id)
        updated = restaurant_repo.update(db, r.id, RestaurantUpdate(name="New Name"))
        assert updated.name == "New Name"

    def test_update_not_found(self, db):
        result = restaurant_repo.update(db, uuid.uuid4(), RestaurantUpdate(name="X"))
        assert result is None


class TestDelete:
    def test_delete(self, db, test_user):
        r = restaurant_repo.create_manual(db, ManualRestaurantCreate(name="Delete Me"), test_user.id)
        assert restaurant_repo.delete(db, r.id) is True
        assert restaurant_repo.get_by_id(db, r.id) is None

    def test_delete_not_found(self, db):
        assert restaurant_repo.delete(db, uuid.uuid4()) is False


class TestAPIEndpoints:
    def test_list_empty(self, client):
        resp = client.get("/restaurants")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["restaurants"] == []

    def test_create_and_get(self, client, test_user):
        resp = client.post(
            f"/restaurants/manual?user_id={test_user.id}",
            json={"name": "API Restaurant", "vicinity": "Test"},
        )
        assert resp.status_code == 201
        rid = resp.json()["id"]

        resp = client.get(f"/restaurants/{rid}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "API Restaurant"
        assert resp.json()["source"] == "manual"

    def test_update_own_restaurant(self, client, test_user):
        resp = client.post(
            f"/restaurants/manual?user_id={test_user.id}",
            json={"name": "Original"},
        )
        rid = resp.json()["id"]

        resp = client.put(
            f"/restaurants/{rid}?user_id={test_user.id}",
            json={"name": "Updated"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"

    def test_update_other_user_forbidden(self, client, test_user):
        resp = client.post(
            f"/restaurants/manual?user_id={test_user.id}",
            json={"name": "Mine"},
        )
        rid = resp.json()["id"]

        resp = client.put(
            f"/restaurants/{rid}?user_id={uuid.uuid4()}",
            json={"name": "Hacked"},
        )
        assert resp.status_code == 403

    def test_delete_own_restaurant(self, client, test_user):
        resp = client.post(
            f"/restaurants/manual?user_id={test_user.id}",
            json={"name": "Delete Me"},
        )
        rid = resp.json()["id"]

        resp = client.delete(f"/restaurants/{rid}?user_id={test_user.id}")
        assert resp.status_code == 204

        resp = client.get(f"/restaurants/{rid}")
        assert resp.status_code == 404

    def test_delete_other_user_forbidden(self, client, test_user):
        resp = client.post(
            f"/restaurants/manual?user_id={test_user.id}",
            json={"name": "Mine"},
        )
        rid = resp.json()["id"]

        resp = client.delete(f"/restaurants/{rid}?user_id={uuid.uuid4()}")
        assert resp.status_code == 403

    def test_get_not_found(self, client):
        resp = client.get(f"/restaurants/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_cannot_edit_google_maps_restaurant(self, client, google_restaurant):
        resp = client.put(
            f"/restaurants/{google_restaurant.id}?user_id={uuid.uuid4()}",
            json={"name": "Hacked"},
        )
        assert resp.status_code == 403
