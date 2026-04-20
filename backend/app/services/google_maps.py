import logging

import httpx

from app.config import settings
from app.schemas.google_maps import Location, NearbySearchResponse, Restaurant

logger = logging.getLogger(__name__)

NEARBY_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
PHOTO_URL = "https://maps.googleapis.com/maps/api/place/photo"

_client: httpx.AsyncClient | None = None


async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=10.0)
    return _client


def _parse_restaurant(place: dict) -> Restaurant:
    loc = place.get("geometry", {}).get("location", {})
    photos = place.get("photos", [])
    opening_hours = place.get("opening_hours", {})

    return Restaurant(
        place_id=place["place_id"],
        name=place["name"],
        location=Location(lat=loc.get("lat", 0), lng=loc.get("lng", 0)),
        vicinity=place.get("vicinity"),
        rating=place.get("rating"),
        user_ratings_total=place.get("user_ratings_total"),
        price_level=place.get("price_level"),
        types=place.get("types", []),
        business_status=place.get("business_status"),
        open_now=opening_hours.get("open_now"),
        photo_reference=photos[0]["photo_reference"] if photos else None,
    )


async def search_nearby(
    lat: float,
    lng: float,
    radius: int = 1000,
    type: str = "restaurant",
) -> NearbySearchResponse:
    client = await get_client()
    params = {
        "location": f"{lat},{lng}",
        "radius": radius,
        "type": type,
        "key": settings.google_maps_api_key,
    }

    try:
        resp = await client.get(NEARBY_SEARCH_URL, params=params)
        resp.raise_for_status()
    except httpx.TimeoutException:
        logger.warning("Google Maps API timeout, retrying once...")
        try:
            resp = await client.get(NEARBY_SEARCH_URL, params=params)
            resp.raise_for_status()
        except Exception:
            logger.error("Google Maps API retry failed")
            return NearbySearchResponse(restaurants=[], status="TIMEOUT")
    except httpx.HTTPStatusError as e:
        logger.error("Google Maps API HTTP error: %s", e.response.status_code)
        return NearbySearchResponse(restaurants=[], status="HTTP_ERROR")

    data = resp.json()
    status = data.get("status", "UNKNOWN")

    if status == "OVER_QUERY_LIMIT":
        logger.error("Google Maps API quota exceeded")
        return NearbySearchResponse(restaurants=[], status=status)

    if status != "OK":
        logger.warning("Google Maps API status: %s — %s", status, data.get("error_message", ""))
        return NearbySearchResponse(restaurants=[], status=status)

    restaurants = [_parse_restaurant(p) for p in data.get("results", [])]
    logger.info("Google Maps API returned %d restaurants", len(restaurants))

    return NearbySearchResponse(
        restaurants=restaurants,
        status=status,
        next_page_token=data.get("next_page_token"),
    )


def get_photo_url(photo_reference: str, max_width: int = 400) -> str:
    return (
        f"{PHOTO_URL}"
        f"?photoreference={photo_reference}"
        f"&maxwidth={max_width}"
        f"&key={settings.google_maps_api_key}"
    )
