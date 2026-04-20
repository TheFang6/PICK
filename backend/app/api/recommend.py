from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.recommendation import RecommendRequest, RecommendationResult
from app.schemas.restaurant import RestaurantResponse
from app.services.recommendation import recommend

router = APIRouter(tags=["recommend"])


@router.post("/recommend", response_model=RecommendationResult)
async def recommend_restaurants(
    body: RecommendRequest,
    db: Session = Depends(get_db),
):
    if not body.user_ids:
        raise HTTPException(status_code=400, detail="At least one user_id is required")

    lat = body.location.get("lat")
    lng = body.location.get("lng")
    if lat is None or lng is None:
        raise HTTPException(status_code=400, detail="location must include lat and lng")

    result = await recommend(
        db=db,
        user_ids=body.user_ids,
        office_lat=lat,
        office_lng=lng,
        radius=body.radius,
    )

    return RecommendationResult(
        candidates=[RestaurantResponse.model_validate(r) for r in result["candidates"]],
        pool=[RestaurantResponse.model_validate(r) for r in result["pool"]],
        session_id=result["session_id"],
    )
