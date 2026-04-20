import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.history import LogLunchRequest, LunchHistoryListResponse, LunchHistoryResponse
from app.services import history_repo, restaurant_repo

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=LunchHistoryListResponse)
def get_user_history(
    user_id: uuid.UUID = Query(..., description="User ID"),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    entries = history_repo.get_user_history(db, user_id=user_id, limit=limit, offset=offset)
    return LunchHistoryListResponse(
        entries=[LunchHistoryResponse.model_validate(e) for e in entries],
    )


@router.get("/team", response_model=LunchHistoryListResponse)
def get_team_history(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    entries = history_repo.get_team_history(db, limit=limit, offset=offset)
    return LunchHistoryListResponse(
        entries=[LunchHistoryResponse.model_validate(e) for e in entries],
    )


@router.post("", response_model=LunchHistoryResponse, status_code=201)
def log_lunch(
    body: LogLunchRequest,
    db: Session = Depends(get_db),
):
    restaurant = restaurant_repo.get_by_id(db, body.restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    entry = history_repo.log_lunch(
        db,
        restaurant_id=body.restaurant_id,
        attendees=body.attendees,
        lunch_date=body.lunch_date,
    )
    return LunchHistoryResponse.model_validate(entry)
