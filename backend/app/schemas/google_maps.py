from pydantic import BaseModel


class Location(BaseModel):
    lat: float
    lng: float


class Restaurant(BaseModel):
    place_id: str
    name: str
    location: Location
    vicinity: str | None = None
    rating: float | None = None
    user_ratings_total: int | None = None
    price_level: int | None = None
    types: list[str] = []
    business_status: str | None = None
    open_now: bool | None = None
    photo_reference: str | None = None


class NearbySearchResponse(BaseModel):
    restaurants: list[Restaurant]
    status: str
    next_page_token: str | None = None
