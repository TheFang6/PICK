from pydantic import BaseModel

from app.schemas.restaurant import RestaurantResponse


class GachaResult(BaseModel):
    candidates: list[RestaurantResponse]
    remaining_rolls: int
    gacha_count: int
