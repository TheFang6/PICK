import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.blacklist import BlacklistAddRequest, BlacklistListResponse, BlacklistResponse
from app.services import blacklist_repo, restaurant_repo

router = APIRouter(prefix="/blacklist", tags=["blacklist"])


@router.post("", response_model=BlacklistResponse, status_code=201)
def add_blacklist(
    body: BlacklistAddRequest,
    user_id: uuid.UUID = Query(..., description="User ID"),
    db: Session = Depends(get_db),
):
    if body.mode not in ("permanent", "today"):
        raise HTTPException(status_code=400, detail="mode must be 'permanent' or 'today'")

    restaurant = restaurant_repo.get_by_id(db, body.restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    entry = blacklist_repo.add(db, user_id=user_id, restaurant_id=body.restaurant_id, mode=body.mode)
    return BlacklistResponse.model_validate(entry)


@router.delete("/{blacklist_id}", status_code=204)
def remove_blacklist(
    blacklist_id: uuid.UUID,
    user_id: uuid.UUID = Query(..., description="User ID"),
    db: Session = Depends(get_db),
):
    removed = blacklist_repo.remove(db, user_id=user_id, blacklist_id=blacklist_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Blacklist entry not found")


@router.get("", response_model=BlacklistListResponse)
def list_blacklist(
    user_id: uuid.UUID = Query(..., description="User ID"),
    db: Session = Depends(get_db),
):
    entries = blacklist_repo.list_by_user(db, user_id=user_id)
    result = []
    for e in entries:
        resp = BlacklistResponse.model_validate(e)
        restaurant = restaurant_repo.get_by_id(db, e.restaurant_id)
        if restaurant:
            resp.restaurant_name = restaurant.name
        result.append(resp)
    return BlacklistListResponse(entries=result)
