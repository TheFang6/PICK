from fastapi import APIRouter, HTTPException

from app.schemas.gacha import GachaResult
from app.schemas.restaurant import RestaurantResponse
from app.services.gacha import (
    GachaLimitExceeded,
    SessionExpired,
    SessionNotFound,
    roll,
)

router = APIRouter(tags=["gacha"])


@router.post("/gacha/{session_id}", response_model=GachaResult)
def gacha_roll(session_id: str):
    try:
        result = roll(session_id)
    except SessionNotFound:
        raise HTTPException(status_code=404, detail="Session not found")
    except SessionExpired:
        raise HTTPException(status_code=410, detail="Session expired")
    except GachaLimitExceeded:
        raise HTTPException(status_code=429, detail="Gacha roll limit exceeded (max 5)")

    return GachaResult(
        candidates=[RestaurantResponse.model_validate(r) for r in result["candidates"]],
        remaining_rolls=result["remaining_rolls"],
        gacha_count=result["gacha_count"],
    )
