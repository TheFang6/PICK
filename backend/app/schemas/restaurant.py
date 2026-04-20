import uuid
from datetime import datetime

from pydantic import BaseModel


class RestaurantBase(BaseModel):
    name: str
    vicinity: str | None = None
    lat: float | None = None
    lng: float | None = None
    rating: float | None = None
    price_level: int | None = None
    types: list[str] = []
    photo_reference: str | None = None
    closed_weekdays: list[int] = []
    closed_monthly_ranges: list[dict] = []


class ManualRestaurantCreate(RestaurantBase):
    pass


class RestaurantUpdate(BaseModel):
    name: str | None = None
    vicinity: str | None = None
    lat: float | None = None
    lng: float | None = None
    rating: float | None = None
    price_level: int | None = None
    types: list[str] | None = None
    photo_reference: str | None = None
    closed_weekdays: list[int] | None = None
    closed_monthly_ranges: list[dict] | None = None


class RestaurantResponse(RestaurantBase):
    id: uuid.UUID
    place_id: str | None = None
    source: str
    added_by: uuid.UUID | None = None
    last_fetched_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RestaurantListResponse(BaseModel):
    restaurants: list[RestaurantResponse]
    total: int
    page: int
    page_size: int
