import uuid

import pytest
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.restaurant import Restaurant, RestaurantSource
from app.models.user import User
from app.schemas.google_maps import Location
from app.schemas.google_maps import Restaurant as MapsRestaurant
from app.services.restaurant_repo import upsert_from_maps

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


def test_upsert_from_maps_copies_user_ratings_total(db):
    maps_data = MapsRestaurant(
        place_id="ChIJ_test_urt",
        name="Ratings Count Test",
        location=Location(lat=13.7, lng=100.5),
        rating=4.3,
        user_ratings_total=245,
        price_level=2,
        types=["restaurant"],
    )

    restaurant = upsert_from_maps(db, maps_data)

    assert restaurant.user_ratings_total == 245


def test_upsert_from_maps_updates_user_ratings_total_on_conflict(db):
    maps_data = MapsRestaurant(
        place_id="ChIJ_test_urt_update",
        name="Update Test",
        location=Location(lat=13.7, lng=100.5),
        rating=4.0,
        user_ratings_total=100,
        types=["restaurant"],
    )

    upsert_from_maps(db, maps_data)

    maps_data.user_ratings_total = 150
    maps_data.rating = 4.1
    restaurant = upsert_from_maps(db, maps_data)

    assert restaurant.user_ratings_total == 150
    assert restaurant.rating == 4.1
