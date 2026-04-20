from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.schemas.google_maps import NearbySearchResponse
from app.services.google_maps import _parse_restaurant, get_photo_url, search_nearby

MOCK_PLACE = {
    "place_id": "ChIJtest123",
    "name": "Test Restaurant",
    "geometry": {"location": {"lat": 13.756, "lng": 100.502}},
    "vicinity": "123 Test Street",
    "rating": 4.5,
    "user_ratings_total": 200,
    "price_level": 2,
    "types": ["restaurant", "food"],
    "business_status": "OPERATIONAL",
    "opening_hours": {"open_now": True},
    "photos": [{"photo_reference": "photo_ref_abc", "height": 400, "width": 600}],
}

MOCK_OK_RESPONSE = {
    "status": "OK",
    "results": [MOCK_PLACE],
    "next_page_token": "token123",
}


class TestParseRestaurant:
    def test_full_place(self):
        r = _parse_restaurant(MOCK_PLACE)
        assert r.place_id == "ChIJtest123"
        assert r.name == "Test Restaurant"
        assert r.location.lat == 13.756
        assert r.location.lng == 100.502
        assert r.vicinity == "123 Test Street"
        assert r.rating == 4.5
        assert r.user_ratings_total == 200
        assert r.price_level == 2
        assert r.types == ["restaurant", "food"]
        assert r.business_status == "OPERATIONAL"
        assert r.open_now is True
        assert r.photo_reference == "photo_ref_abc"

    def test_minimal_place(self):
        minimal = {"place_id": "abc", "name": "Min", "geometry": {"location": {"lat": 0, "lng": 0}}}
        r = _parse_restaurant(minimal)
        assert r.place_id == "abc"
        assert r.rating is None
        assert r.photo_reference is None
        assert r.open_now is None
        assert r.types == []

    def test_no_photos(self):
        place = {**MOCK_PLACE, "photos": []}
        r = _parse_restaurant(place)
        assert r.photo_reference is None


class TestGetPhotoUrl:
    @patch("app.services.google_maps.settings")
    def test_photo_url(self, mock_settings):
        mock_settings.google_maps_api_key = "test_key"
        url = get_photo_url("ref123", max_width=800)
        assert "photoreference=ref123" in url
        assert "maxwidth=800" in url
        assert "key=test_key" in url

    @patch("app.services.google_maps.settings")
    def test_default_width(self, mock_settings):
        mock_settings.google_maps_api_key = "test_key"
        url = get_photo_url("ref123")
        assert "maxwidth=400" in url


class TestSearchNearby:
    @pytest.mark.asyncio
    @patch("app.services.google_maps.get_client")
    async def test_success(self, mock_get_client):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_OK_RESPONSE
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = await search_nearby(13.756, 100.502)
        assert isinstance(result, NearbySearchResponse)
        assert result.status == "OK"
        assert len(result.restaurants) == 1
        assert result.restaurants[0].name == "Test Restaurant"
        assert result.next_page_token == "token123"

    @pytest.mark.asyncio
    @patch("app.services.google_maps.get_client")
    async def test_quota_exceeded(self, mock_get_client):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "OVER_QUERY_LIMIT", "results": []}
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = await search_nearby(13.756, 100.502)
        assert result.status == "OVER_QUERY_LIMIT"
        assert result.restaurants == []

    @pytest.mark.asyncio
    @patch("app.services.google_maps.get_client")
    async def test_timeout_retry_success(self, mock_get_client):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_OK_RESPONSE
        mock_response.raise_for_status = MagicMock()
        mock_client.get.side_effect = [httpx.TimeoutException("timeout"), mock_response]
        mock_get_client.return_value = mock_client

        result = await search_nearby(13.756, 100.502)
        assert result.status == "OK"
        assert len(result.restaurants) == 1

    @pytest.mark.asyncio
    @patch("app.services.google_maps.get_client")
    async def test_timeout_retry_fail(self, mock_get_client):
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("timeout")
        mock_get_client.return_value = mock_client

        result = await search_nearby(13.756, 100.502)
        assert result.status == "TIMEOUT"
        assert result.restaurants == []

    @pytest.mark.asyncio
    @patch("app.services.google_maps.get_client")
    async def test_invalid_api_key(self, mock_get_client):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "REQUEST_DENIED",
            "error_message": "Invalid key",
            "results": [],
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = await search_nearby(13.756, 100.502)
        assert result.status == "REQUEST_DENIED"
        assert result.restaurants == []
