import uuid
from dataclasses import dataclass, field
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.models.restaurant import RestaurantSource
from app.services.recommendation import (
    _haversine,
    build_pool,
    filter_restaurants,
    sample_candidates,
)


@dataclass
class FakeRestaurant:
    id: uuid.UUID = None
    name: str = "Test Restaurant"
    source: str = RestaurantSource.GOOGLE_MAPS
    lat: float | None = 13.756
    lng: float | None = 100.502
    rating: float | None = 4.0
    user_ratings_total: int | None = 50
    price_level: int | None = 2
    types: list = field(default_factory=lambda: ["restaurant"])
    closed_weekdays: list = field(default_factory=list)
    closed_monthly_ranges: list = field(default_factory=list)
    place_id: str | None = None
    vicinity: str | None = None
    photo_reference: str | None = None
    added_by: uuid.UUID | None = None
    last_fetched_at: object = None
    created_at: object = None

    def __post_init__(self):
        if self.id is None:
            self.id = uuid.uuid4()


def _make_restaurant(**kwargs):
    return FakeRestaurant(**kwargs)


class TestHaversine:
    def test_same_point(self):
        assert _haversine(13.756, 100.502, 13.756, 100.502) == 0

    def test_known_distance(self):
        dist = _haversine(13.756, 100.502, 13.757, 100.503)
        assert 100 < dist < 200


class TestFilterRestaurants:
    def test_pass_all(self):
        r = _make_restaurant()
        result = filter_restaurants([r], {"today_weekday": 0, "today_date": date(2026, 4, 20)})
        assert len(result) == 1

    def test_filter_closed_weekday(self):
        r = _make_restaurant(closed_weekdays=[0])
        result = filter_restaurants([r], {"today_weekday": 0, "today_date": date(2026, 4, 20)})
        assert len(result) == 0

    def test_filter_closed_monthly_range(self):
        r = _make_restaurant(closed_monthly_ranges=[{"start": "2026-04-19", "end": "2026-04-21"}])
        result = filter_restaurants([r], {"today_weekday": 0, "today_date": date(2026, 4, 20)})
        assert len(result) == 0

    def test_pass_outside_closed_range(self):
        r = _make_restaurant(closed_monthly_ranges=[{"start": "2026-04-10", "end": "2026-04-15"}])
        result = filter_restaurants([r], {"today_weekday": 0, "today_date": date(2026, 4, 20)})
        assert len(result) == 1

    def test_filter_out_of_radius(self):
        r = _make_restaurant(lat=14.0, lng=101.0)
        result = filter_restaurants(
            [r],
            {"today_weekday": 0, "today_date": date(2026, 4, 20), "office_lat": 13.756, "office_lng": 100.502, "radius": 1000},
        )
        assert len(result) == 0

    def test_pass_within_radius(self):
        r = _make_restaurant(lat=13.757, lng=100.503)
        result = filter_restaurants(
            [r],
            {"today_weekday": 0, "today_date": date(2026, 4, 20), "office_lat": 13.756, "office_lng": 100.502, "radius": 1000},
        )
        assert len(result) == 1

    def test_manual_no_latlng_passes(self):
        r = _make_restaurant(source=RestaurantSource.MANUAL, lat=None, lng=None)
        result = filter_restaurants(
            [r],
            {"today_weekday": 0, "today_date": date(2026, 4, 20), "office_lat": 13.756, "office_lng": 100.502, "radius": 1000},
        )
        assert len(result) == 1

    def test_filter_excludes_rating_below_threshold(self):
        low = _make_restaurant(rating=3.5, user_ratings_total=100)
        ok = _make_restaurant(rating=4.2, user_ratings_total=100)
        context = {
            "office_lat": 13.756, "office_lng": 100.502, "radius": 1000,
            "rating_threshold": 3.8, "ratings_count_threshold": 20,
        }
        result = filter_restaurants([low, ok], context)
        assert ok in result
        assert low not in result

    def test_filter_excludes_ratings_count_below_threshold(self):
        few = _make_restaurant(rating=4.5, user_ratings_total=5)
        ok = _make_restaurant(rating=4.0, user_ratings_total=50)
        context = {
            "office_lat": 13.756, "office_lng": 100.502, "radius": 1000,
            "rating_threshold": 3.8, "ratings_count_threshold": 20,
        }
        result = filter_restaurants([few, ok], context)
        assert ok in result
        assert few not in result

    def test_filter_excludes_null_rating(self):
        manual = _make_restaurant(rating=None, user_ratings_total=None)
        context = {
            "office_lat": 13.756, "office_lng": 100.502, "radius": 1000,
            "rating_threshold": 3.8, "ratings_count_threshold": 20,
        }
        result = filter_restaurants([manual], context)
        assert manual not in result


class TestBuildPool:
    def test_build_pool_uses_uniform_weights(self):
        restaurants = [_make_restaurant(rating=r) for r in [4.0, 4.2, 4.5, 4.8]]
        pool = build_pool(restaurants, pool_size=10)

        assert len(pool) == 4
        for _, weight in pool:
            assert weight == 1.0

    def test_build_pool_limits_to_pool_size(self):
        restaurants = [_make_restaurant() for _ in range(20)]
        pool = build_pool(restaurants, pool_size=10)

        assert len(pool) == 10

    def test_build_pool_shuffles(self):
        import random
        from app.services.recommendation import build_pool

        random.seed(42)
        restaurants = [_make_restaurant(name=f"R{i}") for i in range(10)]
        ordered_ids_before = [r.id for r in restaurants]
        pool = build_pool(restaurants, pool_size=10)
        ordered_ids_after = [r.id for r, _ in pool]

        assert set(ordered_ids_before) == set(ordered_ids_after)
        assert ordered_ids_before != ordered_ids_after


class TestSampleCandidates:
    def test_returns_k(self):
        pool = [(_make_restaurant(name=f"R{i}"), float(5 - i)) for i in range(10)]
        picks = sample_candidates(pool, k=3)
        assert len(picks) == 3

    def test_no_duplicates(self):
        pool = [(_make_restaurant(name=f"R{i}"), float(5 - i)) for i in range(10)]
        picks = sample_candidates(pool, k=3)
        names = [p.name for p in picks]
        assert len(set(names)) == 3

    def test_pool_smaller_than_k(self):
        pool = [(_make_restaurant(name=f"R{i}"), float(5 - i)) for i in range(2)]
        picks = sample_candidates(pool, k=3)
        assert len(picks) == 2


class TestRecommendEndpoint:
    @pytest.mark.asyncio
    @patch("app.services.recommendation.fetch_candidates")
    async def test_full_pipeline(self, mock_fetch):
        restaurants = [_make_restaurant(name=f"R{i}", rating=4.0 + i * 0.1) for i in range(15)]
        mock_fetch.return_value = (restaurants, set())

        from app.services.recommendation import recommend

        with patch("app.services.recommendation.restaurant_repo"), \
             patch("app.services.recommendation.history_repo") as mock_history, \
             patch("app.services.recommendation.blacklist_repo") as mock_blacklist:
            mock_history.get_recent_restaurant_ids.return_value = set()
            mock_blacklist.get_blacklisted_restaurant_ids.return_value = set()
            result = await recommend(
                db=None,
                user_ids=[uuid.uuid4()],
                office_lat=13.756,
                office_lng=100.502,
            )

        assert len(result["candidates"]) == 3
        assert len(result["pool"]) == 10
        assert "session_id" in result

    @pytest.mark.asyncio
    @patch("app.services.recommendation.fetch_candidates")
    async def test_few_restaurants(self, mock_fetch):
        restaurants = [_make_restaurant(name=f"R{i}", rating=4.0) for i in range(2)]
        mock_fetch.return_value = (restaurants, set())

        from app.services.recommendation import recommend

        with patch("app.services.recommendation.restaurant_repo"), \
             patch("app.services.recommendation.history_repo") as mock_history, \
             patch("app.services.recommendation.blacklist_repo") as mock_blacklist:
            mock_history.get_recent_restaurant_ids.return_value = set()
            mock_blacklist.get_blacklisted_restaurant_ids.return_value = set()
            result = await recommend(
                db=None,
                user_ids=[uuid.uuid4()],
                office_lat=13.756,
                office_lng=100.502,
            )

        assert len(result["candidates"]) == 2
        assert len(result["pool"]) == 2
