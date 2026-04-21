import logging
import random
import uuid
from datetime import datetime, timezone
from math import log1p, radians, sin, cos, sqrt, atan2

from sqlalchemy.orm import Session

from app.models.restaurant import Restaurant, RestaurantSource
from app.schemas.google_maps import Restaurant as MapsRestaurant
from app.services.google_maps import search_nearby
from app.services import blacklist_repo, history_repo, restaurant_repo
from app.services.session_pool import MAX_GACHA_ROLLS, create_session, add_previous_picks

logger = logging.getLogger(__name__)


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371000
    rlat1, rlat2 = radians(lat1), radians(lat2)
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(rlat1) * cos(rlat2) * sin(dlng / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


async def fetch_candidates(
    db: Session,
    office_lat: float,
    office_lng: float,
    radius: int = 1000,
) -> list[Restaurant]:
    maps_result = await search_nearby(lat=office_lat, lng=office_lng, radius=radius)

    if maps_result.status == "OK":
        for r in maps_result.restaurants:
            restaurant_repo.upsert_from_maps(db, r)

    all_restaurants, _ = restaurant_repo.list_all(db, page_size=100)
    return all_restaurants


def filter_restaurants(
    candidates: list[Restaurant],
    context: dict,
) -> list[Restaurant]:
    today_weekday = context.get("today_weekday", datetime.now(timezone.utc).weekday())
    today_date = context.get("today_date", datetime.now(timezone.utc).date())
    office_lat = context.get("office_lat")
    office_lng = context.get("office_lng")
    radius = context.get("radius", 1000)
    recent_restaurant_ids = context.get("recent_restaurant_ids", set())
    blacklisted_ids = context.get("blacklisted_ids", set())

    filtered = []
    for r in candidates:
        if r.id in recent_restaurant_ids:
            continue

        if r.id in blacklisted_ids:
            continue

        if r.source == RestaurantSource.GOOGLE_MAPS:
            if hasattr(r, "business_status") and r.business_status == "CLOSED_PERMANENTLY":
                continue

        closed_weekdays = r.closed_weekdays or []
        if today_weekday in closed_weekdays:
            continue

        closed_ranges = r.closed_monthly_ranges or []
        skip = False
        for cr in closed_ranges:
            start = cr.get("start")
            end = cr.get("end")
            if start and end:
                from datetime import date as date_type
                s = date_type.fromisoformat(start)
                e = date_type.fromisoformat(end)
                if s <= today_date <= e:
                    skip = True
                    break
        if skip:
            continue

        if office_lat and office_lng and r.lat and r.lng:
            dist = _haversine(office_lat, office_lng, r.lat, r.lng)
            if dist > radius:
                continue

        filtered.append(r)

    return filtered


def score_restaurants(
    restaurants: list[Restaurant],
    context: dict,
) -> list[tuple[Restaurant, float]]:
    office_lat = context.get("office_lat")
    office_lng = context.get("office_lng")
    max_distance = context.get("radius", 1000)

    scored = []
    for r in restaurants:
        rating = r.rating or 3.5
        ratings_total = r.user_ratings_total if hasattr(r, "user_ratings_total") else 0
        ratings_count = ratings_total or 0

        distance_score = 1.0
        if office_lat and office_lng and r.lat and r.lng:
            dist = _haversine(office_lat, office_lng, r.lat, r.lng)
            distance_score = max(0, 1 - dist / max_distance)

        price = r.price_level or 2
        price_score = 1 - (price / 4)

        score = (
            rating * 0.4
            + log1p(ratings_count) * 0.3
            + distance_score * 0.2
            + price_score * 0.1
        )

        scored.append((r, round(score, 4)))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def select_pool(
    scored: list[tuple[Restaurant, float]],
    pool_size: int = 10,
) -> list[tuple[Restaurant, float]]:
    return scored[:pool_size]


def sample_candidates(
    pool: list[tuple[Restaurant, float]],
    k: int = 3,
) -> list[Restaurant]:
    if len(pool) <= k:
        return [r for r, _ in pool]

    restaurants = [r for r, _ in pool]
    weights = [max(0.01, score) for _, score in pool]
    selected = []
    remaining = list(range(len(pool)))
    remaining_weights = list(weights)

    for _ in range(k):
        chosen = random.choices(remaining, weights=remaining_weights, k=1)[0]
        idx = remaining.index(chosen)
        selected.append(chosen)
        remaining.pop(idx)
        remaining_weights.pop(idx)

    return [restaurants[i] for i in selected]


async def recommend(
    db: Session,
    user_ids: list,
    office_lat: float,
    office_lng: float,
    radius: int = 1000,
) -> dict:
    candidates = await fetch_candidates(db, office_lat, office_lng, radius)

    recent_restaurant_ids = history_repo.get_recent_restaurant_ids(db, user_ids, days=7)
    blacklisted_ids = blacklist_repo.get_blacklisted_restaurant_ids(db, user_ids)

    context = {
        "today_weekday": datetime.now(timezone.utc).weekday(),
        "today_date": datetime.now(timezone.utc).date(),
        "attendees": user_ids,
        "office_lat": office_lat,
        "office_lng": office_lng,
        "radius": radius,
        "recent_restaurant_ids": recent_restaurant_ids,
        "blacklisted_ids": blacklisted_ids,
    }

    filtered = filter_restaurants(candidates, context)
    scored = score_restaurants(filtered, context)
    pool = select_pool(scored, pool_size=10)
    picks = sample_candidates(pool, k=3)

    if db is not None:
        for r, _ in pool:
            try:
                db.expunge(r)
            except Exception:
                pass

    session_id = create_session(pool)
    add_previous_picks(session_id, {r.id for r in picks})

    return {
        "candidates": picks,
        "pool": [r for r, _ in pool],
        "session_id": session_id,
        "remaining_rolls": MAX_GACHA_ROLLS,
    }
