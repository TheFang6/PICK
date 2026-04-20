import uuid
from dataclasses import dataclass, field
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.models.restaurant import RestaurantSource
from app.services.recommendation import (
    _haversine,
    filter_restaurants,
    sample_candidates,
    score_restaurants,
    select_pool,
)


@dataclass
class FakeRestaurant:
    id: uuid.UUID = None
    name: str = "Test Restaurant"
    source: str = RestaurantSource.GOOGLE_MAPS
    lat: float | None = 13.756
    lng: float | None = 100.502
    rating: float | None = 4.0
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


class TestScoreRestaurants:
    def test_higher_rating_scores_higher(self):
        r1 = _make_restaurant(name="High", rating=4.8, price_level=2)
        r2 = _make_restaurant(name="Low", rating=3.0, price_level=2)
        scored = score_restaurants([r1, r2], {"office_lat": 13.756, "office_lng": 100.502, "radius": 1000})
        assert scored[0][0].name == "High"
        assert scored[0][1] > scored[1][1]

    def test_no_rating_uses_default(self):
        r = _make_restaurant(rating=None)
        scored = score_restaurants([r], {})
        assert scored[0][1] > 0

    def test_sorted_descending(self):
        restaurants = [
            _make_restaurant(name="A", rating=3.0),
            _make_restaurant(name="B", rating=5.0),
            _make_restaurant(name="C", rating=4.0),
        ]
        scored = score_restaurants(restaurants, {})
        names = [r.name for r, _ in scored]
        assert names[0] == "B"


class TestSelectPool:
    def test_pool_size(self):
        scored = [(r, 1.0) for r in [_make_restaurant(name=f"R{i}") for i in range(20)]]
        pool = select_pool(scored, pool_size=10)
        assert len(pool) == 10

    def test_pool_smaller_than_input(self):
        scored = [(r, 1.0) for r in [_make_restaurant(name=f"R{i}") for i in range(3)]]
        pool = select_pool(scored, pool_size=10)
        assert len(pool) == 3


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
        mock_fetch.return_value = restaurants

        from app.services.recommendation import recommend

        with patch("app.services.recommendation.restaurant_repo"):
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
        mock_fetch.return_value = restaurants

        from app.services.recommendation import recommend

        with patch("app.services.recommendation.restaurant_repo"):
            result = await recommend(
                db=None,
                user_ids=[uuid.uuid4()],
                office_lat=13.756,
                office_lng=100.502,
            )

        assert len(result["candidates"]) == 2
        assert len(result["pool"]) == 2
