import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.restaurant import RestaurantSource
from app.services import session_pool
from app.services.gacha import (
    GachaLimitExceeded,
    SessionExpired,
    SessionNotFound,
    roll,
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
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


def _make_pool(n: int = 10) -> list[tuple]:
    return [(FakeRestaurant(name=f"R{i}"), float(5 - i * 0.3)) for i in range(n)]


@pytest.fixture(autouse=True)
def clear_sessions():
    session_pool.clear_all()
    yield
    session_pool.clear_all()


class TestSessionPool:
    def test_create_session(self):
        pool = _make_pool()
        sid = session_pool.create_session(pool)
        assert sid is not None
        session = session_pool.get_session(sid)
        assert session is not None
        assert session["gacha_count"] == 0
        assert len(session["pool"]) == 10

    def test_get_nonexistent(self):
        assert session_pool.get_session("fake-id") is None

    def test_get_expired(self):
        pool = _make_pool()
        sid = session_pool.create_session(pool)
        session_pool._sessions[sid]["expires_at"] = datetime.now(timezone.utc) - timedelta(hours=1)
        assert session_pool.get_session(sid) is None

    def test_increment_gacha(self):
        pool = _make_pool()
        sid = session_pool.create_session(pool)
        assert session_pool.increment_gacha(sid) == 1
        assert session_pool.increment_gacha(sid) == 2

    def test_increment_nonexistent(self):
        assert session_pool.increment_gacha("fake") == -1

    def test_add_previous_picks(self):
        pool = _make_pool()
        sid = session_pool.create_session(pool)
        pick_id = uuid.uuid4()
        session_pool.add_previous_picks(sid, {pick_id})
        session = session_pool.get_session(sid)
        assert pick_id in session["previous_picks"]

    def test_cleanup_expired(self):
        pool = _make_pool()
        sid1 = session_pool.create_session(pool)
        sid2 = session_pool.create_session(pool)
        session_pool._sessions[sid1]["expires_at"] = datetime.now(timezone.utc) - timedelta(hours=1)
        count = session_pool.cleanup_expired()
        assert count == 1
        assert session_pool.get_session(sid2) is not None


class TestGachaRoll:
    def test_roll_returns_3(self):
        pool = _make_pool()
        sid = session_pool.create_session(pool)
        result = roll(sid)
        assert len(result["candidates"]) == 3
        assert result["remaining_rolls"] == 4
        assert result["gacha_count"] == 1

    def test_roll_excludes_previous(self):
        pool = _make_pool()
        sid = session_pool.create_session(pool)
        result1 = roll(sid)
        first_ids = {r.id for r in result1["candidates"]}
        result2 = roll(sid)
        second_ids = {r.id for r in result2["candidates"]}
        assert first_ids != second_ids or len(pool) <= 6

    def test_roll_5_times(self):
        pool = _make_pool(15)
        sid = session_pool.create_session(pool)
        for i in range(5):
            result = roll(sid)
            assert result["remaining_rolls"] == 4 - i

    def test_roll_6th_raises(self):
        pool = _make_pool(15)
        sid = session_pool.create_session(pool)
        for _ in range(5):
            roll(sid)
        with pytest.raises(GachaLimitExceeded):
            roll(sid)

    def test_session_not_found(self):
        with pytest.raises(SessionNotFound):
            roll("nonexistent-id")

    def test_session_expired(self):
        pool = _make_pool()
        sid = session_pool.create_session(pool)
        session_pool._sessions[sid]["expires_at"] = datetime.now(timezone.utc) - timedelta(hours=1)
        with pytest.raises(SessionExpired):
            roll(sid)

    def test_small_pool(self):
        pool = _make_pool(2)
        sid = session_pool.create_session(pool)
        result = roll(sid)
        assert len(result["candidates"]) == 2

    def test_pool_exhausted_wraps_around(self):
        pool = _make_pool(4)
        sid = session_pool.create_session(pool)
        result1 = roll(sid)
        assert len(result1["candidates"]) == 3
        result2 = roll(sid)
        assert len(result2["candidates"]) == 1
        result3 = roll(sid)
        assert len(result3["candidates"]) == 3


class TestGachaAPI:
    @pytest.fixture
    def client(self):
        yield TestClient(app)

    def test_roll_success(self, client):
        pool = _make_pool()
        sid = session_pool.create_session(pool)
        resp = client.post(f"/gacha/{sid}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["candidates"]) == 3
        assert data["remaining_rolls"] == 4

    def test_roll_not_found(self, client):
        resp = client.post("/gacha/nonexistent")
        assert resp.status_code == 404

    def test_roll_expired(self, client):
        pool = _make_pool()
        sid = session_pool.create_session(pool)
        session_pool._sessions[sid]["expires_at"] = datetime.now(timezone.utc) - timedelta(hours=1)
        resp = client.post(f"/gacha/{sid}")
        assert resp.status_code == 410

    def test_roll_limit_exceeded(self, client):
        pool = _make_pool(15)
        sid = session_pool.create_session(pool)
        for _ in range(5):
            resp = client.post(f"/gacha/{sid}")
            assert resp.status_code == 200
        resp = client.post(f"/gacha/{sid}")
        assert resp.status_code == 429

    def test_remaining_decrements(self, client):
        pool = _make_pool()
        sid = session_pool.create_session(pool)
        for i in range(3):
            resp = client.post(f"/gacha/{sid}")
            assert resp.json()["remaining_rolls"] == 4 - i
