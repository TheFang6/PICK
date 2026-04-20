import uuid

from pydantic import BaseModel

from app.schemas.restaurant import RestaurantResponse


class RecommendRequest(BaseModel):
    user_ids: list[uuid.UUID]
    location: dict  # {"lat": float, "lng": float}
    radius: int = 1000


class RecommendationResult(BaseModel):
    candidates: list[RestaurantResponse]
    pool: list[RestaurantResponse]
    session_id: str
    remaining_rolls: int
